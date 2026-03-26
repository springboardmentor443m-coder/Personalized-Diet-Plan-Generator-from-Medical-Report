from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from typing import Optional
from pydantic import BaseModel

from database import engine, get_db
import models_auth, schemas, auth

models_auth.Base.metadata.create_all(bind=engine)

from modules.extractor import extract_text
from modules.utils import extract_metrics, extract_metrics_from_json
from modules.ml_model import predict_condition
from modules.diet_generator import generate_diet
from modules.llm_extractor import extract_structured_data
from modules.bmi_calculator import calculate_bmi
from modules.pdf_exporter import generate_pdf

app = FastAPI()

# Γ£à Allow React / Frontend Access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change later for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DownloadPayload(BaseModel):
    structured_data: Optional[dict] = None
    diet: Optional[dict] = None
    user_info: Optional[dict] = None

class ChatPayload(BaseModel):
    query: str
    structured_data: Optional[dict] = None
    diet: Optional[dict] = None
    chat_history: Optional[list] = None

@app.post("/chat/")
def chat_agent(payload: ChatPayload):
    from modules.rag_chatbot import generate_chat_response
    try:
        reply = generate_chat_response(
            query=payload.query, 
            structured_data=payload.structured_data, 
            diet=payload.diet, 
            chat_history=payload.chat_history
        )
        return {"success": True, "reply": reply}
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/download-report/")
def download_report(payload: DownloadPayload):
    try:
        pdf_buffer = generate_pdf(payload.structured_data, payload.diet, payload.user_info)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": "attachment; filename=DietPlan.pdf"}
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-report/")
async def analyze_report(
    file: UploadFile = File(...),
    patient_name: Optional[str] = Form(None),
    age: Optional[int] = Form(None),
    gender: Optional[str] = Form(None),
    weight: Optional[float] = Form(None),
    height: Optional[float] = Form(None)
):

    try:
        # Γ£à Safety Checks
        if file is None or not file.filename:
            return {"error": "Invalid file"}

        # Γ£à File Type Detection
        file_type = file.filename.split(".")[-1].lower()

        # Γ£à Extract Text
        extracted_text = extract_text(file.file, file_type)

        # Γ£à Structure the Biomarker Context (Gemini)
        structured_data = extract_structured_data(extracted_text) or {}

        # Γ£à Synthesize Physical Metrics (BMI)
        bmi_data = calculate_bmi(weight, height)
        
        # Merge if payload exists
        if bmi_data:
             if "patient_information" not in structured_data:
                 structured_data["patient_information"] = {}
             
             if patient_name:
                 structured_data["patient_information"]["patient_name"] = patient_name
                 
             structured_data["patient_information"]["age_years"] = age
             structured_data["patient_information"]["gender"] = gender
             structured_data["patient_information"]["weight_kg"] = weight
             structured_data["patient_information"]["height_cm"] = height
             structured_data["patient_information"]["calculated_bmi"] = bmi_data["bmi_value"]
             structured_data["patient_information"]["bmi_category"] = bmi_data["bmi_category"]

        # Γ£à Map the structured schema array into the flat dict required by ML tools
        metrics = extract_metrics_from_json(structured_data) if structured_data else {}
        
        # Γ£à Fallback: If AI failed to find tests, try robust regex scanning
        if not metrics:
            metrics = extract_metrics(extracted_text)

        # Γ£à Automatically Compute Abnormal Findings if missing or empty
        if structured_data:
            abnormal = structured_data.get("abnormal_findings", [])
            # If the LLM returned it as None or an empty list, explicitly regenerate it
            if not abnormal:
                computed_abnormal = []
                tests = structured_data.get("tests_index", {})
                for t_key, t_val in tests.items():
                    interp = str(t_val.get("interpretation") or "").strip().lower()
                    if interp in ["low", "high", "critical", "borderline", "abnormal"] and interp != "normal":
                        computed_abnormal.append({
                            "canonical_test_key": t_key,
                            "observed_value": t_val.get("value", "--"),
                            "expected_range": t_val.get("reference_range", "--"),
                            "severity": interp
                        })
                structured_data["abnormal_findings"] = computed_abnormal

        # Γ£à Prediction + Diet Logic (Phase 3 pending)
        if metrics:
            condition = predict_condition(metrics)
            diet = generate_diet(condition, metrics, structured_data)
        else:
            condition = "Insufficient Data"
            diet = generate_diet(None, metrics, structured_data)

        return {
            "success": True,
            "structured_data": structured_data,
            "condition": condition,
            "metrics": metrics,
            "diet": diet
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@app.post("/signup", response_model=schemas.UserResponse)
def signup(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = auth.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models_auth.User(
        email=user.email,
        full_name=user.full_name,
        hashed_password=hashed_password
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@app.post("/login", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = auth.get_user_by_email(db, email=form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = auth.timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=schemas.UserResponse)
def read_users_me(current_user: models_auth.User = Depends(auth.get_current_user)):
    return current_user
