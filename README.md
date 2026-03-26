\# 🩺 AI for Health: Intelligent Diet \& Lab Analyzer



It is a full-stack health-tech application that transforms complex medical lab reports (PDFs/Images) into actionable health insights. By combining \*\*OCR (Optical Character Recognition)\*\* with \*\*Large Language Models (LLMs)\*\*, the app provides a personalized nutrition strategy and an interactive medical consultant based on a user's unique biomarkers.



\---



\## 🚀 Key Features



\* \*\*⚡ Smart Report Parsing:\*\* Upload blood work in PDF, JPG, or PNG format. The AI automatically extracts and categorizes medical markers.

\* \*\*📊 Health Dashboard:\*\* A clean, wide-screen interface showing BMI, critical abnormalities, and clinical lab notes at a glance.

\* \*\*🥗 Dynamic Nutrition Strategy:\*\* Generates a personalized meal plan in an appealing card-based grid layout, specifically addressing detected deficiencies (e.g., Anaemia, High Cholesterol).

\* \*\*💬 Interactive AI Consultant:\*\* A ChatGPT-style interface with a professional medical greeting and \*\*Dynamic FAQs\*\* that change based on your specific report results.

\* \*\*📥 Professional PDF Export:\*\* One-click download of your generated nutrition plan for offline use or sharing with a doctor.

\* \*\*⏳ Real-time Progress:\*\* A multi-step loading bar that keeps the user informed during the heavy lifting of AI analysis.



\---



\## 🛠️ Tech Stack



\*\*Frontend:\*\* Streamlit, CSS3 (Custom Glassmorphism/Stone UI)  

\*\*Backend:\*\* FastAPI / Python  

\*\*AI/ML:\*\* LLM Integration (OpenAI/Gemini), OCR Engine  

\*\*PDF Generation:\*\* FPDF (Legacy Support)  

\*\*Data Handling:\*\* Pandas, JSON, Regex  



\---



\## 📦 Installation \& Setup



\### 1. Clone the Repository

```bash

git clone \[https://github.com/your-username/ai-for-health.git](https://github.com/your-username/ai-for-health.git)

cd ai-for-health

2\. Set Up Virtual Environment

Bash

python -m venv venv

\# On Windows:

source venv/Scripts/activate

\# On Mac/Linux:

source venv/bin/activate

3\. Install Dependencies

Bash

pip install -r requirements.txt

4\. Configuration

Create a .env file in the root directory and add your API keys:



Code snippet

API\_KEY=your\_llm\_api\_key\_here

BACKEND\_URL=http://localhost:8000

5\. Run the Application

You will need two terminals (one for backend, one for frontend):



Terminal 1 (Backend):



Bash

cd backend

uvicorn main:app --reload

Terminal 2 (Frontend):



Bash

cd frontend

streamlit run app.py

🎨 User Interface Preview

Home: Minimalist centered landing page for profile input and file upload.

Dashboard: Wide-view metrics and critical marker alerts.

Nutrition: Grid-style cards separating meals and dietary goals.

Chat: Pinned input bar with report-specific "Quick Prompt" buttons.



⚖️ Disclaimer

This application is an AI-powered tool intended for educational and informational purposes only. It is not a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of your physician or other qualified health provider with any questions you may have regarding a medical condition.

