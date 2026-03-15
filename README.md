# 🩺 AI Medical Diet Plan Generator

An intelligent diet planning system that extracts information from medical lab reports
and generates personalized 7-day diet plans using AI — built with Flask, Groq LLaMA,
Tesseract OCR, and a professional HTML/CSS frontend with an integrated AI chatbot.

---

## 📁 Project Structure

```
AI_Diet_Plan/
├── templates/
│   └── index.html           # Professional Flask HTML/CSS/JS frontend + chatbot UI
├── static/                  # Auto-generated charts (BMI, abnormal, category)
├── uploads/                 # Temporary uploaded report files
├── model/
│   ├── prompt_templates.py  # All LLM prompts centralized
│   └── model_config.json    # Model settings (temperature, tokens, BMI config)
├── extractor.py             # OCR + LLM-based lab report extraction
├── diet_planner.py          # AI diet plan generation using Groq LLM
├── app.py                   # Flask web application + chatbot route
├── output.json              # Auto-generated extracted lab report
├── diet_output.json         # Auto-generated diet plan output
├── .env                     # API keys (never commit this)
├── requirements.txt         # Python dependencies
└── README.md                # Project documentation
```

---

## ⚙️ Setup Instructions

### 1. Create Project Folder
```bash
mkdir AI_Diet_Plan
cd AI_Diet_Plan
```

### 2. Create Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Install Tesseract OCR
- Download installer from: https://github.com/UB-Mannheim/tesseract/wiki
- Install to your user folder to avoid admin issues:
```
C:\Users\<yourname>\Tesseract-OCR\
```
- Update path in `extractor.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\<yourname>\Tesseract-OCR\tesseract.exe"
```
- For images in Program Files, run VS Code as Administrator

### 5. Configure API Key
Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
```
Get your free API key at: https://console.groq.com

### 6. Run the Application
```bash
python app.py
```
Open browser at: **http://127.0.0.1:8080**

---

## 🚀 Features

### 📂 Input
- Upload medical reports in PDF, Image (PNG/JPG), or TXT format
- Select Vegetarian / Non-Vegetarian diet preference
- Enter Height, Weight, Age, Gender for BMI calculation
- Optionally specify food allergies / intolerances

### 🤖 AI Processing
- Automatic OCR text extraction using Tesseract + pdfplumber
- Structured data extraction via Groq LLaMA 3.3 70B
- Personalized diet plan generation based on lab results + preferences
- AI chatbot powered by LLaMA 3.3 70B with full report context

### 📊 Output Tabs

| Tab | Contents |
|-----|----------|
| 🥗 Diet Plan | Nutrient targets + 7-day meal plan table |
| 📊 BMI & Charts | BMI gauge + abnormal findings + category summary |
| 💊 Supplements | Supplements + zero sugar products + Indian brands |
| 💧 Hydration & Detox | Daily hydration plan + weekly detox |

### 🤖 AI Chatbot
- Floating chat bubble (bottom right corner)
- Available before and after report upload
- Automatically receives full lab report + diet plan context after generation
- Answers questions about lab results, meal substitutes, supplements, Indian food options
- Maintains conversation history for contextual replies

---

## 🗺️ System Architecture

```
USER BROWSER
     │
     ▼
FLASK UI (app.py) ── http://127.0.0.1:8080
     │
     ├── POST /generate ──────────────────────────────────┐
     │                                                     │
     ▼                                                     │
EXTRACTOR (extractor.py)                                   │
     │  pdfplumber → PDF text                              │
     │  OpenCV + Tesseract → Image text                    │
     │                                                     │
     ▼                                                     │
GROQ API ──► LLaMA 3.3 70B                                 │
     │  returns structured JSON                            │
     │  (patient info, tests, abnormal findings)           │
     │                                                     ▼
     ▼                                          POST /chat
DIET PLANNER (diet_planner.py)                GROQ API ──► LLaMA 3.3 70B
     │  BMI calculated locally                     │  chatbot replies with
     │  sends report + user prefs to LLM           │  report + diet context
     │                                             ▼
     ▼                                        USER BROWSER
GROQ API ──► LLaMA 3.3 70B
     │  returns full diet plan JSON
     │
     ▼
MATPLOTLIB
     │  bmi_plot.png
     │  abnormal_plot.png
     │  category_plot.png
     │
     ▼
