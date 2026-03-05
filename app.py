import gradio as gr
import json
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from extractor import process_file
from diet_planner import generate_diet_plan, calculate_bmi

# ─────────────────────────────────────────────
# VISUALIZATION: Abnormal Findings
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
    bars = ax.barh(labels, observed, color=colors, edgecolor="white", linewidth=0.5)
    ax.set_title("Abnormal Test Findings", fontsize=13, fontweight="bold", pad=12)
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
    fig.savefig("abnormal_plot.png", dpi=130)
    plt.close(fig)
    return "abnormal_plot.png"


# ─────────────────────────────────────────────
# VISUALIZATION: Category Summary
# ─────────────────────────────────────────────
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
    fig.savefig("category_plot.png", dpi=130)
    plt.close(fig)
    return "category_plot.png"


# ─────────────────────────────────────────────
# VISUALIZATION: BMI Gauge
# ─────────────────────────────────────────────
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
        ax.text((x_start + x_end) / 2, 0.25, label, ha="center", fontsize=8, color="black")

    ax.axvline(x=bmi, color="black", linewidth=3, ymin=0.2, ymax=0.9)
    ax.text(bmi, 0.95, f"BMI: {bmi}", ha="center", fontsize=11, fontweight="bold", color="black")
    ax.set_title(f"BMI Category: {category}", fontsize=12, fontweight="bold")

    plt.tight_layout()
    fig.savefig("bmi_plot.png", dpi=130)
    plt.close(fig)
    return "bmi_plot.png"


