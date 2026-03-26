# AI-NutriCare 🧬

AI-NutriCare is a modern, full-stack medical intelligence application. It empowers users to upload their clinical lab reports (like blood work and diagnostics), parses the complex data using advanced Artificial Intelligence OCR and LLMs, and synthesizes it into actionable health insights. By combining these lab results with physical biomarkers (Age, Weight, Height), AI-NutriCare generates personalized nutritional protocols and explicitly flags critical abnormalities. 

It also includes an integrated **RAG (Retrieval-Augmented Generation) Chatbot** that allows users to converse naturally with their medical data.

---

## ✨ Core Features
- **Intelligent Document Parsing**: Upload any PDF or Image report. Google Gemini AI will read, extract, and structure all clinical tests, observed values, and expected ranges.
- **Defensive Health Fallbacks**: The system actively scans all extracted interpretations. Any result flagged as "high", "low", or "critical" is pulled into a dedicated "Abnormal Findings" pipeline, ensuring health risks are never overlooked.
- **Biometric Nutritional Synthesis**: Calculates BMI and prescribes a detailed dietary intervention containing Focus Superfoods, Foods to Avoid, and a precision Daily Meal Blueprint.
- **Dynamic PDF Reports**: Programmatically generated, beautifully formatted PDF downloads summarizing the extracted report alongside the synthesized nutritional plan.
- **RAG Clinical Assistant**: A floating chat interface on the dashboard where users can query their specific imported medical results naturally.
- **Robust Security**: Fully authenticated using JWT tokens and bcrypt password hashing, storing legacy medical reports securely for returning users.

---

## 🛠️ Technology Stack

**Frontend (Client)**
- React.js (Vite)
- React Router DOM
- CSS3 (Custom Claymorphism Aesthetic & Fully Responsive)
- Axios

**Backend (Server & AI Pipeline)**
- Python 3.10+
- FastAPI & Uvicorn (High-performance Async API)
- Google Generative AI (Gemini Flash LLM & Embeddings)
- ChromaDB (Vector Database for RAG)
- SQLAlchemy (ORM) & SQLite/PostgreSQL (Database Layer)
- ReportLab (PDF Generation)
- PyJWT & Passlib (Authentication)

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js** (v18+)
- **Python** (v3.10+)

### 2. Backend Setup
1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```
2. Create and activate a python virtual environment:
   ```bash
   python -m venv venv
   # Windows: 
   venv\Scripts\activate
   # Mac/Linux: 
   source venv/bin/activate
   ```
3. Install the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the FastAPI server (Runs on `http://127.0.0.1:8001`):
   ```bash
   uvicorn main:app --reload --port 8001
   ```

### 3. Frontend Setup
1. Open a new terminal and navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```
2. Install the node modules:
   ```bash
   npm install
   ```
3. Start the Vite development server (Runs on `http://localhost:5173`):
   ```bash
   npm run dev
   ```

### 4. API & Environment Keys
To utilize the AI extraction and RAG chatbot, ensure your Google AI Studio API Key is configured in `backend/config.py` (or migrated to a `.env` file).

---

## 📁 Architecture Overview
- `/frontend/src/pages/Dashboard.jsx`: The primary UI hub containing the document intake forms, the parsed "Bento Box" visualizer, and the floating RAG chat interface.
- `/backend/api.py`: The core FastAPI router handling user authentication, file uploads, and payload manipulation.
- `/backend/modules/llm_extractor.py`: The bridge to the Gemini Model that parses raw lab OCR text into strict JSON structure.
- `/backend/modules/diet_generator.py`: Generates the personalized Nutritional Protocol based on extracted bloodwork and calculated biometrics.
- `/backend/modules/pdf_exporter.py`: Handles programmatic drawing of the structured clinical profile into a downloadable PDF format. 

---
*Built for clinical efficiency and personalized wellness.*
