An intelligent healthcare system that extracts information from medical lab reports and generates personalized 7-day diet plans using AI/ML — built with Flask, Groq LLaMA, Tesseract OCR, and a professional HTML/CSS frontend.

##📁**Project Structure**
```
AI-NutriCare/
├── templates/
│   └── dashboard.html         # Professional Flask HTML/CSS/JS frontend
├── static/                    # Auto-generated charts (BMI, health metrics, risk analysis)
├── uploads/                    # Temporary uploaded report files
├── src/
│   ├── extraction/
│   │   └── report_parser.py    # OCR + LLM-based lab report extraction
│   ├── ml_analysis/
│   │   └── health_classifier.py # ML-based health risk classification
│   ├── nlp_interpretation/
│   │   └── medical_nlp.py       # AI/NLP interpretation of doctor notes
│   └── diet_generator/
│       └── diet_planner.py      # AI diet plan generation using Groq LLM
├── models/                      # Trained ML models
├── output/                      # Generated diet plans (PDF/JSON)
├── app.py                       # Flask web application (tabbed UI)
├── output.json                   # Auto-generated extracted lab report
├── diet_output.json              # Auto-generated diet plan output
├── .env                          # API keys (not committed to git)
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```


---

##⚙️**Setup Instructions**

###1.**Create Project Folder**
```bash
mkdir AI-NutriCare
cd AI-NutriCare
```
###2.**Create Virtual Environment**
```bash
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Mac/Linux
```

###3.**Install Dependencies**
```bash   
pip install -r requirements.txt
```
###4.**Install Tesseract OCR**

Download from: https://github.com/UB-Mannheim/tesseract/wiki
Install to your user folder (avoid Program Files):
```
C:\Users\<yourname>\Tesseract-OCR\
```
Update path in src/extraction/report_parser.py:
```python
pytesseract.pytesseract.tesseract_cmd = r"C:\Users\<yourname>\Tesseract-OCR\tesseract.exe"
```

###5.**Configure API Key**
Create a .env file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
```
Get your free API key at: https://console.groq.com

###6.**Train ML Model (Optional)**
```bash
python src/ml_analysis/train_model.py
```

###7.**Run the Application**
```bash
python app.py
```
Open browser at: **http://127.0.0.1:5000**

---

##🚀 **Features**

###📂 **Input**
-Upload medical reports in PDF, Image (PNG/JPG), or TXT format
-Select Vegetarian / Non-Vegetarian / Vegan / Keto diet preference
-Enter Height, Weight, Age, Gender for BMI calculation
-Optionally specify food allergies / intolerances

###🤖 **AI/ML Processing**
-Automatic OCR text extraction using Tesseract + pdfplumber
-ML-based health risk classification (Random Forest/XGBoost)
-NLP interpretation of doctor notes using transformer models
-Structured data extraction via Groq LLaMA 3.3 70B
-Personalized diet plan generation based on lab results + preferences + ML insights

###📊**Output Tabs**

|Tab|Contents|
|----|-------|
|🥗 Diet Plan	Nutrient targets | 7-day meal plan table with medication timing|
|📈 Health Analytics	BMI gauge | risk level + abnormal findings + category summary|
|🩺 Medical Insights	Extracted health metrics | doctor notes | detected conditions|
|💊 Recommendations	Supplements | dietary guidelines | Indian brand suggestions|
|💧 Wellness Plan	Daily hydration plan | weekly detox | exercise tips|
---
🗺️ **System Architecture**
```
USER BROWSER
     │
     ▼
FLASK UI (app.py) ── http://127.0.0.1:5000
     │
     ├── POST /generate
     │
     ▼
EXTRACTOR (src/extraction/report_parser.py)
     │  pdfplumber → PDF text
     │  OpenCV + Tesseract → Image text
     │
     ▼
STRUCTURED DATA EXTRACTION
     │  Rule-based parsing + Groq API
     │
     ▼
ML HEALTH CLASSIFIER (src/ml_analysis/health_classifier.py)
     │  Trained models evaluate health metrics
     │  Returns risk levels + alerts
     │
     ▼
NLP INTERPRETER (src/nlp_interpretation/medical_nlp.py)
     │  Transformer models analyze doctor notes
     │  Extracts conditions + dietary rules
     │
     ▼
