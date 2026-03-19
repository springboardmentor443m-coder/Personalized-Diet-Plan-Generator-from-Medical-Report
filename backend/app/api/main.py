from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import os

from ..services.ocr_service import OCRService
from ..services.data_extractor import DataExtractor
from ..services.health_predictor import HealthPredictor
from ..services.diet_generator import DietPlanGenerator
from ..services.pdf_generator import PDFGenerator
import shutil
import json
import traceback

app = FastAPI(title="AI-NutriCare API")

os.makedirs("data/raw", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ocr = OCRService()
extractor = DataExtractor()
predictor = HealthPredictor()
diet_generator = DietPlanGenerator()
pdf_generator = PDFGenerator()

def calculate_bmi(height_cm, weight_kg):
    # BMI should come from height and weight whenever they are available.
    if not height_cm or not weight_kg:
        return None
    if height_cm <= 0 or weight_kg <= 0:
        return None
    return round(weight_kg / ((height_cm / 100) ** 2), 1)

@app.get("/")
def root():
    return {"message": "AI-NutriCare API", "status": "running"}

@app.post("/api/upload")
async def upload_report(file: UploadFile = File(...)):
    filename = file.filename or ""
    if not filename.endswith(('.pdf', '.png', '.jpg', '.jpeg')):
        raise HTTPException(400, "Only PDF and image files allowed")
    
    temp_path = f"data/raw/temp_{filename}"
    with open(temp_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        raw_text = ocr.process_file(temp_path)
        print(f"\n=== OCR EXTRACTED TEXT (first 500 chars) ===")
        print(raw_text[:500])
        
        extracted_data = extractor.process_report(raw_text)
        print(f"\n=== EXTRACTED DATA ===")
        print(f"Patient Info: {extracted_data.get('patient_info')}")
        print(f"Lab Values: {extracted_data.get('lab_values')}")
        
        ml_predictions = predictor.predict(extracted_data['lab_values'])
        recommendations = predictor.get_recommendations(ml_predictions)
        
        print(f"\n=== ML PREDICTIONS ===")
        print(json.dumps(ml_predictions, indent=2))
        
        extracted_data['ml_predictions'] = ml_predictions
        extracted_data['recommendations'] = recommendations
        
        if not extracted_data.get('doctor_notes') or len(extracted_data['doctor_notes']) == 0:
            from ..services.groq_service import GroqService
            groq = GroqService()
            ai_note = groq.generate_ai_doctor_note(extracted_data)
            extracted_data['doctor_notes'] = [f"[AI Generated] {ai_note}"]
            print(f"\n=== AI DOCTOR NOTE ===")
            print(ai_note)
        
        os.remove(temp_path)
        
        return {
            "success": True,
            "patient_info": extracted_data.get('patient_info', {}),
            "lab_values": extracted_data.get('lab_values', {}),
            "ml_predictions": ml_predictions,
            "recommendations": recommendations,
            "doctor_notes": extracted_data.get('doctor_notes', [])
        }
    
    except Exception as e:
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(500, f"Processing error: {str(e)}")

class GenerateRequest(BaseModel):
    extracted: Dict[str, Any]
    allergies: List[str]
    preferences: List[str]
    height: Optional[float] = None
    weight: Optional[float] = None
    activityLevel: str = 'moderate'

class ChatRequest(BaseModel):
    question: str
    extracted: Dict[str, Any]
    diet_plan: Dict[str, Any] = {}
    history: List[Dict[str, str]] = []

@app.post("/api/generate")
async def generate_diet(request: GenerateRequest):
    try:
        extracted = request.extracted
        extracted.setdefault('lab_values', {})

        # Recalculate BMI so the plan does not rely on an OCR-misread BMI value.
        height_value = request.height or extracted.get('lab_values', {}).get('height', {}).get('value')
        weight_value = request.weight or extracted.get('lab_values', {}).get('weight', {}).get('value')
        bmi = calculate_bmi(height_value, weight_value)

        if bmi is not None:
            extracted['lab_values']['bmi'] = {
                'value': bmi,
                'status': 'calculated',
                'label': 'BMI',
                'unit': ''
            }

        if request.height and request.weight:
            
            age = extracted.get('patient_info', {}).get('age', 30)
            gender = extracted.get('patient_info', {}).get('gender', 'M')
            
            if gender == 'M':
                bmr = 10 * request.weight + 6.25 * request.height - 5 * age + 5
            else:
                bmr = 10 * request.weight + 6.25 * request.height - 5 * age - 161
            
            activity_multipliers = {'sedentary': 1.2, 'light': 1.375, 'moderate': 1.55, 'active': 1.725}
            daily_calories = int(bmr * activity_multipliers.get(request.activityLevel, 1.2))
            
            conditions = []
            if extracted.get('lab_values', {}).get('hba1c', {}).get('value', 0) >= 6.5:
                conditions.append('diabetes')
                daily_calories -= 200
            cholesterol = extracted.get('lab_values', {}).get('cholesterol_total', {}).get('value', 0)
            if cholesterol >= 200:
                conditions.append('high_cholesterol')
                daily_calories -= 150
            if bmi is not None and bmi >= 30:
                conditions.append('obesity')
                daily_calories -= 300
            
            daily_calories = max(daily_calories, 1200)
            extracted['_calculated_calories'] = daily_calories
            extracted['_conditions'] = conditions
        else:
            extracted['_conditions'] = extracted.get('_conditions', [])
            if extracted.get('ml_predictions', {}).get('diabetes', {}).get('detected'):
                extracted['_conditions'].append('diabetes')
            if extracted.get('ml_predictions', {}).get('high_cholesterol', {}).get('detected'):
                extracted['_conditions'].append('high_cholesterol')
            extracted['_conditions'] = sorted(set(extracted['_conditions']))

        preference_set = set(request.preferences or [])
        selected_diet = 'Vegetarian'
        if 'Vegan' in preference_set:
            selected_diet = 'Vegan'
        elif 'Veg + Non-Veg' in preference_set:
            selected_diet = 'Veg + Non-Veg'
        elif 'Non-Veg' in preference_set:
            selected_diet = 'Non-Veg'
        
        prefs = {
            'vegetarian': selected_diet == 'Vegetarian',
            'non_veg': selected_diet in ['Non-Veg', 'Veg + Non-Veg'],
            'vegan': selected_diet == 'Vegan',
            'mixed_diet': selected_diet == 'Veg + Non-Veg',
            'allergies': [a.strip() for a in request.allergies if a and a.strip()]
        }
        
        print(f"\n=== GENERATING DIET PLAN ===")
        print(f"Preferences: {prefs}")
        print(f"Calculated Calories: {extracted.get('_calculated_calories')}")
        
        diet_result = diet_generator.generate(extracted, days=3, preferences=prefs)
        
        if 'diet_plan' in diet_result:
            diet_plan_raw = diet_result['diet_plan']
        else:
            diet_plan_raw = diet_result
        
        diet_plan_data = {k: v for k, v in diet_plan_raw.items() if not k.startswith('_')}
        calories = diet_plan_raw.get('_calories', extracted.get('_calculated_calories', 1800))
        distribution = diet_plan_raw.get('_distribution', {})
        macro_targets = diet_plan_raw.get('_macro_targets', {})
        patient_bmi = diet_plan_raw.get('_patient_bmi', extracted.get('lab_values', {}).get('bmi', {}).get('value'))
        generation_source = diet_plan_raw.get('_source', 'unknown')
        
        print(f"\n=== GENERATING PDF ===")
        pdf_path = "data/processed/diet_plan.pdf"
        try:
            pdf_generator.generate_diet_plan_pdf(extracted, diet_result, pdf_path)
            print("✓ PDF generated successfully")
        except Exception as pdf_error:
            print(f"⚠ PDF generation failed: {pdf_error}")
        
        return {
            "success": True,
            "patient_info": extracted.get('patient_info', {}),
            "lab_values": extracted.get('lab_values', {}),
            "ml_predictions": extracted.get('ml_predictions', {}),
            "diet_plan": {
                **diet_plan_data,
                '_calories': calories,
                '_distribution': distribution,
                '_macro_targets': macro_targets,
                '_patient_bmi': patient_bmi
            },
            "diet_generation_source": generation_source,
            "doctor_notes": extracted.get('doctor_notes', []),
            "conditions": extracted.get('_conditions', []),
            "pdf_ready": True
        }
    except Exception as e:
        import traceback
        print(f"\n=== FULL ERROR TRACEBACK ===")
        traceback.print_exc()
        print(f"Generation error: {e}")
        raise HTTPException(500, f"Generation error: {str(e)}")

@app.get("/api/download-pdf")
def download_pdf():
    pdf_path = "data/processed/diet_plan.pdf"
    if not os.path.exists(pdf_path):
        raise HTTPException(404, "PDF not found")
    return FileResponse(pdf_path, filename="diet_plan.pdf", media_type="application/pdf")

@app.post("/api/chat")
async def chat_with_assistant(request: ChatRequest):
    try:
        from ..services.groq_service import GroqService
        groq = GroqService()
        result = groq.answer_patient_question(
            request.question,
            health_data=request.extracted or {},
            diet_plan=request.diet_plan or {},
            history=request.history or []
        )
        return {
            "success": True,
            "answer": result.get("answer", ""),
            "source": result.get("source", "fallback")
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Chat error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
