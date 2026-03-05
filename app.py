from flask import Flask, render_template, request, jsonify, send_file
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from extractor import process_file, clean_json
from diet_planner import generate_diet_plan, calculate_bmi

app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ─────────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────────
def plot_abnormal(report: dict):
    abnormal = report.get("abnormal_findings", [])
    tests = report.get("tests_index", {})
    if not abnormal:
        return None

    labels, observed, colors = [], [], []
    for item in abnormal:
        key = item.get("canonical_test_key", "")
        name = tests.get(key, {}).get("test_name", key)[:22]
        val = item.get("observed_value")
        sev = item.get("severity", "high")
        if isinstance(val, (int, float)):
            labels.append(name)
            observed.append(val)
            colors.append("crimson" if sev == "critical" else "orange" if sev == "high" else "gold")

    if not labels:
        return None

    fig, ax = plt.subplots(figsize=(10, max(4, len(labels) * 0.7)))
    bars = ax.barh(labels, observed, color=colors, edgecolor="white")
    ax.set_title("Abnormal Test Findings", fontsize=13, fontweight="bold")
    ax.set_xlabel("Observed Value")
    for bar, val in zip(bars, observed):
        ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                str(val), va="center", fontsize=9)
    patches = [
        mpatches.Patch(color="crimson", label="Critical"),
        mpatches.Patch(color="orange",  label="High"),
        mpatches.Patch(color="gold",    label="Low"),
    ]
    ax.legend(handles=patches)
    plt.tight_layout()
    path = "static/abnormal_plot.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_categories(report: dict):
    by_cat = report.get("tests_by_category", {})
    tests  = report.get("tests_index", {})

    categories, normal_counts, abnormal_counts = [], [], []
    for cat, keys in by_cat.items():
        if not keys:
            continue
        normal = sum(1 for k in keys if tests.get(k, {}).get("interpretation") == "normal")
        categories.append(cat.replace("_", " ").title())
        normal_counts.append(normal)
        abnormal_counts.append(len(keys) - normal)

    if not categories:
        return None

    x = np.arange(len(categories))
    width = 0.4
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.bar(x - width/2, normal_counts,   width, label="Normal",   color="seagreen")
    ax.bar(x + width/2, abnormal_counts, width, label="Abnormal", color="tomato")
    ax.set_xticks(x)
    ax.set_xticklabels(categories, rotation=30, ha="right", fontsize=9)
    ax.set_ylabel("Number of Tests")
    ax.set_title("Category-wise Test Summary", fontsize=13, fontweight="bold")
    ax.legend()
    plt.tight_layout()
    path = "static/category_plot.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def plot_bmi(bmi_data: dict):
    bmi = bmi_data["bmi"]
    category = bmi_data["category"]

    fig, ax = plt.subplots(figsize=(8, 2.5))
    ax.set_xlim(10, 45)
    ax.set_ylim(0, 1)
    ax.axis("off")

    zones = [(10, 18.5, "#4fc3f7", "Underweight"),
             (18.5, 25, "#81c784", "Normal"),
             (25, 30, "#ffb74d", "Overweight"),
             (30, 45, "#e57373", "Obese")]

    for x_start, x_end, color, label in zones:
        ax.barh(0.5, x_end - x_start, left=x_start, height=0.4, color=color, edgecolor="white")
        ax.text((x_start + x_end) / 2, 0.25, label, ha="center", fontsize=8)

    ax.axvline(x=bmi, color="black", linewidth=3, ymin=0.2, ymax=0.9)
    ax.text(bmi, 0.95, f"BMI: {bmi}", ha="center", fontsize=11, fontweight="bold")
    ax.set_title(f"BMI Category: {category}", fontsize=12, fontweight="bold")
    plt.tight_layout()
    path = "static/bmi_plot.png"
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


# ─────────────────────────────────────────────
# ROUTES
# ─────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    try:
        # ── Get form inputs ──
        file        = request.files.get("report_file")
        diet_type   = request.form.get("diet_type", "Vegetarian")
        height      = float(request.form.get("height", 170))
        weight      = float(request.form.get("weight", 70))
        age         = int(request.form.get("age", 30))
        gender      = request.form.get("gender", "Male")
        allergies   = request.form.get("allergies", "None")

        if not file:
            return jsonify({"error": "No file uploaded"}), 400

        # ── Save uploaded file ──
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        # ── Step 1: OCR + Extract ──
        class FileWrapper:
            def __init__(self, path):
                self.name = path

        raw_json_str = process_file(FileWrapper(file_path))
        if raw_json_str.startswith("ERROR") or raw_json_str.startswith("OCR"):
            return jsonify({"error": raw_json_str}), 500

        report = json.loads(raw_json_str)

        # ── Step 2: BMI ──
        bmi_data = calculate_bmi(weight, height)

        # ── Step 3: User preferences ──
        user_prefs = {
            "diet_type": diet_type,
            "height_cm": height,
            "weight_kg": weight,
            "age": age,
            "gender": gender,
            "allergies": allergies,
            "bmi_data": bmi_data
        }

        # ── Step 4: Generate diet plan ──
        diet = generate_diet_plan(report, user_prefs)

        # ── Step 5: Save outputs ──
        with open("output.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        with open("diet_output.json", "w", encoding="utf-8") as f:
            json.dump(diet, f, indent=2)

        # ── Step 6: Generate charts ──
        os.makedirs("static", exist_ok=True)
        plot_abnormal(report)
        plot_categories(report)
        plot_bmi(bmi_data)

        return jsonify({
            "success": True,
            "bmi": bmi_data,
            "diet": diet,
            "report": report
        })

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True, port=8080)