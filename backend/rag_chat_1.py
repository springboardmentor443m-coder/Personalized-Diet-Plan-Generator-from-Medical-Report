import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict
from groq import Groq
from backend.config import settings
import uuid

# Initialize Groq client
client = Groq(api_key=settings.GROQ_API_KEY)

# Embedding model (runs locally)
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


class RAGChat:
    def __init__(self):
        """Initialize ChromaDB client and collection."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_PERSIST_DIR)
        )

        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.COLLECTION_NAME,
                embedding_function=embedding_func,
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"ChromaDB Initialization Error: {e}")
            raise e

    def add_context(
        self,
        session_id: str,
        markdown_text: str,
        structured_data: dict,
        diet_plan: str,
        patient_profile: str = ""
    ):
        """Add context safely to vector DB."""

        documents = []
        metadatas = []
        ids = []

        # --- OCR TEXT (chunked) ---
        chunk_size = 1000
        text_chunks = [
            markdown_text[i:i + chunk_size]
            for i in range(0, len(markdown_text), chunk_size)
        ]

        for idx, chunk in enumerate(text_chunks):
            documents.append(str(chunk))
            metadatas.append({
                "session_id": session_id,
                "context_type": "unstructured_ocr",
                "chunk_index": idx
            })
            ids.append(f"{session_id}_ocr_{idx}_{uuid.uuid4()}")

        # --- STRUCTURED DATA ---
        documents.append(f"Structured Data:\n{str(structured_data)}")
        metadatas.append({
            "session_id": session_id,
            "context_type": "structured_data"
        })
        ids.append(f"{session_id}_structured_{uuid.uuid4()}")

        # --- DIET PLAN ---
        documents.append(f"Diet Plan:\n{str(diet_plan)}")
        metadatas.append({
            "session_id": session_id,
            "context_type": "diet_plan"
        })
        ids.append(f"{session_id}_diet_{uuid.uuid4()}")

        # --- PATIENT PROFILE ---
        if patient_profile:
            documents.append(f"Patient Profile:\n{str(patient_profile)}")
            metadatas.append({
                "session_id": session_id,
                "context_type": "patient_profile"
            })
            ids.append(f"{session_id}_profile_{uuid.uuid4()}")

        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )

    def query_context(self, session_id: str, query: str, n_results: int = 3) -> List[str]:
        """Retrieve relevant context from DB."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"session_id": session_id}
            )

            if results and results["documents"]:
                return [doc for sublist in results["documents"] for doc in sublist]

            return []

        except Exception as e:
            print(f"Query Error: {e}")
            return []

    def chat(self, session_id: str, user_message: str, chat_history: List[Dict] = None) -> str:
        """Generate RAG response."""

        if chat_history is None:
            chat_history = []

        # --- Retrieve context ---
        relevant_docs = self.query_context(session_id, str(user_message), 3)
        context = "\n\n".join(map(str, relevant_docs)) if relevant_docs else "No specific context found."

        # --- Build messages safely ---
        messages = [
            {
                "role": "system",
                "content": str(
                    f"""You are a helpful medical assistant specializing in diet and nutrition.

Use the following context to answer questions:

{context}

Guidelines:
- Provide helpful, accurate information
- Be empathetic
- Refer to medical values when relevant
- Refer to diet plan when relevant
- Do NOT give medical diagnoses
- Encourage consulting professionals
"""
                )
            }
        ]

        # --- SAFE chat history ---
        for msg in chat_history[-4:]:
            if isinstance(msg, dict):
                messages.append({
                    "role": msg.get("role", "user"),
                    "content": str(msg.get("content", ""))
                })

        # --- Current user message ---
        messages.append({
            "role": "user",
            "content": str(user_message)
        })

        # --- Call Groq ---
        try:
            response = client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=messages,
                temperature=0.7
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print(f"Groq API Error: {e}")
            return "Sorry, I encountered an error while processing your request."

    def clear_session(self, session_id: str):
        """Clear session data from DB."""
        try:
            self.collection.delete(where={"session_id": session_id})
        except Exception as e:
            print(f"Error clearing session: {e}")


# Singleton instance
rag_chat = RAGChat()