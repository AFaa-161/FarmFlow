# 🌱 FarmFlow – AI-Powered Smart Agriculture Platform

FarmFlow is an AI-powered smart agriculture platform designed to help farmers make better decisions about crop quality, weather conditions, and market opportunities.

It combines Machine Learning, weather APIs, and intelligent decision-making to reduce post-harvest losses and improve farmers' profits.

## 🚀 Features

- **🌾 AI-Based Crop Analysis:** Analyze uploaded crop images using a Machine Learning model.
- **📊 Crop Quality Detection:** Evaluate crop quality, damage percentage, and estimated shelf life.
- **🌦️ Real-Time Weather Monitoring:** Display temperature, humidity, and weather conditions based on the farmer's location.
- **🤖 Smart Decision Engine:** Recommend whether farmers should SELL, STORE, or TRANSPORT their crops.
- **🔐 User Authentication:** Login and registration functionality.
- **💰 Market-Based Recommendations:** Consider market price, storage costs, and transportation expenses to support decisions.

## 🛠️ Tech Stack

### Frontend
- React.js
- Vite
- JavaScript
- CSS

### Backend
- Python
- FastAPI
- Uvicorn

### Machine Learning
- Python
- TensorFlow
- Computer Vision

### Database
- SQLite / JSON

### APIs
- Weather API

## 📂 Project Structure

```text
FarmFlow/
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── ...
│   ├── public/
│   └── package.json
│
├── backend/
│   ├── main.py
│   ├── ml_service.py
│   ├── decision_engine.py
│   ├── weather_service.py
│   ├── dataset/
│   └── ...
│
├── .gitignore
└── README.md
```

## ⚙️ Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/FarmFlow.git
cd FarmFlow
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the backend:

```bash
uvicorn main:app --reload
```

Backend URL: http://127.0.0.1:8000

API Documentation: http://127.0.0.1:8000/docs

### 3. Frontend Setup

Open another terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: http://localhost:5173

## 🔄 How FarmFlow Works

1. Farmer logs into the FarmFlow application.
2. Farmer uploads an image of the crop.
3. The Machine Learning model analyzes crop quality.
4. The system estimates crop damage and shelf life.
5. Weather information is retrieved using the farmer's location.
6. The decision engine evaluates market price, storage cost, and transportation cost.
7. FarmFlow recommends the most suitable action: SELL, STORE, or TRANSPORT.

## 🎯 Project Objective

The main objective of FarmFlow is to empower farmers with AI-driven insights, reduce food wastage, minimize post-harvest losses, and improve agricultural decision-making.

## 🔮 Future Enhancements

- Advanced crop disease detection.
- Live agricultural market price integration.
- Multilingual support for farmers.
- Farmer-to-buyer marketplace.
- Improved ML model accuracy.
- Mobile application integration.





