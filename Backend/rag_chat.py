import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
from groq import Groq
import uuid
import os

# ---------------- API KEY ----------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# ---------------- EMBEDDINGS ----------------
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

class RAGChat:
    def __init__(self):
        self.chroma_client = chromadb.Client()
        self.collection = self.chroma_client.get_or_create_collection(
            name="diet_collection",
            embedding_function=embedding_func
        )

    # ---------------- ADD DATA ----------------
    def add_context(self, session_id, markdown_text, structured_data, diet_plan, patient_profile=""):
        documents = []
        metadatas = []
        ids = []

        # 🔥 LIMIT TEXT SIZE
        documents.append(markdown_text[:2000])
        metadatas.append({"session_id": session_id})
        ids.append(str(uuid.uuid4()))

        documents.append(str(structured_data)[:1000])
        metadatas.append({"session_id": session_id})
        ids.append(str(uuid.uuid4()))

        documents.append(diet_plan[:1500])
        metadatas.append({"session_id": session_id})
        ids.append(str(uuid.uuid4()))

        if patient_profile:
            documents.append(patient_profile[:500])
            metadatas.append({"session_id": session_id})
            ids.append(str(uuid.uuid4()))

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    # ---------------- QUERY ----------------
    def query_context(self, session_id, query):
        results = self.collection.query(
            query_texts=[query],
            n_results=1,  # 🔥 reduce results
            where={"session_id": session_id}
        )

        if results and results['documents']:
            docs = [doc for sub in results['documents'] for doc in sub]

            # 🔥 LIMIT TOTAL CONTEXT SIZE
            combined = " ".join(docs)
            return combined[:1500]

        return ""

    # ---------------- CHAT ----------------
    def chat(self, session_id, user_message):
        context = self.query_context(session_id, user_message)

        messages = [
            {
                "role": "system",
                "content": f"""
You are a helpful diet and health assistant.

Use this user data:
{context}

Guidelines:
- Answer based on user's health and diet
- Be simple and clear
- Do not give medical diagnosis
"""
            },
            {
                "role": "user",
                "content": user_message
            }
        ]

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # ✅ stable + low token usage
            messages=messages,
            temperature=0.7
        )

        return response.choices[0].message.content

# ---------------- INSTANCE ----------------
rag_chat = RAGChat()