DIET PLANNER (src/diet_generator/diet_planner.py)
     │  Combines ML + NLP outputs
     │  BMI calculated locally
     │  Sends report + user prefs to LLM
     │
     ▼
GROQ API ──► LLaMA 3.3 70B
     │  Returns full diet plan JSON
     │
     ▼
MATPLOTLIB
     │  bmi_gauge.png
     │  risk_analysis.png
     │  category_summary.png
     │
     ▼
FLASK → dashboard.html → USER BROWSER
```

---

##🔗 **Connections Used**
|Connection|Type|Details|
|----------|----|-------|
|User ↔ Flask|HTTP|localhost:5000|
|Flask → Extractor|Internal Python|Function call|
|Extractor → Groq|HTTPS REST API|LLM Call 1 — OCR extraction|
|Flask → ML Classifier|Internal Python|Health risk prediction|
|Flask → NLP Interpreter|Internal Python|Doctor notes analysis|
|Flask → Diet Planner|Internal Python|	Function call|
|Diet Planner → Groq|HTTPS REST API|LLM Call 2 — Diet generation|
|Flask → Matplotlib|Internal Python|Chart generation|
|Flask → Browser|HTTP|Serves HTML + static charts|

---

##🧠 **AI/ML Models**
|Task|Model|Provider|Temperature|Max Tokens|
|----|-----|--------|-----------|----------|
|Lab Report Extraction|LLaMA 3.3 70B Versatile|Groq|0|8000|
|Health Risk Classification|Random Forest/XGBoost	scikit-learn|N/A|N/A|
|Doctor Notes Interpretation|BART/GPT	Hugging Face|0.2|1000|
|Diet Plan Generation|LLaMA 3.3 70B Versatile|Groq|0.3|8000|

---

##📊**Health Risk Categories**

|Risk Level|Description|Action Required|
|----------|-----------|---------------|
|Low Risk|All metrics within normal range|Maintain healthy diet|
|Moderate Risk|	1-2 abnormal values|Targeted dietary changes|
|High Risk|	Multiple abnormal values|	Immediate dietary intervention + doctor follow-up|

---

##**BMI Categories**

|BMI|Range|Category|Action|
|---|-----|--------|------|
|< 18.5|Underweight|Calorie-dense nutrition|
|18.5 – 24.9|	Normal|Maintain balance|
|25 – 29.9|Overweight|Reduce carbs, increase fiber|
|≥ 30|Obese|Low-calorie, high-fiber diet|

---

##**Health Metrics Thresholds**

|Metric|Normal|Borderline|High Risk|
|------|------|----------|----------|
|Blood Sugar|70-100 mg/dL|100-125 mg/dL|≥ 126 mg/dL|
|Total Cholesterol|< 200 mg/dL|200-239 mg/dL|≥ 240 mg/dL|
|HDL|> 40 mg/dL|35-40 mg/dL|< 35 mg/dL|
|LDL|< 100 mg/dL|130-159 mg/dL|≥ 160 mg/dL|
|Triglycerides|< 150 mg/dL|150-199 mg/dL|≥ 200 mg/dL|

---

##📈 **Charts Generated**

|Chart|Source|Data|Description|
|-----|------|----|-----------|
|BMI Gauge|User inputs|Color-coded scale with marker|
|Risk Level Gauge|ML classification|Visual representation of health risk|
|Abnormal Findings|Lab results|Horizontal bar chart of abnormal values|
|Category Summary|Tests by category|Normal vs Abnormal grouped bars|
|Health Metrics Radar|Multiple metrics|Comparative analysis of all parameters|

---

##🛠️**Tech Stack**

|Layer|Technology|
|-----|----------|
|Frontend|HTML5, CSS3, Vanilla JavaScript|
|Backend|Flask (Python)|
|OCR|Tesseract 5.5 + pdfplumber + EasyOCR|
|ML|scikit-learn, XGBoost, LightGBM|
|AI|LLM	Groq API — LLaMA 3.3 70B|
|NLP|Transformers (BART, BERT)|
|Visualization|Matplotlib + NumPy|
|PDF Export|ReportLab|
|Environment|python-dotenv|

---

##📦 **Dependencies**
```
flask
groq
python-dotenv
pdfplumber
pytesseract
easyocr
opencv-python
pillow
scikit-learn
xgboost
lightgbm
transformers
torch
matplotlib
numpy
reportlab
joblib
```
Install all with:
```bash
pip install -r requirements.txt
```
