"""
app.py - AI-NutriCare Flask Web Application
- Uploading medical reports (PDF/images)
- Extracting structured data using MedicalDocumentProcessor
- Generating personalized diet plans using DietPlanGenerator
- Visualizing results with matplotlib charts
"""

import os
import json
import traceback
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from flask import Flask, render_template, request, jsonify

# Local imports – adjust paths as needed
from report_parser import MedicalDocumentProcessor, clean_json
from diet_planner import DietPlanGenerator, compute_bmi_metrics

# ----------------------------------------------------------------------
# Flask app configuration
# ----------------------------------------------------------------------
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB limit
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs("static", exist_ok=True)


# ----------------------------------------------------------------------
# Chart generation functions (adapted with minor changes)
# ----------------------------------------------------------------------
def create_abnormal_chart(extracted_data: dict) -> str:
    """
    Generate a horizontal bar chart of abnormal findings.
    Returns the file path of the saved image.
    """
    abnormal = extracted_data.get("abnormal_results", [])
    tests = extracted_data.get("lab_results", {})

    if not abnormal:
        return None

    labels, values, colors = [], [], []
    for item in abnormal:
        test_key = item.get("test_key", "")
        test_info = tests.get(test_key, {})
        test_name = test_info.get("test_name", test_key)[:25]
        val = item.get("measured_value")
        severity = item.get("severity", "moderate")

        try:
            val_float = float(val)
        except (TypeError, ValueError):
            continue

        labels.append(test_name)
        values.append(val_float)
        if severity == "severe":
            colors.append("#d62728")      # dark red
        elif severity == "moderate":
            colors.append("#ff7f0e")      # orange
        else:
            colors.append("#ffbb78")      # light orange (mild)

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(9, max(3, len(labels) * 0.6)))
    bars = ax.barh(labels, values, color=colors, edgecolor="white")
    ax.set_title("Abnormal Lab Results", fontsize=13, fontweight="bold")
    ax.set_xlabel("Measured Value")

    # Add value labels
    for bar, val in zip(bars, values):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height()/2,
                f"{val}", va="center", fontsize=9)

    # Legend for severity
    legend_patches = [
        mpatches.Patch(color="#d62728", label="Severe"),
        mpatches.Patch(color="#ff7f0e", label="Moderate"),
        mpatches.Patch(color="#ffbb78", label="Mild"),
    ]
    ax.legend(handles=legend_patches, loc="best")
    plt.tight_layout()

    filepath = "static/abnormal_chart.png"
    fig.savefig(filepath, dpi=120)
    plt.close(fig)
    return filepath