FLASK → index.html → USER BROWSER
```

---

## 🔗 Connections Used

| Connection | Type | Details |
|------------|------|---------|
| User ↔ Flask | HTTP | localhost:8080 |
| Flask → Extractor | Internal Python | Function call |
| Extractor → Groq | HTTPS REST API | LLM Call 1 — OCR extraction |
| Flask → Diet Planner | Internal Python | Function call |
| Diet Planner → Groq | HTTPS REST API | LLM Call 2 — Diet generation |
| Chatbot → Groq | HTTPS REST API | LLM Call 3 — Chat responses |
| Flask → Matplotlib | Internal Python | Chart generation |
| Flask → Browser | HTTP | Serves HTML + static charts |

---

## 🧠 AI Models

| Task | Model | Provider | Temperature | Max Tokens |
|------|-------|----------|-------------|------------|
| Lab Report Extraction | LLaMA 3.3 70B Versatile | Groq | 0 | 8000 |
| Diet Plan Generation | LLaMA 3.3 70B Versatile | Groq | 0.3 | 8000 |
| Chatbot Responses | LLaMA 3.3 70B Versatile | Groq | 0.5 | 1000 |

---

## 📊 BMI Categories

| BMI Range | Category | Action |
|-----------|----------|--------|
| < 18.5 | Underweight | Calorie-dense nutrition |
| 18.5 – 24.9 | Normal | Maintain balance |
| 25 – 29.9 | Overweight | Reduce carbs, increase fiber |
| ≥ 30 | Obese | Low-calorie, high-fiber diet |

---

## 📈 Charts Generated

| Chart | Source Data | Description |
|-------|-------------|-------------|
| BMI Gauge | User inputs | Color-coded scale with marker |
| Abnormal Findings | `abnormal_findings` JSON | Horizontal bar chart, color by severity |
| Category Summary | `tests_by_category` JSON | Normal vs Abnormal grouped bars |

---

## 💬 Chatbot Capabilities

The AI chatbot can answer questions about:

| Topic | Example Questions |
|-------|------------------|
| Lab Report | "What does my hemoglobin mean?" |
| Diet Plan | "Can I replace roti with rice?" |
| Meal Substitutes | "I don't like dal, what can I eat?" |
| Supplements | "When should I take Vitamin D?" |
| BMI & Weight | "How long to reach normal BMI?" |
| Indian Foods | "Is idli good for my condition?" |
| Hydration | "What detox drink suits me?" |
| Products | "Which Indian brand for iron?" |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Flask (Python) |
| OCR | Tesseract 5.5 + pdfplumber |
| AI / LLM | Groq API — LLaMA 3.3 70B |
| Visualization | Matplotlib + NumPy |
| Chatbot | Groq API — LLaMA 3.3 70B |
| Environment | python-dotenv |

---

## 📦 Dependencies

```
flask
groq
python-dotenv
pdfplumber
pytesseract
opencv-python
pillow
matplotlib
numpy
```

Install all:
```bash
pip install -r requirements.txt
```

---

## 🖥️ Running Locally

```bash
# 1. Activate virtual environment
venv\Scripts\activate

# 2. Start Flask server
python app.py

# 3. Open in browser
http://127.0.0.1:8080
```

To stop the server press **Ctrl + C** in the terminal.

---

## 🚧 Known Limitations

- Tesseract OCR requires careful path setup on Windows
- Image quality affects OCR accuracy — use clear, high-resolution scans
- LLM responses may vary slightly between runs
- Currently supports English lab reports only
- Uploaded files are stored temporarily in `/uploads` folder
- Charts are overwritten on each new report generation

---

## 🔐 Security Notes

- Never commit your `.env` file to version control
- Add `.env` to your `.gitignore` before pushing to GitHub
- Regenerate your Groq API key if accidentally exposed
- For production deployment use a WSGI server like Gunicorn

---

## 🌐 Future Deployment Options

When ready to deploy publicly, supported platforms include:

| Platform | Type | Notes |
|----------|------|-------|
| PythonAnywhere | Free tier | Python-focused, easy setup |
| Render.com | Free tier | Auto-deploy from GitHub |
| Railway.app | Free tier | Simple, fast deployment |
| Ngrok | Instant tunnel | Quick public URL, no hosting |

Deployment guide will be added when the project is ready for public release.

---

## ⚠️ Disclaimer

This application is for **informational purposes only** and does not constitute
medical advice. Always consult a qualified healthcare professional before making
any dietary or lifestyle changes based on lab results.

---

## 👨‍💻 Development Status

```
✅ OCR extraction (PDF + Image + TXT)
✅ LLM-based lab report parsing
✅ Personalized 7-day diet plan generation
✅ BMI calculator + visual gauge
✅ Abnormal findings chart
✅ Category-wise test summary chart
✅ Supplements + zero sugar + Indian brand suggestions
✅ Hydration & detox plan
✅ AI chatbot with full report context
✅ Flask professional frontend
🔲 Public deployment (planned)
🔲 Multi-language support (planned)
🔲 Historical report tracking (planned)
🔲 PDF export of diet plan (planned)
```
