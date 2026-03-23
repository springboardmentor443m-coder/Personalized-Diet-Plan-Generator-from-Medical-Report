import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer
from typing import List, Dict
from groq import Groq
from backend.config import settings
import uuid
import os

client = Groq(api_key=settings.GROQ_API_KEY)

# --- FIX: Use a standard embedding function ---
# This uses the default all-MiniLM-L6-v2 model which is lightweight and standard for RAG.
# If it fails to download, you might need to install: pip install sentence-transformers
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

class RAGChat:
    def __init__(self):
        """Initialize ChromaDB client and collection."""
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_PERSIST_DIR)
        )
        self.chroma_client.delete_collection(settings.COLLECTION_NAME)
        # Get or create collection with the specific embedding function
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.COLLECTION_NAME,
                embedding_function=embedding_func,  # Explicitly set this
                metadata={"hnsw:space": "cosine"}
            )
        except Exception as e:
            print(f"ChromaDB Initialization Error: {e}")
            raise e
    
    def add_context(self, session_id: str, markdown_text: str, structured_data: dict, diet_plan: str, patient_profile: str):
        """Add all three contexts to the vector database."""
        documents = []
        metadatas = []
        ids = []
        
        # Add markdown (unstructured) context
        # Chunking the markdown to avoid token limits if it's too long
        # Simple chunking by 1000 characters for safety
        chunk_size = 1000
        text_chunks = [markdown_text[i:i+chunk_size] for i in range(0, len(markdown_text), chunk_size)]
        
        for idx, chunk in enumerate(text_chunks):
            documents.append(chunk)
            documents.append(f"Patient Profile:\n{patient_profile}")
            metadatas.append({
                "session_id": session_id,
                "context_type": "unstructured_ocr",
                "source": "medical_report",
                "chunk_index": idx
            })
            ids.append(f"{session_id}_markdown_{idx}_{uuid.uuid4()}")
        
        # Add structured data context
        structured_text = f"Structured Medical Data:\n{str(structured_data)}"
        documents.append(structured_text)
        metadatas.append({
            "session_id": session_id,
            "context_type": "structured_data",
            "source": "extracted_data"
        })
        ids.append(f"{session_id}_structured_{uuid.uuid4()}")
        
        # Add diet plan context
        diet_text = f"Generated Diet Plan:\n{diet_plan}"
        documents.append(diet_text)
        metadatas.append({
            "session_id": session_id,
            "context_type": "diet_plan",
            "source": "generated_plan"
        })
        ids.append(f"{session_id}_diet_{uuid.uuid4()}")
        
        # Add to collection
        self.collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
    
    def query_context(self, session_id: str, query: str, n_results: int = 3) -> List[str]:
        """Query relevant context from the vector database."""
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"session_id": session_id}
            )
            
            if results and results['documents']:
                # Flatten list of lists
                return [doc for sublist in results['documents'] for doc in sublist]
            return []
        except Exception as e:
            print(f"Query Error: {e}")
            return []
    
    def chat(self, session_id: str, user_message: str, chat_history: List[Dict] = None) -> str:
        """Generate a chat response using RAG."""
        if chat_history is None:
            chat_history = []
        
        # Retrieve relevant context
        relevant_docs = self.query_context(session_id, user_message, n_results=3)
        context = "\n\n".join(relevant_docs) if relevant_docs else "No specific context found."
        
        # Build messages for LLM
        messages = [
            {
                "role": "system",
                "content": f"""You are a helpful medical assistant specializing in diet and nutrition. 
You have access to the patient's medical report, extracted data, and their personalized diet plan.

Use the following context to answer questions:
{context}

Guidelines:
- Provide helpful, accurate information based on the context
- Be empathetic and supportive
- If asked about specific medical values, refer to the structured data
- If asked about diet recommendations, refer to the diet plan
- Do not provide medical diagnoses or prescribe medications
- Encourage users to consult healthcare professionals for medical advice
"""
            }
        ]
        
        # Add chat history (limit to last 4 messages to save context window)
        messages.extend(chat_history[-4:])
        
        # Add current user message
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        try:
            # Generate response
            response = client.chat.completions.create(
                model=settings.CHAT_MODEL,
                messages=messages,
                temperature=0.7
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq API Error: {e}")
            return "I apologize, but I encountered an error while processing your request. Please try again."
    
    def clear_session(self, session_id: str):
        """Clear all data for a specific session."""
        try:
            self.collection.delete(
                where={"session_id": session_id}
            )
        except Exception as e:
            print(f"Error clearing session: {e}")

# Create a singleton instance
rag_chat = RAGChat()