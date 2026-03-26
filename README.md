Diet-planner-app/
├── backend/
│   ├── __init__.py
│   ├── config.py         # Configuration & Model settings
│   ├── main.py           # FastAPI server entry point
│   ├── ocr.py            # Llama Vision OCR logic
│   ├── extraction.py     # Structured Data Extraction logic
│   ├── diet_generator.py # Diet Plan Generation logic
│   ├── rag_chat.py       # RAG (Vector DB) logic
│   └── rag_chat_1.py     # Updated RAG (Vector DB) logic
├── frontend/
│   ├── app.py            # Streamlit UI
│   └── app2.py           # Updated streamlit UI
├── .env                  # API Keys (Create this file if not exists!)
├── requirements.txt      # Dependency list
└── README.md             # This file

## 🛠️ Quick Start Guide

### 1. Setup Environment (Using uv)

We recommend using `uv` for extremely fast setup.

### steps to do in terminal after opening the folder in ide

**Install uv (if not installed):**
```bash
pip install uv
```

**Create & Activate Virtual Environment:**
```bash
# Windows
uv venv

.venv\Scripts\activate

# Mac/Linux
uv venv

source .venv/bin/activate
```

**Install Dependencies:**
```bash
uv pip install -r requirements.txt
```

> **Alternative:** If you prefer standard pip, run `python -m venv venv`, activate it, and run `pip install -r requirements.txt`

### 2. Configure API Keys

In the file named `.env` in the root folder and add your Groq API Key:
```env
GROQ_API_KEY=gsk_yoursupersecretkeyhere...
```

### 3. Running the Application

You need to open **two separate terminals** (make sure the virtual environment is activated in both).

**Terminal 1: Start Backend (API)**
```bash
uvicorn backend.main:app --reload
```
✅ **Success:** You should see `Application startup complete.` running at `http://127.0.0.1:8000`

**Terminal 2: Start Frontend (UI)**
```bash
streamlit run frontend/app.py
```
✅ **Success:** A browser window will open automatically at `http://localhost:8501`



