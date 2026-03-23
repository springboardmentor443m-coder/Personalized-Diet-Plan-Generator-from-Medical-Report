import chromadb
from chromadb.utils import embedding_functions
from typing import List, Dict, Optional
from groq import Groq
from backend.config import settings
import uuid
import os

# Initialize the Groq client using the API key from our settings
client = Groq(api_key=settings.GROQ_API_KEY)

# --- 1. SETUP EMBEDDINGS ---
# This initializes the "Translator" for our database.
# It converts text (like "Apple") into numbers (vectors like [0.1, 0.5, ...])
# We use 'all-MiniLM-L6-v2' because it's fast, free, and runs locally on your CPU.
embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

class RAGChat:
    def __init__(self):
        """Initialize ChromaDB client and collection."""
        # Connect to the local database folder where vectors will be stored
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_PERSIST_DIR)
        )
        
        # Optional: Reset DB on startup for testing (Uncomment to wipe old data)
        # try: self.chroma_client.delete_collection(settings.COLLECTION_NAME)
        # except: pass

        # Get the specific 'table' (Collection) for our medical reports
        # If it doesn't exist, create it.
        try:
            self.collection = self.chroma_client.get_or_create_collection(
                name=settings.COLLECTION_NAME,
                embedding_function=embedding_func,
                metadata={"hnsw:space": "cosine"} # Use Cosine similarity for search
            )
        except Exception as e:
            print(f"ChromaDB Initialization Error: {e}")
            raise e

    def add_context(self, 
                    session_id: str, 
                    markdown_text: str, 
                    structured_data: dict, 
                    diet_plan: str,
                    patient_profile: str = ""): # <--- Added patient_profile default
        """
        Add context to the vector database safely.
        This function takes the raw text, diet plan, and user info,
        converts them into searchable vectors, and saves them.
        """
        
        # Initialize empty lists - strictly 1:1:1 mapping
        # We need three lists of equal length: The Text, The Metadata tags, and the Unique IDs.
        documents = []
        metadatas = []
        ids = []

        # --- PART A: Add OCR Text (Chunked) ---
        # The PDF text might be huge, so we chop it into smaller pieces (1000 chars).
        # This helps the AI find specific paragraphs later.
        chunk_size = 1000
        text_chunks = [markdown_text[i:i+chunk_size] for i in range(0, len(markdown_text), chunk_size)]
        
        for idx, chunk in enumerate(text_chunks):
            documents.append(chunk)
            # Tag this chunk with the session_id so we don't mix up users
            metadatas.append({
                "session_id": session_id,
                "context_type": "unstructured_ocr",
                "source": "medical_report",
                "chunk_index": idx
            })
            # Create a unique ID like "User123_markdown_0_randomUUID"
            ids.append(f"{session_id}_markdown_{idx}_{uuid.uuid4()}")

        # --- PART B: Add Structured Data ---
        # Convert the JSON data (Lab values) into a string string so the AI can read it.
        structured_text = f"Structured Medical Data:\n{str(structured_data)}"
        documents.append(structured_text)
        metadatas.append({
            "session_id": session_id,
            "context_type": "structured_data",
            "source": "extracted_data",
            "chunk_index": 0
        })
        ids.append(f"{session_id}_structured_{uuid.uuid4()}")

        # --- PART C: Add Diet Plan ---
        # Add the generated diet plan to the searchable knowledge base.
        diet_text = f"Generated Diet Plan:\n{diet_plan}"
        documents.append(diet_text)
        metadatas.append({
            "session_id": session_id,
            "context_type": "diet_plan",
            "source": "generated_plan",
            "chunk_index": 0
        })
        ids.append(f"{session_id}_diet_{uuid.uuid4()}")

        # --- PART D: Add Patient Profile (if provided) ---
        # Add age, weight, height info so the AI knows who it's talking to.
        if patient_profile:
            documents.append(f"Patient Profile:\n{patient_profile}")
            metadatas.append({
                "session_id": session_id,
                "context_type": "patient_profile",
                "source": "user_input",
                "chunk_index": 0
            })
            ids.append(f"{session_id}_profile_{uuid.uuid4()}")

        # --- DEBUG CHECK ---
        # Ensure we didn't mess up the alignment of our lists before saving.
        if not (len(documents) == len(metadatas) == len(ids)):
            print(f"ERROR: Length Mismatch! Docs: {len(documents)}, Metas: {len(metadatas)}, IDs: {len(ids)}")
            return # Stop before crashing

        # Add to collection (This is where the actual saving happens)
        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            print(f"Successfully added {len(documents)} items to ChromaDB.")
        except Exception as e:
            print(f"Error adding to ChromaDB: {e}")
            raise e

    def query_context(self, session_id: str, query: str, n_results: int = 3) -> List[str]:
        """
        Query relevant context from the vector database.
        This searches the DB for the 3 most relevant paragraphs to the user's question.
        Crucially, it filters by 'session_id' so users only see their own data.
        """
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where={"session_id": session_id} # <--- The Firewall: Only show User X their own data
            )
            
            if results and results['documents']:
                # Flatten the list of lists into a single list of strings
                return [doc for sublist in results['documents'] for doc in sublist]
            return []
        except Exception as e:
            print(f"Query Error: {e}")
            return []

    def chat(self, session_id: str, user_message: str, chat_history: List[Dict] = None) -> str:
        """
        Generate a chat response using RAG.
        1. Search DB for context.
        2. Construct a prompt for the LLM.
        3. Get answer from Groq.
        """
        if chat_history is None:
            chat_history = []
        
        # Step 1: Retrieve relevant context
        relevant_docs = self.query_context(session_id, user_message, n_results=3)
        context = "\n\n".join(relevant_docs) if relevant_docs else "No specific context found."
        
        # Step 2: Build the prompt with System Instructions + Context + Chat History
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
        
        # Add recent chat history so the bot remembers the conversation flow
        messages.extend(chat_history[-4:])
        
        # Add the user's current question
        messages.append({
            "role": "user",
            "content": user_message
        })
        
        # Step 3: Call the LLM (Groq) to generate the answer
        try:
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
        """
        Clear all data for a specific session.
        Removes vectors from the database to keep it clean.
        """
        try:
            self.collection.delete(where={"session_id": session_id})
        except Exception as e:
            print(f"Error clearing session: {e}")

# Create a singleton instance so the app reuses the same DB connection
rag_chat = RAGChat()