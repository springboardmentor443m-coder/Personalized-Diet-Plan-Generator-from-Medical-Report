# 🥗 AI Diet Plan Generator

An AI-powered web application that analyzes health reports (PDFs) and generates personalized diet plans.

---

## 🚀 Features

* 📄 Upload medical reports (PDF)
* 🔍 Analyze health metrics
* 🧠 Generate AI-based diet plans
* 💬 Chat with your report (RAG-based)
* 📥 Download diet plan as PDF

---

## 🛠️ Tech Stack

* Streamlit
* Python
* Sentence Transformers
* LLM

---

## 📁 Project Structure

```
modules/
   ocr_module.py
   data_extraction.py
   llm_extraction.py

app.py
README.md
```

---

## ⚙️ Installation

```
git clone https://github.com/your-username/repo.git
cd repo
pip install -r requirements.txt
```

---

## ▶️ Run

```
streamlit run app.py
```

---

## 🔄 System Workflow

```
Upload PDF 
   ↓
Extract Text (OCR / Parser)
   ↓
Analyze Health Data
   ↓
Generate Diet Plan (LLM)
   ↓
Display / Export PDF
```

---

## 💬 Chatbot Workflow (RAG)

```
User Query
   ↓
Convert to Embedding
   ↓
Retrieve Relevant Report Data
   ↓
Send to LLM
   ↓
Generate Response
```

---

## ⚠️ Notes

* Do not expose API keys
* Use `.env` file for secrets
