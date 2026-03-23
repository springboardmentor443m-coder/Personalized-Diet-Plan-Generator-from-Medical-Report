🥗 AI Diet Plan Generator

An AI-powered web application that analyzes health reports (PDFs) and generates personalized diet plans. Built with Streamlit, this app combines NLP, embeddings, and report analysis to deliver tailored nutrition recommendations.

🚀 Features
📄 Upload and extract data from medical reports (PDF)
🔍 Analyze key health metrics
🧠 AI-driven diet plan generation
💬 Chat interface for follow-up questions (RAG-based)
📥 Download personalized diet plans as PDF
⚡ Fast and interactive UI using Streamlit
🛠️ Tech Stack
Frontend/UI: Streamlit
Backend: Python
AI/NLP: Sentence Transformers, LLM integration
PDF Processing: Custom parser
Embeddings: all-MiniLM-L6-v2
Other: UUID, Regex
📁 Project Structure
ai-dietplan-generator/
│
├── backend/
│   ├── diet_generator.py       # Diet plan generation logic
│   ├── health_analyzer.py      # Health metrics analysis
│   ├── llm_engine.py           # LLM interaction layer
│   ├── pdf_export.py           # Export diet plan to PDF
│   ├── rag_chat.py             # Chat system (RAG)
│   ├── report_parser.py        # Extract text from reports
│
├── app.py                      # Main Streamlit app
├── .env                        # Environment variables
├── venv/                       # Virtual environment
├── DietPlan_*.pdf              # Generated diet plans
⚙️ Installation
1. Clone the repository
git clone https://github.com/your-username/ai-dietplan-generator.git
cd ai-dietplan-generator
2. Create virtual environment
python -m venv venv
source venv/bin/activate     # Mac/Linux
venv\Scripts\activate        # Windows
3. Install dependencies
pip install -r requirements.txt
🔑 Environment Variables

Create a .env file and add:

OPENAI_API_KEY=your_api_key
HF_TOKEN=your_huggingface_token (optional but recommended)
▶️ Run the App
streamlit run app.py

Open in browser:

http://localhost:8501
🔄 System Architecture & Workflow
🧩 High-Level Flow
User Upload PDF
        ↓
report_parser.py → Extract Text
        ↓
health_analyzer.py → Analyze Health Metrics
        ↓
diet_generator.py → Generate Diet Plan (LLM)
        ↓
pdf_export.py → Export as PDF (Optional)
        ↓
Streamlit UI → Display Results
⚙️ Detailed Workflow
PDF Upload
User uploads a health report via Streamlit UI.
Text Extraction
report_parser.py extracts raw text from the PDF.
Health Data Processing
health_analyzer.py identifies and structures:
Blood sugar
Cholesterol
Hemoglobin
Other key metrics
Diet Plan Generation
diet_generator.py sends structured data to the LLM
Personalized diet plan is generated
PDF Export
pdf_export.py converts the generated plan into a downloadable PDF
💬 Chatbot (RAG) Workflow

The chatbot enables users to ask questions about their health report and diet plan.

🔄 Chat Flow
User Query
     ↓
rag_chat.py
     ↓
Convert query → Embedding
     ↓
Retrieve relevant context (report data)
     ↓
LLM processes:
   (Query + Retrieved Context)
     ↓
Generate Response
     ↓
Return to Streamlit Chat UI
🧠 How RAG Works Here
Embedding Creation
Report text is converted into vector embeddings using Sentence Transformers
Context Retrieval
Relevant chunks of the report are fetched based on similarity
LLM Response Generation
Combines:
User query
Retrieved context
Produces accurate, context-aware answers
⚠️ Notes

The warning:

embeddings.position_ids | UNEXPECTED

can usually be ignored unless model mismatch issues occur.

For better performance, use a Hugging Face token.
📌 Future Improvements
🧬 More advanced health condition detection
📊 Visual dashboards for metrics
🥦 Meal customization options
🌍 Multi-language support