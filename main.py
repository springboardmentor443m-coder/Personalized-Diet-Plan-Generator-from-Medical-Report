from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Optional
import shutil
from pathlib import Path
import uuid

# --- Custom Modules ---
# These are the specific tools we built in the other files.
# main.py acts as the "Manager" that tells these tools when to work.
from backend.config import settings
from backend.ocr import process_document
from backend.extraction import extract_structured_data
from backend.diet_generator import generate_diet_plan, calculate_bmi
from backend.rag_chat_1 import rag_chat  # Importing our RAG system

# Initialize the API application
app = FastAPI(title="Diet Plan Generator API", version="1.0.0")

# --- CORS SETUP ---
# Security rule: "Who is allowed to talk to this server?"
# We allow "*" (everyone) so your React/Streamlit frontend can connect easily.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
# These define the strict shape of data we expect to receive.
# If the frontend sends data that doesn't match this (e.g., missing session_id),
# FastAPI will automatically reject it with an error.
class ChatMessage(BaseModel):
    session_id: str
    message: str
    chat_history: Optional[List[Dict]] = []

# --- SESSION STORAGE ---
# A simple dictionary to keep track of user sessions in RAM.
# Key = session_id, Value = {file_path, status, results...}
# WARNING: If you restart the server, this variable is wiped empty!
session_store = {}

@app.get("/")
def read_root():
    """Root endpoint just to check if the server is breathing."""
    return {
        "message": "Diet Plan Generator API",
        "version": "1.0.0",
        "endpoints": {
            "/upload": "POST - Upload medical document",
            "/process": "POST - Process document and generate diet plan",
            "/chat": "POST - Chat with RAG assistant",
            "/bmi": "POST - Calculate BMI",
            "/sessions": "GET - Get all sessions",
            "/clear-session/{session_id}": "DELETE - Clear session data"
        }
    }

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Step 1: Upload a medical document (PDF or image).
    - Checks if the file type is allowed.
    - Creates a unique ID (UUID) for this user session.
    - Saves the file physically to the 'uploads' folder.
    """
    # 1. Validate file extension (must be .pdf, .jpg, etc.)
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {settings.ALLOWED_EXTENSIONS}"
        )
    
    # 2. Create a unique Ticket ID for this user
    session_id = str(uuid.uuid4())
    
    # 3. Save the file to disk
    file_path = settings.UPLOAD_DIR / f"{session_id}_{file.filename}"
    with file_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # 4. Initialize the session in our dictionary
    session_store[session_id] = {
        "file_path": str(file_path),
        "filename": file.filename,
        "status": "uploaded"
    }
    
    # 5. Give the ID back to the Frontend so it can remember it
    return {
        "session_id": session_id,
        "filename": file.filename,
        "message": "File uploaded successfully"
    }

@app.post("/process")
async def process_and_generate(
    session_id: str = Form(...),
    age: int = Form(...),
    gender: str = Form(...),
    country: str = Form(...),
    weight: float = Form(...),
    height: float = Form(...),
    diet_preference: str = Form(...)
):
    """
    Step 2: The Core Logic Pipeline.
    This orchestrates the entire AI workflow:
    OCR -> Extraction -> Diet Plan -> RAG Indexing
    """
    # Check if the user actually uploaded a file first
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session_data = session_store[session_id]
    file_path = session_data["file_path"]
    
    try:
        # A. OCR: Convert PDF image to raw text
        print(f"Processing document: {file_path}")
        markdown_text = process_document(file_path)
        session_data["markdown_text"] = markdown_text
        
        # B. Extraction: Convert raw text to structured JSON
        print("Extracting structured data...")
        structured_data = extract_structured_data(markdown_text)
        session_data["structured_data"] = structured_data
        
        # C. BMI: Calculate health metrics
        bmi_info = calculate_bmi(weight, height)
        session_data["bmi"] = bmi_info
        
        # D. Diet Plan: Ask AI to write a meal plan based on the data
        print("Generating diet plan...")
        diet_plan = generate_diet_plan(
            structured_data=structured_data,
            age=age,
            gender=gender,
            country=country,
            weight=weight,
            height=height,
            diet_preference=diet_preference
        )
        session_data["diet_plan"] = diet_plan
        session_data["status"] = "complete"
        
        # E. Patient Profile String:
        # We create a readable summary of the patient's inputs (Age, Weight, etc.)
        # so we can save it to the RAG system too.
        patient_profile_str = f"""
        Patient Profile:
        - Age: {age}
        - Gender: {gender}
        - Height: {height} cm
        - Weight: {weight} kg
        - Country: {country}
        - Diet Preference: {diet_preference}
        - Calculated BMI: {bmi_info['bmi']} ({bmi_info['category']})
        """
        
        # F. RAG Indexing: Save EVERYTHING to the Vector Database
        # This allows the chatbot to answer questions about the report, diet, OR patient stats.
        print("Adding context to RAG system...")
        rag_chat.add_context(
            session_id=session_id,
            markdown_text=markdown_text,
            structured_data=structured_data,
            patient_profile=patient_profile_str, # <--- Passing the profile here
            diet_plan=diet_plan
        )
        
        return {
            "session_id": session_id,
            "status": "success",
            "bmi": bmi_info,
            "structured_data": structured_data,
            "diet_plan": diet_plan,
            "message": "Processing complete"
        }
        
    except Exception as e:
        session_data["status"] = "error"
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/bmi")
async def calculate_bmi_endpoint(weight: float = Form(...), height: float = Form(...)):
    """Helper endpoint to calculate BMI without doing a full analysis."""
    try:
        bmi_info = calculate_bmi(weight, height)
        return bmi_info
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/chat")
async def chat_endpoint(chat_request: ChatMessage):
    """
    Step 3: The Chatbot.
    Receives a message + session_id, queries the Vector DB, and returns an answer.
    """
    try:
        if chat_request.session_id not in session_store:
            raise HTTPException(status_code=404, detail="Session not found")
        
        # Send query to our RAG module
        response = rag_chat.chat(
            session_id=chat_request.session_id,
            user_message=chat_request.message,
            chat_history=chat_request.chat_history
        )
        
        return {
            "response": response,
            "session_id": chat_request.session_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")

@app.get("/sessions")
async def get_sessions():
    """Debug endpoint: See how many users are currently in memory."""
    return {
        "sessions": list(session_store.keys()),
        "total": len(session_store)
    }

@app.delete("/clear-session/{session_id}")
async def clear_session(session_id: str):
    """
    Cleanup endpoint.
    Called when a user leaves the app or starts over.
    Deletes the file, the memory entry, and the vector DB entries.
    """
    if session_id not in session_store:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # 1. Clear Vector DB
    rag_chat.clear_session(session_id)
    
    # 2. Delete Physical File
    if "file_path" in session_store[session_id]:
        file_path = Path(session_store[session_id]["file_path"])
        if file_path.exists():
            file_path.unlink()
    
    # 3. Clear RAM
    del session_store[session_id]
    
    return {"message": "Session cleared successfully"}

@app.get("/health")
async def health_check():
    """
    Health Check.
    Used by cloud platforms (like AWS/Render) to see if the app crashed.
    """
    return {
        "status": "healthy",
        "groq_api_configured": bool(settings.GROQ_API_KEY),
        "upload_dir_exists": settings.UPLOAD_DIR.exists(),
        "chroma_dir_exists": settings.CHROMA_PERSIST_DIR.exists()
    }

# --- SERVER START ---
# This block runs only if you type `python main.py` directly.
# Usually, we run `uvicorn main:app`, so this is just a backup.
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)