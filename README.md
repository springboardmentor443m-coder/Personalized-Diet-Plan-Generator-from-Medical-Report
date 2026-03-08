# AI-NutriCare

AI-NutriCare is a full-stack application that analyzes medical reports and generates personalized diet plans.

## Features

- Upload medical reports (PDF/JPG/PNG)
- OCR-based report text extraction
- Lab value extraction and basic interpretation
- ML-based health risk prediction
- AI-generated diet plans with support for:
  - Vegetarian
  - Non-Veg
  - Veg + Non-Veg
  - Vegan
- Allergy-aware diet generation, including custom allergy input
- PDF export of generated diet plans
- Groq-backed generation with fallback generation when API is unavailable

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI
- ML: scikit-learn
- OCR: pytesseract, pdf2image
- PDF generation: reportlab
- LLM provider: Groq API

## Project Structure

```text
NutriCare/
  backend/
    app/
      api/
      services/
    requirements.txt
    train_model.py
  frontend/
    src/
    package.json
  start.sh
```

## Prerequisites

- Python 3.13+
- Node.js 18+
- npm
- Tesseract OCR installed on your machine

## Setup

### 1. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Frontend setup

```bash
cd ../frontend
npm install
```

## Environment Variables

Create `backend/.env`:

```env
GROQ_API_KEY=groq_api_key
```

## Run the application

From repository root:

```bash
chmod +x start.sh
./start.sh
```

Default URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`

## API Endpoints

- `POST /api/upload` - upload and extract report data
- `POST /api/generate` - generate diet plan
- `GET /api/download-pdf` - download generated PDF

## Notes

- If Groq API is unavailable, the app uses fallback diet generation.
- The generate response contains `diet_generation_source` with value `groq` or `fallback`.
