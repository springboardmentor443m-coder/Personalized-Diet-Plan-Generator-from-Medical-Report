# AI-Powered Personalized Diet Plan Generator

Analyses patient medical reports (PDF / images), extracts lab data with AI vision models, aggregates multi-document health states, and generates a personalised diet plan with safety guardrails.

## Features

- **OCR & Extraction** — Vision-model OCR (Llama 4 Scout) + LLM-based structured extraction (Kimi K2) with schema validation
- **Multi-Document Aggregation** — Conflict resolution, trend detection, chronic-condition flags across multiple reports
- **Diet Generation** — Context-aware prompt builder → LLM diet plan → safety checks (caloric floor, macronutrient extremes, medication interactions)
- **Background Tasks** — Long-running pipelines run asynchronously; poll for progress
- **API Key Authentication** — Optional `X-API-Key` header; disabled when `API_KEY` is empty
- **SQLite Storage** — Persistent sessions, documents, and task queue with automatic TTL cleanup
- **Streamlit Frontend** — Interactive UI for uploading reports and viewing results

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI, Uvicorn |
| Frontend | React 18 + Vite |
| LLM Provider | Groq SDK (Llama 4 Scout, Kimi K2, Llama 3.3 70B) |
| OCR | Vision-model based (no Tesseract) |
| PDF Rendering | pypdfium2 |
| Storage | SQLite (WAL mode) |

## Project Structure

```
main.py                          # FastAPI entry-point
config/

    ```
    frontend/
        src/
            App.jsx                  # Root component + step state machine
            api.js                   # Fetch wrappers for backend endpoints
            index.css                # Global styles
            components/
                UploadStep.jsx       # File upload + dietary preferences form
                ProgressStep.jsx     # Spinner + polling status
                ResultStep.jsx       # Health summary + diet plan display
        index.html
        vite.config.js               # Dev proxy → localhost:8000
        package.json
    ```
    settings.py                  # Env-var configuration
api/
    dependencies.py              # API key dependency
    routers/
        health.py                # GET /api/v1/health
        reports.py               # POST /api/v1/process-report(s)
        diet.py                  # POST /api/v1/generate-diet-plan
        tasks.py                 # POST /api/v1/tasks/*, GET /api/v1/tasks/*
schemas/
    models.py                   # Pydantic request/response models
services/
    database.py                  # SQLite CRUD + task queue
    file_service.py              # File validation & storage
    report_service.py            # OCR → extraction → aggregation pipeline
    diet_service.py              # Diet generation orchestration
modules/
    bmi.py                       # BMI calculation
    ocr.py                       # Vision-model OCR
    pdf_to_image.py              # PDF/image → PIL images
    structured_extraction.py     # LLM JSON extraction
    document_classifier.py       # Rule-based doc-type classifier
    health_state_aggregator.py   # Multi-report aggregation
    diet_generator.py            # LLM diet plan generation
    diet_prompt_builder.py       # Prompt construction
    safety_guardrails.py         # Diet safety checks
```

## Quick Start

### 1. Clone & install

```bash
git clone <repo-url>
cd diet_plan
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS
pip install -r requirements.txt
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env — set GROQ_API_KEY (required)
# Optionally set API_KEY for authentication
```

### 3. Run

**FastAPI backend:**

```bash
uvicorn main:app --reload
```

API docs available at `http://localhost:8000/docs`.

**React frontend:**

```bash
cd frontend
npm install      # first time only
npm run dev      # http://localhost:3000
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/health` | Health check |
| `POST` | `/api/v1/process-report` | Process a single medical report |
| `POST` | `/api/v1/process-reports` | Process multiple reports with aggregation |
| `POST` | `/api/v1/generate-diet-plan` | Full pipeline: process + generate diet |
| `POST` | `/api/v1/tasks/process-reports` | Submit multi-report processing as background task |
| `POST` | `/api/v1/tasks/generate-diet-plan` | Submit diet generation as background task |
| `GET` | `/api/v1/tasks/{task_id}` | Poll task status |

All endpoints (except health) require `X-API-Key` header when `API_KEY` is configured.

## Environment Variables

See [.env.example](.env.example) for all available configuration options.

## License

MIT
