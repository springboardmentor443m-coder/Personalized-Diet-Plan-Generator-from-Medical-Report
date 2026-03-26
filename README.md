# 🥗 AI Diet Recommendation System

This project was developed as part of an internship program.  
It is an AI-powered application that helps users generate personalized diet plans based on extracted health data.

The system uses OCR and AI models to analyze input data and provide intelligent diet recommendations along with chatbot support.

---

## 🚀 Features

- 📄 Extracts health data using OCR  
- 🧠 Generates personalized diet plans using AI  
- 💬 Chatbot support using RAG (Retrieval-Augmented Generation)  
- ⚡ FastAPI backend for processing  
- 🎯 Streamlit-based interactive UI  

---

## 📁 Project Structure
AI-Diet-Recommendation-System/
├── backend/
│ ├── init.py
│ ├── config.py
│ ├── main.py
│ ├── ocr.py
│ ├── extraction.py
│ ├── diet_generator.py
│ └── rag_chat.py
├── frontend/
│ └── app.py
├── .env.example
├── requirements.txt
└── README.md

---

## 🛠️ Setup Instructions

### 1. Create Virtual Environment

**Using uv (recommended):**

```bash
pip install uv
uv venv
Activate environment

Windows:

.venv\Scripts\activate

Mac/Linux:

source .venv/bin/activate
```
2. Install Dependencies
   ```bash
   uv pip install -r requirements.txt

   Alternative:

   pip install -r requirements.txt
   ```

3. Configure Environment Variables
   ```bash

    Create a .env file in the root directory and add your API key:

   GROQ_API_KEY=your_api_key_here
   ```

▶️ Running the Application

Open two terminals and activate the environment in both.

🔹 Start Backend Server
 ```bash
uvicorn backend.main:app --reload
 ```

Backend will run at:
http://127.0.0.1:8000

🔹 Start Frontend UI
 ```bash
streamlit run frontend/app.py
 ```

Frontend will open at:
http://localhost:8501

👩‍💻 Author

Kratika Shukla

🔮 Future Improvements
Add user authentication
Integrate database (PostgreSQL / MongoDB)
Deploy on cloud (AWS / Render)
Improve recommendation accuracy
Add user health tracking dashboard

📌 Note
This project is intended for learning and demonstration purposes.
Further improvements can be made to enhance scalability and real-world usag
