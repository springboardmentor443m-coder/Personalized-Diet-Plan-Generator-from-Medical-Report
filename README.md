# AI-NutriCare

AI-NutriCare is a full-stack web application that reads medical reports, extracts health data, predicts risk indicators, generates a personalized diet plan, and lets the user ask follow-up questions through an AI assistant.

## Features

- Upload medical reports in `pdf`, `png`, `jpg`, or `jpeg`
- OCR-based text extraction for scanned reports
- Lab value extraction from different report layouts
- Status evaluation for extracted values such as `Normal`, `High`, `Low`, `Overweight`, or `Prediabetes`
- ML-based health prediction support
- Personalized diet generation using Groq with fallback mode
- Diet preference support:
  - `Vegetarian`
  - `Non-Veg`
  - `Veg + Non-Veg`
  - `Vegan`
- Allergy-aware diet planning, including custom allergies
- AI assistant for questions about the report and generated diet plan
- PDF export for the generated plan

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI + Python
- OCR: `pytesseract`, `pdf2image`, OpenCV
- ML: `scikit-learn`, `pandas`, `numpy`
- PDF: `reportlab`
- LLM: Groq API

## Project Structure

```text
NutriCare/
├── README.md
├── .gitignore
├── pyrightconfig.json
├── start.sh
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   └── main.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── data_extractor.py
│   │   │   ├── dataset_loader.py
│   │   │   ├── diet_generator.py
│   │   │   ├── groq_service.py
│   │   │   ├── health_predictor.py
│   │   │   ├── model_trainer.py
│   │   │   ├── ocr_service.py
│   │   │   └── pdf_generator.py
│   │   └── __init__.py
│   ├── data/
│   │   ├── models/
│   │   │   └── health_model.pkl
│   │   ├── processed/
│   │   └── raw/
│   ├── requirements.txt
│   └── train_model.py
└── frontend/
    ├── public/
    │   └── vite.svg
    ├── src/
    │   ├── services/
    │   │   └── api.js
    │   ├── utils/
    │   │   └── nutritionCalculator.js
    │   ├── App.css
    │   ├── App.jsx
    │   ├── index.css
    │   └── main.jsx
    ├── .gitignore
    ├── eslint.config.js
    ├── index.html
    ├── package-lock.json
    ├── package.json
    └── vite.config.js
```

## Requirements

- Python `3.13+`
- Node.js `18+`
- npm
- Tesseract OCR installed and available in PATH

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cd ..
```

### Frontend

```bash
cd frontend
npm install
cd ..
```

## Configuration

Create `backend/.env`:

```env
GROQ_API_KEY=your_groq_api_key
```

If the Groq key is missing or the API is unavailable, the project falls back to local diet generation and local assistant answers where possible.

## Running The Project

### Recommended

```bash
chmod +x start.sh
./start.sh
```

### Manual Run

Backend:

```bash
cd backend
source .venv/bin/activate
python -m app.api.main
```

Frontend:

```bash
cd frontend
npm run dev
```

## Default URLs

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger docs: `http://localhost:8000/docs`

## API Endpoints

- `POST /api/upload`
  - Uploads a medical report and returns extracted values
- `POST /api/generate`
  - Generates a personalized diet plan
- `POST /api/chat`
  - Answers user questions about the report and diet plan
- `GET /api/download-pdf`
  - Downloads the generated diet plan PDF

## Notes

- `backend/data/models/health_model.pkl` is required at runtime for ML prediction.
- `backend/data/raw/` and `backend/data/processed/` are runtime folders. They are created and used by the app, but generated contents should not be committed.
- `pyrightconfig.json` is only for local editor support. It is not required to run the app.

## Troubleshooting

- If VS Code shows import warnings:
  - select the backend interpreter at `backend/.venv/bin/python`
- If OCR quality is poor:
  - verify Tesseract is installed and available in terminal
- If `python app/api/main.py` fails:
  - run `python -m app.api.main` instead
- If Groq does not respond:
  - verify `GROQ_API_KEY`
  - the app should still use fallback logic
