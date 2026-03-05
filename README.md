# 🩺 AI Medical Diet Plan Generator

An intelligent diet planning system that extracts information from medical lab reports
and generates personalized 7-day diet plans using AI — built with Flask, Groq LLaMA,
Tesseract OCR, and a professional HTML/CSS frontend.

---

## 📁 Project Structure
```
AI_Diet_Plan/
├── templates/
│   └── index.html         # Professional Flask HTML/CSS/JS frontend
├── static/                # Auto-generated charts (BMI, abnormal, category)
├── uploads/               # Temporary uploaded report files
├── model/
│   ├── prompt_templates.py  # All LLM prompts in one place
│   └── model_config.json    # Model settings (temperature, tokens, etc.)
├── extractor.py           # OCR + LLM-based lab report extraction
├── diet_planner.py        # AI diet plan generation using Groq LLM
├── app.py                 # Flask web application (tabbed UI)
├── output.json            # Auto-generated extracted lab report
├── diet_output.json       # Auto-generated diet plan output
├── .env                   # API keys (not committed to git)
├── requirements.txt       # Python dependencies
└── README.md              # Project documentation
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
- Download from: https://github.com/UB-Mannheim/tesseract/wiki
- Install to your user folder (avoid Program Files):
```
C:\Users\<yourname>\Tesseract-OCR\
```
- Update path in `extractor.py`:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\<yourname>\Tesseract-OCR\tesseract.exe"
```

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
Open browser at: **http://127.0.0.1:5000**

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

### 📊 Output Tabs

| Tab | Contents |
|-----|----------|
| 🥗 Diet Plan | Nutrient targets + 7-day meal plan table |
| 📊 BMI & Charts | BMI gauge + abnormal findings + category summary |
| 💊 Supplements | Supplements + zero sugar products + Indian brands |
| 💧 Hydration & Detox | Daily hydration plan + weekly detox |

---

## 🗺️ System Architecture
```
USER BROWSER
     │
     ▼
FLASK UI (app.py) ── http://127.0.0.1:5000
     │
     ├── POST /generate
     │
     ▼
EXTRACTOR (extractor.py)
     │  pdfplumber → PDF text
     │  OpenCV + Tesseract → Image text
     │
     ▼
GROQ API ──► LLaMA 3.3 70B
     │  returns structured JSON
     │  (patient info, tests, abnormal findings)
     │
     ▼
DIET PLANNER (diet_planner.py)
     │  BMI calculated locally
     │  sends report + user prefs to LLM
     │
     ▼
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
| User ↔ Flask | HTTP | localhost:5000 |
| Flask → Extractor | Internal Python | Function call |
| Extractor → Groq | HTTPS REST API | LLM Call 1 — OCR extraction |
| Flask → Diet Planner | Internal Python | Function call |
| Diet Planner → Groq | HTTPS REST API | LLM Call 2 — Diet generation |
| Flask → Matplotlib | Internal Python | Chart generation |
| Flask → Browser | HTTP | Serves HTML + static charts |

---

## 🧠 AI Models

| Task | Model | Provider | Temperature | Max Tokens |
|------|-------|----------|-------------|------------|
| Lab Report Extraction | LLaMA 3.3 70B Versatile | Groq | 0 | 8000 |
| Diet Plan Generation | LLaMA 3.3 70B Versatile | Groq | 0.3 | 8000 |

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
| Abnormal Findings | `abnormal_findings` JSON | Horizontal bar chart |
| Category Summary | `tests_by_category` JSON | Normal vs Abnormal grouped bars |

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Flask (Python) |
| OCR | Tesseract 5.5 + pdfplumber |
| AI / LLM | Groq API — LLaMA 3.3 70B |
| Visualization | Matplotlib + NumPy |
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

Install all with:
```bash
pip install -r requirements.txt
```