# ─────────────────────────────────────────────
# FORMAT: Diet Plan Tab
# ─────────────────────────────────────────────
def format_diet(diet: dict) -> str:
    lines = []
    p = diet.get("patient_summary", {})
    lines.append(f"Patient  : {p.get('name')}  |  Age: {p.get('age')}  |  Gender: {p.get('gender')}")
    lines.append(f"BMI      : {p.get('bmi')} ({p.get('bmi_category')})")
    lines.append(f"Diet Type: {p.get('diet_type')}")
    lines.append(f"Concerns : {', '.join(p.get('key_concerns', []))}\n")

    nt = diet.get("nutrient_targets", {})
    lines.append("━━━ DAILY NUTRIENT TARGETS ━━━")
    lines.append(f"  Calories : {nt.get('daily_calories')} kcal  |  Protein : {nt.get('protein_g')}g")
    lines.append(f"  Carbs    : {nt.get('carbs_g')}g            |  Fats    : {nt.get('fats_g')}g")
    lines.append(f"  Fiber    : {nt.get('fiber_g')}g            |  Water   : {nt.get('water_liters')}L")
    lines.append(f"  Note     : {nt.get('notes', '')}\n")

    lines.append("━━━ FOODS TO AVOID ━━━")
    for item in diet.get("foods_to_avoid", []):
        lines.append(f"  [X]  {item['food']}  —  {item['reason']}")

    lines.append("\n━━━ FOODS TO INCLUDE ━━━")
    for item in diet.get("foods_to_include", []):
        lines.append(f"  [+]  {item['food']}  —  {item['benefit']}")

    lines.append("\n━━━ 7-DAY MEAL PLAN ━━━")
    for day, meals in diet.get("weekly_meal_plan", {}).items():
        lines.append(f"\n  {day.upper()}")
        lines.append(f"    Breakfast     : {meals.get('breakfast', '-')}")
        lines.append(f"    Mid-Morning   : {meals.get('mid_morning', '-')}")
        lines.append(f"    Lunch         : {meals.get('lunch', '-')}")
        lines.append(f"    Evening Snack : {meals.get('evening_snack', '-')}")
        lines.append(f"    Dinner        : {meals.get('dinner', '-')}")
        lines.append(f"    Bedtime       : {meals.get('bedtime', '-')}")

    lines.append("\n━━━ LIFESTYLE TIPS ━━━")
    for tip in diet.get("lifestyle_tips", []):
        lines.append(f"  ->  {tip}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# FORMAT: Supplements Tab
# ─────────────────────────────────────────────
def format_supplements(diet: dict) -> str:
    lines = ["━━━ RECOMMENDED SUPPLEMENTS ━━━\n"]
    for s in diet.get("supplements", []):
        lines.append(f"  Name         : {s.get('name')}")
        lines.append(f"  Dosage       : {s.get('dosage')}")
        lines.append(f"  Reason       : {s.get('reason')}")
        lines.append(f"  Indian Brand : {s.get('indian_brand', 'Available at medical stores')}")
        lines.append("")

    lines.append("\n━━━ ZERO SUGAR PRODUCTS ━━━\n")
    for p in diet.get("zero_sugar_products", []):
        lines.append(f"  Product  : {p.get('product_name')}  ({p.get('brand')})")
        lines.append(f"  Category : {p.get('category')}")
        lines.append(f"  Why      : {p.get('why_recommended')}")
        lines.append("")

    lines.append("\n━━━ INDIAN BRAND SUGGESTIONS ━━━\n")
    for b in diet.get("indian_brand_suggestions", []):
        lines.append(f"  Product    : {b.get('product')}  —  {b.get('brand')}")
        lines.append(f"  Available  : {b.get('available_at')}")
        lines.append(f"  Benefit    : {b.get('benefit')}")
        lines.append("")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# FORMAT: Hydration Tab
# ─────────────────────────────────────────────
def format_hydration(diet: dict) -> str:
    h = diet.get("hydration_detox_plan", {})
    lines = ["━━━ HYDRATION & DETOX PLAN ━━━\n"]
    lines.append(f"  Morning Ritual  : {h.get('morning_ritual', '-')}")
    lines.append(f"  During Meals    : {h.get('during_meals', '-')}")
    lines.append(f"  Post Workout    : {h.get('post_workout', '-')}")
    lines.append(f"  Evening         : {h.get('evening', '-')}")
    lines.append(f"  Weekly Detox Day: {h.get('weekly_detox_day', '-')}\n")
    lines.append("  Detox Drinks:")
    for d in h.get("detox_drinks", []):
        lines.append(f"    - {d}")
    lines.append("\n  Detox Foods:")
    for f in h.get("foods_for_detox", []):
        lines.append(f"    - {f}")
    return "\n".join(lines)


# ─────────────────────────────────────────────
# MAIN PIPELINE
# ─────────────────────────────────────────────
def run_pipeline(file, diet_type, height, weight, age, gender, allergies):
    if file is None:
        return ("No file uploaded.", "", "", "", None, None, None)

    # Step 1: OCR + Extract
    raw_json_str = process_file(file)
    if raw_json_str.startswith("ERROR") or raw_json_str.startswith("OCR"):
        return (raw_json_str, "", "", "", None, None, None)

    report = json.loads(raw_json_str)

    # Step 2: BMI
    bmi_data = calculate_bmi(float(weight), float(height))
    bmi_summary = (
        f"BMI: {bmi_data['bmi']}  |  Category: {bmi_data['category']}\n"
        f"Advice: {bmi_data['advice']}"
    )

    # Step 3: User preferences
    user_prefs = {
        "diet_type": diet_type,
        "height_cm": float(height),
        "weight_kg": float(weight),
        "age": int(age),
        "gender": gender,
        "allergies": allergies if allergies else "None",
        "bmi_data": bmi_data
    }

    # Step 4: Generate diet plan
    diet = generate_diet_plan(report, user_prefs)
    with open("diet_output.json", "w", encoding="utf-8") as f:
        json.dump(diet, f, indent=2)

    # Step 5: Format outputs
    diet_text        = format_diet(diet)
    supplements_text = format_supplements(diet)
    hydration_text   = format_hydration(diet)

    # Step 6: Charts
    chart_abnormal  = plot_abnormal(report)
    chart_category  = plot_categories(report)
    chart_bmi       = plot_bmi(bmi_data)

    return (diet_text, bmi_summary, supplements_text, hydration_text,
            chart_bmi, chart_abnormal, chart_category)


# ─────────────────────────────────────────────
# GRADIO UI — TABBED LAYOUT
# ─────────────────────────────────────────────
with gr.Blocks(title="AI Diet Plan Generator") as demo:

    gr.Markdown("""
    # 🩺 AI Medical Diet Plan Generator
    ### Upload your lab report → Get a personalized, medically-informed 7-day diet plan
    ---
    """)

    # ── INPUT SECTION ──
    with gr.Row():
        with gr.Column(scale=1):
            gr.Markdown("### 📂 Upload Report")
            file_input = gr.File(label="Medical Report (PDF / Image / TXT)")

        with gr.Column(scale=2):
            gr.Markdown("### 👤 Patient Preferences")
            with gr.Row():
                diet_type = gr.Radio(["Vegetarian", "Non-Vegetarian"],
                                     label="Diet Type", value="Vegetarian")
                gender    = gr.Radio(["Male", "Female", "Other"],
                                     label="Gender", value="Male")
            with gr.Row():
                height = gr.Number(label="Height (cm)", value=170)
                weight = gr.Number(label="Weight (kg)", value=70)
                age    = gr.Number(label="Age (years)", value=30)
            allergies = gr.Textbox(label="Food Allergies / Intolerances (optional)",
                                   placeholder="e.g. lactose, gluten, nuts")

    submit_btn = gr.Button("🚀 Generate My Diet Plan", variant="primary", size="lg")

    # ── OUTPUT TABS ──
    with gr.Tabs():

        with gr.Tab("🥗 Diet Plan"):
            diet_output = gr.Textbox(label="Your Personalized 7-Day Diet Plan", lines=45)

        with gr.Tab("📊 BMI & Charts"):
            bmi_summary = gr.Textbox(label="BMI Result", lines=3)
            bmi_chart   = gr.Image(label="BMI Scale")
            with gr.Row():
                chart_abnormal = gr.Image(label="Abnormal Findings")
                chart_category = gr.Image(label="Category-wise Summary")

        with gr.Tab("💊 Supplements & Products"):
            supplements_output = gr.Textbox(label="Supplements, Zero Sugar & Indian Brand Suggestions", lines=40)

        with gr.Tab("💧 Hydration & Detox"):
            hydration_output = gr.Textbox(label="Hydration & Detox Plan", lines=25)

    submit_btn.click(
        fn=run_pipeline,
        inputs=[file_input, diet_type, height, weight, age, gender, allergies],
        outputs=[diet_output, bmi_summary, supplements_output, hydration_output,
                 bmi_chart, chart_abnormal, chart_category]
    )

if __name__ == "__main__":
    demo.launch()