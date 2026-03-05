# Personalized-Diet-Plan-Generator-from-Medical-Report
NOTE : create branches by using your name as branch names and don't add any code to main 
# 🩺 AI Medical Diet Plan Generator

An intelligent diet planning system that extracts information from medical lab reports
and generates personalized 7-day diet plans using AI.

---

## 📁 Project Structure
```
AI_Diet_Plan/
├── extractor.py       # OCR + LLM-based lab report extraction
├── diet_planner.py    # AI diet plan generation using Groq LLM
├── app.py             # Gradio web application (tabbed UI)
├── .env               # API keys (not committed to git)
├── requirements.txt   # Python dependencies
└── README.md          # Project documentation
```

---

## ⚙️ Setup Instructions

### 1. Clone or Download the Project
```bash
cd Desktop
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
- Install to: `C:\Users\<yourname>\Tesseract-OCR\`
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
Open browser at: http://127.0.0.1:7861

---

## 🚀 Features

- 📂 Upload medical reports in PDF, Image (PNG/JPG), or TXT format
- 🔍 Automatic OCR text extraction using Tesseract + pdfplumber
- 🤖 AI-powered structured data extraction using Groq LLaMA 3.3 70B
- 🥗 Personalized 7-day meal plan (Vegetarian / Non-Vegetarian)
- 📊 BMI calculation with visual gauge
- ⚠️ Abnormal findings visualization
- 📈 Category-wise test summary charts
- 💊 Supplement recommendations with Indian brands
- 🛒 Zero sugar product suggestions
- 💧 Hydration & detox plan
- 🌿 Indian food-focused meal recommendations

---

## 📋 How to Use

1. Open the app at http://127.0.0.1:7861
2. Upload your medical lab report (PDF or image)
3. Fill in your preferences:
   - Diet type (Vegetarian / Non-Vegetarian)
   - Height, Weight, Age, Gender
   - Food allergies (optional)
4. Click **Generate My Diet Plan**
5. View results across 4 tabs:
   - 🥗 **Diet Plan** — 7-day meal plan + nutrient targets
   - 📊 **BMI & Charts** — BMI gauge + lab result visualizations
   - 💊 **Supplements & Products** — Supplements + zero sugar + Indian brands
   - 💧 **Hydration & Detox** — Daily hydration + weekly detox plan

---

## 🧠 AI Models Used

| Task | Model |
|------|-------|
| Lab Report Extraction | LLaMA 3.3 70B (via Groq) |
| Diet Plan Generation | LLaMA 3.3 70B (via Groq) |


---

## 🛠️ Tech Stack

- **Frontend**: Gradio
- **OCR**: Tesseract + pdfplumber
- **AI**: Groq API (LLaMA 3.3 70B)
- **Visualization**: Matplotlib
- **Language**: Python 3.10+
