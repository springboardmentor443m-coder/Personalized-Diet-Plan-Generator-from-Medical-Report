from fastapi import FastAPI, UploadFile, File
from modules.extractor import extract_text
from modules.utils import extract_metrics
from modules.ml_model import predict_condition
from modules.diet_generator import generate_diet

app = FastAPI()

@app.post("/analyze-report/")
async def analyze_report(file: UploadFile = File(...)):

    file_type = file.filename.split(".")[-1]

    contents = await file.read()

    extracted_text = extract_text(contents, file_type)

    metrics = extract_metrics(extracted_text)

    if not metrics:
        return {"error": "No metrics detected"}

    condition = predict_condition(metrics)

    diet = generate_diet(condition)

    return {
        "metrics": metrics,
        "condition": condition,
        "diet": diet
    }
