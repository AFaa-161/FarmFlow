
import os
import shutil
import tempfile

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from ml_service import analyze_crop
from decision_engine import recommend_action
from weather_service import get_weather
from fastapi import Depends
from auth import router as auth_router, init_auth_db, get_current_user

app = FastAPI(title="FarmFlow API")
init_auth_db()
app.include_router(auth_router)

# Allow requests from the local React/Vite frontend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def home():
    return {"message": "FarmFlow API is running"}


# --------------------------------------------------
# Weather API
# --------------------------------------------------

@app.get("/api/weather")
async def weather(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
):
    try:
        return await get_weather(latitude, longitude)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except httpx.HTTPError:
        raise HTTPException(
            status_code=502,
            detail="Weather service is temporarily unavailable.",
        )


# --------------------------------------------------
# Crop analysis and decision API
# --------------------------------------------------

@app.post("/api/analyze")
async def analyze(
    image: UploadFile = File(...),
    market_price: float = Form(100),
    storage_cost: float = Form(5),
    transport_cost: float = Form(10),
    transport_hours: float = Form(4),
    current_user: dict = Depends(get_current_user),
):
    allowed_types = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }

    # Validate uploaded image type.
    if image.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail="Upload a JPG, PNG, or WEBP image.",
        )

    # Validate numeric inputs.
    if min(
        market_price,
        storage_cost,
        transport_cost,
        transport_hours,
    ) < 0:
        raise HTTPException(
            status_code=400,
            detail="Costs, price, and transport time cannot be negative.",
        )

    # Preserve a valid image extension.
    suffix = os.path.splitext(image.filename or "")[1].lower()

    if suffix not in {".jpg", ".jpeg", ".png", ".webp"}:
        suffix_by_type = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
        }
        suffix = suffix_by_type.get(image.content_type, ".jpg")

    temp_path = None

    try:
        # Save the uploaded image temporarily.
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=suffix,
        ) as temp_file:
            temp_path = temp_file.name
            shutil.copyfileobj(image.file, temp_file)

        # Run the crop assessment.
        assessment = analyze_crop(temp_path)

        if not isinstance(assessment, dict):
            raise ValueError(
                "Crop assessment must return a dictionary."
            )

        # Support either shelf-life key used by ml_service.py.
        shelf_life = assessment.get(
            "estimated_shelf_life_days",
            assessment.get("shelf_life_days"),
        )

        if "quality_score" not in assessment:
            raise ValueError(
                f"quality_score missing from assessment: {assessment}"
            )

        if shelf_life is None:
            raise ValueError(
                f"Shelf-life field missing from assessment: {assessment}"
            )

        # Run the decision engine using its six required arguments.
        decision = recommend_action(
            quality_score=int(assessment["quality_score"]),
            shelf_life_days=int(shelf_life),
            market_price=market_price,
            storage_cost=storage_cost,
            transport_cost=transport_cost,
            transport_hours=transport_hours,
        )

        return {
            "filename": image.filename,
            "assessment": assessment,
            "decision": decision,
        }

    except HTTPException:
        raise

    except Exception as exc:
        print(f"Crop analysis error: {exc}")

        raise HTTPException(
            status_code=500,
            detail="Crop analysis failed. Check the backend terminal logs.",
        )

    finally:
        await image.close()

        # Remove the temporary image after processing.
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)