def create_category_chart(extracted_data: dict) -> str:
    """
    Generate a grouped bar chart showing normal vs abnormal per category.
    """
    categories = extracted_data.get("test_categories", {})
    tests = extracted_data.get("lab_results", {})

    cat_names, normal_counts, abnormal_counts = [], [], []
    for cat, test_keys in categories.items():
        if not test_keys:
            continue
        norm = 0
        abn = 0
        for key in test_keys:
            test = tests.get(key, {})
            flag = test.get("flag")
            if flag in ("low", "high", "critical"):
                abn += 1
            else:
                norm += 1
        if norm + abn > 0:
            cat_names.append(cat.replace("_", " ").title())
            normal_counts.append(norm)
            abnormal_counts.append(abn)

    if not cat_names:
        return None

    x = np.arange(len(cat_names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - width/2, normal_counts, width, label="Normal", color="#2ca02c")
    ax.bar(x + width/2, abnormal_counts, width, label="Abnormal", color="#d62728")
    ax.set_xticks(x)
    ax.set_xticklabels(cat_names, rotation=25, ha="right", fontsize=9)
    ax.set_ylabel("Number of Tests")
    ax.set_title("Test Results by Category", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()

    filepath = "static/category_chart.png"
    fig.savefig(filepath, dpi=120)
    plt.close(fig)
    return filepath


def create_bmi_gauge(bmi_info: dict) -> str:
    """
    Draw a horizontal color bar with a marker for the patient's BMI.
    """
    bmi = bmi_info["bmi"]
    category = bmi_info["category"]

    fig, ax = plt.subplots(figsize=(8, 2.2))
    ax.set_xlim(10, 45)
    ax.set_ylim(0, 1)
    ax.axis("off")

    # Color zones
    zones = [
        (10, 18.5, "#66b3ff", "Underweight"),
        (18.5, 25, "#99ff99", "Normal"),
        (25, 30, "#ffcc99", "Overweight"),
        (30, 45, "#ff9999", "Obese")
    ]

    for start, end, color, label in zones:
        ax.barh(0.5, end - start, left=start, height=0.4,
                color=color, edgecolor="white", linewidth=1)
        ax.text((start + end) / 2, 0.2, label, ha="center", fontsize=8)

    # BMI marker
    ax.axvline(x=bmi, color="black", linewidth=3, ymin=0.2, ymax=0.8)
    ax.text(bmi, 0.9, f"{bmi}", ha="center", fontsize=11, fontweight="bold")

    ax.set_title(f"BMI: {bmi} – {category}", fontsize=12, fontweight="bold")
    plt.tight_layout()

    filepath = "static/bmi_gauge.png"
    fig.savefig(filepath, dpi=120)
    plt.close(fig)
    return filepath


# ----------------------------------------------------------------------
# Flask Routes
# ----------------------------------------------------------------------
@app.route("/")
def home():
    """Render the main upload page."""
    return render_template("index.html")


@app.route("/process", methods=["POST"])
def process_report():
    """
    Handle file upload, run extraction and diet planning, return JSON.
    """
    try:
        # Retrieve form data
        uploaded_file = request.files.get("report")
        if not uploaded_file:
            return jsonify({"error": "No file provided"}), 400

        diet_pref = request.form.get("diet", "vegetarian")
        height_cm = float(request.form.get("height", 170))
        weight_kg = float(request.form.get("weight", 70))
        patient_age = request.form.get("age")
        patient_gender = request.form.get("gender", "unspecified")
        allergies = request.form.get("allergies", "")

        # Save uploaded file temporarily
        file_path = os.path.join(app.config["UPLOAD_FOLDER"], uploaded_file.filename)
        uploaded_file.save(file_path)

        # --------------------------------------------------------------
        # Step 1: Extract data from medical report
        # --------------------------------------------------------------
        doc_processor = MedicalDocumentProcessor(max_workers=2)
        extracted = doc_processor.process_document(file_path)

        if "error" in extracted:
            return jsonify({"error": extracted["error"]}), 500

        # --------------------------------------------------------------
        # Step 2: Calculate BMI
        # --------------------------------------------------------------
        bmi_result = compute_bmi_metrics(weight_kg, height_cm)

        # --------------------------------------------------------------
        # Step 3: Generate diet plan
        # --------------------------------------------------------------
        user_prefs = {
            "diet_type": diet_pref,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "age": patient_age,
            "gender": patient_gender,
            "allergies": allergies
        }
        diet_generator = DietPlanGenerator()
        diet_plan = diet_generator.generate_plan(extracted, user_prefs)

        if "error" in diet_plan:
            return jsonify({"error": diet_plan["error"]}), 500

        # --------------------------------------------------------------
        # Step 4: Generate visual charts
        # --------------------------------------------------------------
        abnormal_path = create_abnormal_chart(extracted)
        category_path = create_category_chart(extracted)
        bmi_path = create_bmi_gauge(bmi_result)

        # --------------------------------------------------------------
        # Step 5: Save outputs (optional, for reference)
        # --------------------------------------------------------------
        with open("output/latest_report.json", "w", encoding="utf-8") as f:
            json.dump(extracted, f, indent=2)
        with open("output/latest_diet.json", "w", encoding="utf-8") as f:
            json.dump(diet_plan, f, indent=2)

        # --------------------------------------------------------------
        # Return JSON response with all data
        # --------------------------------------------------------------
        return jsonify({
            "status": "success",
            "bmi": bmi_result,
            "extracted": extracted,
            "diet_plan": diet_plan,
            "charts": {
                "abnormal": abnormal_path,
                "category": category_path,
                "bmi": bmi_path
            }
        })

    except Exception as e:
        traceback.print_exc()
        return jsonify({"error": f"Server error: {str(e)}"}), 500


# ----------------------------------------------------------------------
# Run the application
# ----------------------------------------------------------------------
if __name__ == "__main__":
    # Ensure output directory exists
    Path("output").mkdir(exist_ok=True)
    app.run(debug=True, host="0.0.0.0", port=5050)