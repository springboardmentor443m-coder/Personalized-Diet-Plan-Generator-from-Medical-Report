\# 🩺 AI for Health: Intelligent Diet \& Lab Analyzer



A full-stack health-tech application that transforms complex medical lab reports (PDFs/Images) into actionable health insights. By combining \*\*OCR (Optical Character Recognition)\*\* with \*\*Large Language Models (LLMs)\*\*, the app provides personalized nutrition strategies and an interactive medical assistant based on user biomarkers.



\---



\## 🚀 Key Features



\* ⚡ \*\*Smart Report Parsing\*\*

&#x20; Upload blood reports (PDF, JPG, PNG). AI automatically extracts and structures medical markers.



\* 📊 \*\*Health Dashboard\*\*

&#x20; Clean interface displaying BMI, abnormalities, and clinical insights.



\* 🥗 \*\*Dynamic Nutrition Strategy\*\*

&#x20; Generates personalized diet plans based on detected deficiencies (e.g., anemia, cholesterol).



\* 💬 \*\*Interactive AI Consultant\*\*

&#x20; Chat interface with context-aware responses and dynamic FAQs based on your report.



\* 📥 \*\*Export Diet Plan\*\*

&#x20; Download generated diet plans for offline use or doctor consultation.



\* ⏳ \*\*Real-time Progress Feedback\*\*

&#x20; User-friendly progress indicators during AI processing.



\---



\## 🛠️ Tech Stack



\*\*Frontend:\*\* Streamlit

\*\*Backend:\*\* FastAPI (Python)

\*\*AI/ML:\*\* LLM Integration (Groq / OpenAI / Gemini), OCR

\*\*Data Handling:\*\* Pandas, JSON, Regex

\*\*Vector DB:\*\* ChromaDB

\*\*Other Tools:\*\* dotenv, requests



\---



\## 📦 Installation \& Setup



\### 1️⃣ Clone the Repository



```bash

git clone https://github.com/your-username/ai-for-health.git

cd ai-for-health

```



\---



\### 2️⃣ Create Virtual Environment



```bash

python -m venv venv

```



\#### Activate environment:



\*\*Windows\*\*



```bash

venv\\Scripts\\activate

```



\*\*Mac/Linux\*\*



```bash

source venv/bin/activate

```



\---



\### 3️⃣ Install Dependencies



```bash

pip install -r requirements.txt

```



\---



\### 4️⃣ Configure Environment Variables



Create a `.env` file in the root directory:



```env

GROQ\_API\_KEY=your\_api\_key\_here

BACKEND\_URL=http://localhost:8000

```



\---



\### 5️⃣ Run the Application



\#### 🔹 Terminal 1 — Backend



```bash

cd backend

uvicorn main:app --reload

```



\#### 🔹 Terminal 2 — Frontend



```bash

cd frontend

streamlit run app.py

```



\---



\## 🎨 Application Flow



1\. Upload medical report

2\. OCR extracts text

3\. AI processes medical data

4\. Structured insights generated

5\. Personalized diet plan created

6\. Chat assistant uses RAG for context-aware responses



\---



\## 📸 UI Overview



\* \*\*Home:\*\* Upload report + enter details

\* \*\*Dashboard:\*\* Health metrics \& abnormalities

\* \*\*Diet Plan:\*\* Personalized recommendations

\* \*\*Chat:\*\* Ask questions about your report



\---



\## ⚖️ Disclaimer



This application is intended for \*\*educational and informational purposes only\*\*.

It is \*\*not a substitute for professional medical advice, diagnosis, or treatment\*\*.



Always consult a qualified healthcare provider for medical concerns.



\---



\## 👩‍💻 Author



\*\*Adhya Prashanth\*\*

AI Internship Project



\---



