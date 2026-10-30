
from pathlib import Path

import numpy as np
import tensorflow as tf
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
MODEL_PATH = BASE_DIR / "models" / "farmflow_freshness.keras"

IMAGE_SIZE = (224, 224)
_model = None


def get_model():
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            raise FileNotFoundError(
                f"Trained model not found: {MODEL_PATH}. "
                "Run train_model.py first."
            )
        _model = tf.keras.models.load_model(MODEL_PATH)

    return _model


def analyze_crop(image_path: str) -> dict:
    path = Path(image_path)

    if not path.exists():
        raise FileNotFoundError("Uploaded image was not found.")

    # The training model expects RGB pixels sized 224 x 224.
    with Image.open(path) as image:
        image = image.convert("RGB").resize(IMAGE_SIZE)
        image_array = np.asarray(image, dtype=np.float32)

    batch = np.expand_dims(image_array, axis=0)

    model = get_model()

    # The sigmoid output represents the probability of the stale class.
    stale_probability = float(model.predict(batch, verbose=0)[0][0])
    stale_probability = min(1.0, max(0.0, stale_probability))

    quality_score = round((1.0 - stale_probability) * 100)
    damage_percent = round(stale_probability * 100)

    if stale_probability >= 0.5:
        quality = "Stale"
    else:
        quality = "Fresh"

    # Illustrative heuristic only; this is NOT a trained shelf-life model.
    if quality_score >= 85:
        shelf_life_days = 5
    elif quality_score >= 70:
        shelf_life_days = 3
    elif quality_score >= 50:
        shelf_life_days = 2
    else:
        shelf_life_days = 1

    return {
        "assessment_mode": "MobileNetV2 trained freshness classifier",
        "quality": quality,
        "quality_score": quality_score,
        "stale_probability": round(stale_probability, 4),
        "damage_percent": damage_percent,
        "estimated_shelf_life_days": shelf_life_days,
        "shelf_life_note": (
            "Illustrative estimate from a heuristic, not a validated "
            "shelf-life prediction."
        ),
    }
