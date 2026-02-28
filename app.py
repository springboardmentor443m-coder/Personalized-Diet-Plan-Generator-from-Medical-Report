"""Streamlit frontend for the AI Diet Plan Generator."""

import asyncio
import logging
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title="AI Diet Plan Generator",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

from config.settings import (
    ALLOWED_EXTENSIONS,
    MAX_FILE_SIZE_MB,
    MAX_DOCUMENTS_PER_SESSION,
)
from services.file_service import FileValidationError
from services.report_service import process_multiple_reports, PipelineError
from services.diet_service import generate_diet_from_results

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger(__name__)


#  Validate uploaded files (lightweight — UI-level check)
def _validate_file(f) -> str | None:
    """Return error string or None if valid."""
    ext = Path(f.name).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return f"**{f.name}**: Unsupported format `{ext}`. Use PDF, JPG, JPEG, or PNG."
    size_mb = len(f.getvalue()) / (1024 * 1024)
    if size_mb > MAX_FILE_SIZE_MB:
        return f"**{f.name}**: File too large ({size_mb:.1f} MB). Max {MAX_FILE_SIZE_MB} MB."
    return None


#  Display helpers
def _format_test_name(key: str) -> str:
    return key.replace("_", " ").title() if key else "—"


def _render_patient_info(pi: dict):
    """Render patient information in a nice column layout."""
    if not pi or not any(pi.values()):
        st.info("No patient information found in the report.")
        return

    cols = st.columns(4)
    field_map = [
        ("Name", pi.get("patient_name")),
        ("Age", f"{pi['age_years']} years" if pi.get("age_years") else None),
        ("Gender", pi.get("gender")),
        ("Report Date", pi.get("report_datetime") or pi.get("report_date")),
        ("Lab / Hospital", pi.get("lab_name") or pi.get("hospital_name")),
        ("Referring Doctor", pi.get("referring_doctor")),
    ]
    for idx, (label, val) in enumerate(field_map):
        if val:
            with cols[idx % 4]:
                st.metric(label=label, value=str(val))


def _render_tests_table(tests: dict):
    """Render lab tests as a styled table."""
    if not tests:
        st.info("No test results extracted.")
        return

    import pandas as pd

    rows = []
    for key, test in tests.items():
        interp = test.get("interpretation", "—")
        rows.append({
            "Test": _format_test_name(key),
            "Value": test.get("value", "—"),
            "Units": test.get("units") or test.get("unit", "—"),
            "Reference Range": test.get("reference_range") or test.get("ref_range", "—"),
            "Status": interp,
        })

    df = pd.DataFrame(rows)

    def _style_status(val):
        color_map = {"normal": "#059669", "low": "#d97706", "high": "#dc2626", "critical": "#dc2626"}
        bg_map = {"normal": "#d1fae5", "low": "#fef3c7", "high": "#fee2e2", "critical": "#fee2e2"}
        v = val.lower() if isinstance(val, str) else ""
        color = color_map.get(v, "#64748b")
        bg = bg_map.get(v, "#f1f5f9")
        return f"background-color: {bg}; color: {color}; font-weight: 600; border-radius: 12px; text-align: center;"

    styled = df.style.map(_style_status, subset=["Status"])
    st.dataframe(styled, width='stretch', hide_index=True, height=min(400, 40 + 35 * len(rows)))


def _render_abnormal_findings(findings: list):
    """Render abnormal findings as warning boxes."""
    if not findings:
        return

    st.subheader("⚠️ Abnormal Findings")
    for f in findings:
        name = _format_test_name(f.get("canonical_test_key") or f.get("test_key", "?"))
        val = f.get("observed_value") or f.get("value", "?")
        units = f.get("units", "")
        interp = f.get("interpretation") or f.get("severity", "abnormal")
        ref = f.get("reference_range", "")

        severity = interp.lower()
        if "critical" in severity or severity == "high":
            st.error(f"**{name}**: {val} {units} — {interp} {f'(ref: {ref})' if ref else ''}")
        else:
            st.warning(f"**{name}**: {val} {units} — {interp} {f'(ref: {ref})' if ref else ''}")


def _render_bmi(bmi_data):
    """Render BMI card."""
    if not bmi_data or not isinstance(bmi_data, dict) or not bmi_data.get("bmi_value"):
        return

    st.subheader("⚖️ Body Mass Index (BMI)")
    bmi_val = bmi_data["bmi_value"]
    classification = bmi_data.get("classification") or bmi_data.get("category", "")
    height = bmi_data.get("height_cm", "?")
    weight = bmi_data.get("weight_kg", "?")

    col1, col2 = st.columns([1, 3])
    with col1:
        if bmi_val < 18.5:
            color = "orange"
        elif bmi_val < 25:
            color = "green"
        elif bmi_val < 30:
            color = "orange"
        else:
            color = "red"
        st.markdown(f"<h1 style='color:{color}; text-align:center;'>{bmi_val}</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"**{classification}**")
        st.caption(f"Height: {height} cm · Weight: {weight} kg")


def _render_diet_plan(diet_plan: dict, safety: dict | None):
    """Render the full diet plan."""
    if not diet_plan:
        st.error("No diet plan was generated.")
        return

    reasoning = diet_plan.get("clinical_reasoning")
    if reasoning:
        with st.expander("🧠 Clinical Reasoning", expanded=False):
            if isinstance(reasoning, dict):
                for key, val in reasoning.items():
                    st.markdown(f"**{_format_test_name(key)}**")
                    if isinstance(val, list):
                        for item in val:
                            st.markdown(f"- {item}")
                    else:
                        st.write(val)
            elif isinstance(reasoning, str):
                st.write(reasoning)

    targets = (
        diet_plan.get("daily_nutrition_targets")
        or diet_plan.get("nutrition_summary")
        or diet_plan.get("daily_targets")
        or diet_plan.get("dietary_guidelines", {}).get("daily_nutrition_targets")
        or {}
    )

    if targets:
        st.subheader("📊 Daily Nutrition Targets")
        items = [
            ("Calories", targets.get("calories") or targets.get("total_calories"), "kcal"),
            ("Protein", targets.get("protein") or targets.get("protein_g"), "g"),
            ("Carbs", targets.get("carbohydrates") or targets.get("carbs") or targets.get("carbohydrates_g"), "g"),
            ("Fat", targets.get("fat") or targets.get("fat_g") or targets.get("fats"), "g"),
            ("Fiber", targets.get("fiber") or targets.get("fiber_g"), "g"),
            ("Sodium", targets.get("sodium") or targets.get("sodium_mg"), "mg"),
        ]
        visible = [(l, v, u) for l, v, u in items if v is not None]
        if visible:
            cols = st.columns(len(visible))
            for idx, (label, val, unit) in enumerate(visible):
                with cols[idx]:
                    st.metric(label=f"{label} ({unit})", value=str(val))

    if safety:
        st.subheader("🛡️ Safety Assessment")
        is_safe = safety.get("safe", True)
        if is_safe:
            st.success("✅ Diet plan passed all safety checks.")
        else:
            st.error("⚠️ Safety concerns detected — review warnings below.")

        warnings_list = safety.get("warnings", [])
        for w in warnings_list:
            w_type = w.get("type") or w.get("severity", "info") if isinstance(w, dict) else "info"
            msg = w.get("message") or w.get("description") or str(w) if isinstance(w, dict) else str(w)
            if "critical" in str(w_type).lower() or w_type == "error":
                st.error(f"🚨 {msg}")
            elif "warn" in str(w_type).lower() or w_type == "caution":
                st.warning(f"⚠️ {msg}")
            else:
                st.info(f"ℹ️ {msg}")

    st.subheader("🍽️ Your Personalized Meal Plan")

    # Try weekly meal plan first, then daily
    weekly = diet_plan.get("weekly_meal_plan", {})
    meals = diet_plan.get("meals") or diet_plan.get("meal_plan", [])

    meal_icons = {
        "breakfast": "🌅", "mid-morning snack": "🍎", "morning snack": "🍎",
        "lunch": "☀️", "afternoon snack": "🥜", "evening snack": "🥜",
        "snack": "🥜", "dinner": "🌙", "bedtime snack": "🌜",
    }

    if weekly and isinstance(weekly, dict):
        # Weekly plan — show tabs per day
        days = list(weekly.keys())
        if days:
            tabs = st.tabs([d.title() if isinstance(d, str) else str(d) for d in days])
            for tab, day in zip(tabs, days):
                with tab:
                    day_data = weekly[day]
                    day_meals = []
                    if isinstance(day_data, dict):
                        day_meals = day_data.get("meals", [])
                        if not day_meals:
                            # Maybe the day_data itself is meals keyed by name
                            day_meals = [
                                {"meal_name": k, **(v if isinstance(v, dict) else {"items": [v]})}
                                for k, v in day_data.items()
                                if k != "daily_totals"
                            ]
                    elif isinstance(day_data, list):
                        day_meals = day_data

                    for meal in day_meals:
                        _render_single_meal(meal, meal_icons)

                    totals = day_data.get("daily_totals") if isinstance(day_data, dict) else None
                    if totals:
                        st.caption(f"Day total: ~{totals.get('calories', '?')} kcal")

    elif isinstance(meals, list) and meals:
        for meal in meals:
            _render_single_meal(meal, meal_icons)

    elif isinstance(meals, dict) and meals:
        for name, meal in meals.items():
            meal_data = meal if isinstance(meal, dict) else {"items": [meal]}
            meal_data["meal_name"] = name
            _render_single_meal(meal_data, meal_icons)
    else:
        # Fallback: show raw plan
        st.json(diet_plan)

    guidelines = diet_plan.get("dietary_guidelines", {})
    if isinstance(guidelines, dict):
        _render_guidelines_section(guidelines, "foods_to_increase", "✅ Foods to Increase", st.success)
        _render_guidelines_section(guidelines, "foods_to_limit", "⚠️ Foods to Limit", st.warning)
        _render_guidelines_section(guidelines, "foods_to_avoid", "🚫 Foods to Avoid", st.error)

        special = guidelines.get("special_instructions") or guidelines.get("special_considerations")
        if special:
            st.subheader("📋 Special Instructions")
            if isinstance(special, list):
                for s in special:
                    st.info(f"• {s}" if isinstance(s, str) else f"• {s}")
            elif isinstance(special, str):
                st.info(special)

    recs = (
        diet_plan.get("recommendations")
        or diet_plan.get("dietary_recommendations")
        or diet_plan.get("general_recommendations")
        or diet_plan.get("guidelines")
    )
    if recs:
        st.subheader("💡 General Recommendations")
        if isinstance(recs, list):
            for r in recs:
                txt = r if isinstance(r, str) else (r.get("recommendation") or r.get("description", str(r)))
                st.markdown(f"- {txt}")
        elif isinstance(recs, dict):
            for k, v in recs.items():
                st.markdown(f"**{_format_test_name(k)}**: {v if isinstance(v, str) else ', '.join(v) if isinstance(v, list) else v}")
        elif isinstance(recs, str):
            st.write(recs)

    avoid = diet_plan.get("foods_to_avoid") or diet_plan.get("avoid") or diet_plan.get("restrictions")
    if avoid and not guidelines.get("foods_to_avoid"):
        st.subheader("🚫 Foods to Avoid or Limit")
        if isinstance(avoid, list):
            for a in avoid:
                txt = a if isinstance(a, str) else (a.get("food") or a.get("item", str(a)))
                st.markdown(f"- {txt}")
        elif isinstance(avoid, str):
            st.write(avoid)

    confidence = diet_plan.get("confidence_assessment")
    if confidence:
        with st.expander("📊 Confidence Assessment", expanded=False):
            if isinstance(confidence, dict):
                for k, v in confidence.items():
                    st.markdown(f"**{_format_test_name(k)}**: {v}")
            else:
                st.write(confidence)

    st.divider()
    disclaimer = diet_plan.get("disclaimer", "")
    st.warning(
        "**⚠️ Medical Disclaimer**\n\n"
        + (disclaimer if disclaimer else
           "This diet plan is generated by AI based on your medical reports and is for "
           "informational purposes only. It is NOT a substitute for professional medical "
           "advice. Always consult your doctor or a registered dietitian before making "
           "dietary changes, especially if you have chronic conditions or are on medication.")
    )


def _render_single_meal(meal: dict, icons: dict):
    """Render one meal block."""
    name = meal.get("meal_name") or meal.get("name") or meal.get("meal", "Meal")
    icon = icons.get(name.lower(), "🍽️")
    timing = meal.get("time") or meal.get("timing", "")
    cals = meal.get("calories") or meal.get("estimated_calories", "")
    items = meal.get("items") or meal.get("foods") or meal.get("food_items", [])
    notes = meal.get("notes", "")

    header = f"{icon} **{name}**"
    if cals:
        header += f" · ~{cals} kcal"
    if timing:
        header += f" · ⏰ {timing}"

    with st.container():
        st.markdown(header)
        if isinstance(items, list):
            for item in items:
                if isinstance(item, str):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {item}")
                elif isinstance(item, dict):
                    food = item.get("name") or item.get("food") or str(item)
                    qty = item.get("quantity") or item.get("portion") or item.get("amount", "")
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {food}" + (f" — {qty}" if qty else ""))
        if notes:
            st.caption(f"💡 {notes}")
        st.markdown("---")


def _render_guidelines_section(guidelines: dict, key: str, title: str, display_fn):
    """Render a foods_to_increase / foods_to_limit / foods_to_avoid section."""
    data = guidelines.get(key)
    if not data:
        return
    st.subheader(title)
    if isinstance(data, list):
        for item in data:
            if isinstance(item, str):
                display_fn(f"• {item}")
            elif isinstance(item, dict):
                food = item.get("food") or item.get("name") or item.get("category", "")
                reason = item.get("reason") or item.get("rationale", "")
                display_fn(f"**{food}**" + (f": {reason}" if reason else ""))
    elif isinstance(data, dict):
        for cat, items in data.items():
            display_fn(f"**{_format_test_name(cat)}**: {', '.join(items) if isinstance(items, list) else items}")


#  Main App
def main():
    if "analysis_done" not in st.session_state:
        st.session_state.analysis_done = False
    if "diet_done" not in st.session_state:
        st.session_state.diet_done = False
    if "results" not in st.session_state:
        st.session_state.results = None
    if "diet_data" not in st.session_state:
        st.session_state.diet_data = None
    if "active_tab" not in st.session_state:
        st.session_state.active_tab = "📄 Upload Reports"
    if "manual_height" not in st.session_state:
        st.session_state.manual_height = None
    if "manual_weight" not in st.session_state:
        st.session_state.manual_weight = None

    with st.sidebar:
        st.image("https://img.icons8.com/color/96/heart-health.png", width=64)
        st.title("🏥 AI Diet Planner")
        st.markdown(
            "Upload your medical reports and get a **personalized diet plan** "
            "powered by AI analysis of your lab results."
        )
        st.divider()
        st.markdown("##### How it works")
        st.markdown(
            "1. 📄 **Upload** reports by category\n"
            "2. ⚖️ **Calculate** your BMI\n"
            "3. 🔬 **AI extracts** all test results\n"
            "4. 🧪 **Review** lab data & flags\n"
            "5. 🥗 **Generate** a personalized diet plan"
        )
        st.divider()
        st.markdown("##### Supported Formats")
        st.markdown("PDF, JPG, JPEG, PNG — up to 20 MB each")

        st.divider()
        st.markdown("##### ⚖️ BMI Calculator")

        with st.expander("🧭 Calculate Your BMI", expanded=False):
            unit_sys = st.radio(
                "Units",
                ["Metric", "Imperial"],
                horizontal=True,
                key="_sb_bmi_units",
            )

            if unit_sys == "Metric":
                sb_height = st.number_input(
                    "Height (cm)",
                    min_value=50.0, max_value=250.0,
                    value=st.session_state.manual_height or 170.0,
                    step=0.5, key="_sb_h_cm",
                )
                sb_weight = st.number_input(
                    "Weight (kg)",
                    min_value=10.0, max_value=300.0,
                    value=st.session_state.manual_weight or 70.0,
                    step=0.5, key="_sb_w_kg",
                )
                h_cm, w_kg = sb_height, sb_weight
            else:
                ft_c, in_c = st.columns(2)
                with ft_c:
                    sb_ft = st.number_input("Feet", 1, 8, 5, key="_sb_ft")
                with in_c:
                    sb_in = st.number_input("Inches", 0, 11, 7, key="_sb_in")
                h_cm = round((sb_ft * 12 + sb_in) * 2.54, 1)
                sb_lbs = st.number_input(
                    "Weight (lbs)",
                    min_value=20.0, max_value=660.0,
                    value=154.0, step=1.0, key="_sb_lbs",
                )
                w_kg = round(sb_lbs * 0.453592, 1)

            bmi_live = round(w_kg / ((h_cm / 100) ** 2), 2)
            if bmi_live < 18.5:
                bmi_lbl, bmi_clr = "Underweight", "🟡"
            elif bmi_live < 25:
                bmi_lbl, bmi_clr = "Normal", "🟢"
            elif bmi_live < 30:
                bmi_lbl, bmi_clr = "Overweight", "🟠"
            else:
                bmi_lbl, bmi_clr = "Obese", "🔴"

            st.metric("BMI", f"{bmi_live}", delta=bmi_lbl, delta_color="off")
            st.caption(f"{bmi_clr} {h_cm} cm · {w_kg} kg")

            if st.button("💾 Save BMI", key="_sb_save_bmi", type="primary"):
                st.session_state.manual_height = h_cm
                st.session_state.manual_weight = w_kg
                st.success(f"Saved! BMI = {bmi_live}")
            elif st.session_state.manual_height and st.session_state.manual_weight:
                saved = round(
                    st.session_state.manual_weight / ((st.session_state.manual_height / 100) ** 2), 2
                )
                st.caption(f"✅ Saved BMI: **{saved}**")

        st.divider()
        st.caption("v0.3.0 · Powered by Groq AI")

    st.markdown(
        "<h1 style='text-align:center; margin-bottom:0;'>🏥 AI-Powered Diet Plan Generator</h1>"
        "<p style='text-align:center; color:#64748b; margin-top:4px;'>"
        "Upload medical reports → Extract lab data → Get personalized diet recommendations"
        "</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    TAB_OPTIONS = ["📄 Upload Reports", "🧪 Lab Results", "🥗 Diet Plan"]
    # Ensure active_tab is valid (in case it was set to BMI Calculator previously)
    if st.session_state.active_tab not in TAB_OPTIONS:
        st.session_state.active_tab = TAB_OPTIONS[0]
    active_tab = st.radio(
        "Navigate",
        TAB_OPTIONS,
        index=TAB_OPTIONS.index(st.session_state.active_tab),
        horizontal=True,
        label_visibility="collapsed",
        key="_nav_radio",
    )
    # Sync radio selection back to session state
    if active_tab != st.session_state.active_tab:
        st.session_state.active_tab = active_tab
        st.rerun()

    st.markdown("---")

    # ═══════════════════════════════════════════════════════════
    #  TAB 1: Upload (Categorized)
    # ═══════════════════════════════════════════════════════════
    if active_tab == "📄 Upload Reports":
        st.subheader("Upload Medical Reports")
        st.markdown(
            "Upload your documents into the appropriate category below. "
            "The AI will **auto-verify** your selection after processing."
        )

        UPLOAD_CATEGORIES = [
            {
                "key": "lab_report",
                "label": "🧪 Lab Reports",
                "desc": "Blood tests, urine analysis, lipid panels, HbA1c, CBC, LFT, KFT, thyroid panels, etc.",
                "icon": "🧪",
            },
            {
                "key": "diagnosis",
                "label": "📋 Diagnosis / Clinical Summaries",
                "desc": "Doctor's diagnosis, clinical impressions, ICD codes, specialist opinions.",
                "icon": "📋",
            },
            {
                "key": "prescription",
                "label": "💊 Prescriptions",
                "desc": "Medication prescriptions, drug dosages, pharmacy records.",
                "icon": "💊",
            },
            {
                "key": "discharge_summary",
                "label": "🏥 Discharge Summaries & Other",
                "desc": "Hospital discharge papers, admission summaries, or any other medical documents.",
                "icon": "🏥",
            },
        ]

        all_categorized_files: list[tuple] = []  # list of (file, user_declared_type)

        col_left, col_right = st.columns(2)

        for idx, cat in enumerate(UPLOAD_CATEGORIES):
            target_col = col_left if idx % 2 == 0 else col_right
            with target_col:
                with st.container(border=True):
                    st.markdown(f"**{cat['label']}**")
                    st.caption(cat["desc"])
                    files = st.file_uploader(
                        f"Upload {cat['label']}",
                        type=["pdf", "jpg", "jpeg", "png"],
                        accept_multiple_files=True,
                        key=f"upload_{cat['key']}",
                        label_visibility="collapsed",
                    )
                    if files:
                        for f in files:
                            all_categorized_files.append((f, cat["key"]))
                        st.caption(f"{len(files)} file(s) added")

        if all_categorized_files:
            st.divider()
            total_files = len(all_categorized_files)

            cat_counts = {}
            for _, cat_key in all_categorized_files:
                cat_counts[cat_key] = cat_counts.get(cat_key, 0) + 1

            cat_icons = {"lab_report": "🧪", "diagnosis": "📋", "prescription": "💊", "discharge_summary": "🏥"}
            summary_parts = [f"{cat_icons.get(k, '📄')} {k.replace('_', ' ').title()}: {v}" for k, v in cat_counts.items()]

            st.markdown(f"**📊 Upload Summary — {total_files} file(s):** &nbsp; " + " &nbsp;|&nbsp; ".join(summary_parts))

            with st.expander("View all files", expanded=False):
                for f, cat_key in all_categorized_files:
                    size = len(f.getvalue()) / 1024
                    unit = "KB"
                    if size > 1024:
                        size /= 1024
                        unit = "MB"
                    ficon = "📑" if f.name.lower().endswith(".pdf") else "🖼️"
                    st.markdown(
                        f"{ficon} `{f.name}` — {size:.1f} {unit} "
                        f"&nbsp; {cat_icons.get(cat_key, '📄')} *{cat_key.replace('_', ' ').title()}*"
                    )

            errors = []
            for f, _ in all_categorized_files:
                err = _validate_file(f)
                if err:
                    errors.append(err)

            if total_files > MAX_DOCUMENTS_PER_SESSION:
                errors.append(f"Too many files ({total_files}). Maximum {MAX_DOCUMENTS_PER_SESSION} allowed.")

            if errors:
                for e in errors:
                    st.error(e)
            else:
                st.divider()
                col1, col2 = st.columns(2)

                with col1:
                    analyze_btn = st.button(
                        "🔬 Analyze Reports",
                        type="secondary",
                        help="Extract lab data from your reports",
                    )

                with col2:
                    diet_btn = st.button(
                        "🥗 Analyze & Generate Diet Plan",
                        type="primary",
                        help="Extract data AND generate a personalized diet plan",
                    )

                if analyze_btn:
                    _run_analysis(all_categorized_files)

                if diet_btn:
                    _run_analysis(all_categorized_files)
                    if st.session_state.analysis_done:
                        _run_diet_generation()

        if st.session_state.analysis_done or st.session_state.diet_done:
            st.divider()
            if st.button("🔄 Start Over", type="secondary"):
                st.session_state.analysis_done = False
                st.session_state.diet_done = False
                st.session_state.results = None
                st.session_state.diet_data = None
                st.session_state.manual_height = None
                st.session_state.manual_weight = None
                st.session_state.active_tab = "📄 Upload Reports"
                st.rerun()

    # ═══════════════════════════════════════════════════════════
    #  TAB 2: Lab Results
    # ═══════════════════════════════════════════════════════════
    elif active_tab == "🧪 Lab Results":
        if not st.session_state.analysis_done:
            st.info("👈 Upload and analyze your reports first to see results here.")
        else:
            data = st.session_state.results
            is_multi = data.get("documents_processed") is not None

            proc_time = data.get("processing_time_seconds", "?")
            if is_multi:
                n_proc = data.get("documents_processed", 0)
                n_fail = data.get("documents_failed", 0)
                n_dup = data.get("documents_skipped_duplicate", 0)
                st.success(
                    f"✅ Processed **{n_proc}** document(s) in **{proc_time}s** "
                    + (f"| {n_fail} failed " if n_fail else "")
                    + (f"| {n_dup} duplicates skipped" if n_dup else "")
                )
            else:
                st.success(f"✅ Report analyzed in **{proc_time}s**")

            st.subheader("👤 Patient Information")
            _render_patient_info(data.get("patient_information", {}))

            st.subheader("🧪 Lab Test Results")
            if is_multi:
                tests = data.get("aggregated_tests") or data.get("tests_index", {})
            else:
                tests = data.get("tests_index", {})

            st.caption(f"{len(tests)} test(s) extracted")
            _render_tests_table(tests)

            if is_multi:
                abnormal = data.get("aggregated_abnormal_findings") or data.get("abnormal_findings", [])
            else:
                abnormal = data.get("abnormal_findings", [])
            _render_abnormal_findings(abnormal)

            _render_bmi(data.get("bmi"))

            # Per-document details (multi-doc)
            if is_multi and data.get("per_document_results"):
                # Check for category mismatches
                mismatches = [
                    doc for doc in data["per_document_results"]
                    if doc.get("user_declared_type") and doc.get("doc_type")
                    and doc["user_declared_type"] != doc["doc_type"]
                    and doc.get("status") == "processed"
                ]

                if mismatches:
                    st.subheader("🔀 Category Verification Warnings")
                    for doc in mismatches:
                        user_type = doc["user_declared_type"].replace("_", " ").title()
                        auto_type = doc["doc_type"].replace("_", " ").title()
                        st.warning(
                            f"**{doc.get('original_filename', '?')}** — "
                            f"You uploaded as *{user_type}*, but AI classified it as **{auto_type}**. "
                            f"The AI classification is used for processing."
                        )

                with st.expander("📋 Per-Document Details", expanded=False):
                    for doc in data["per_document_results"]:
                        status = doc.get("status", "?")
                        name = doc.get("original_filename", "?")
                        auto_type = doc.get("doc_type", "?")
                        user_type = doc.get("user_declared_type", "—")
                        status_icon = "✅" if status == "processed" else "❌" if status == "failed" else "⏭️"

                        cat_icons = {"lab_report": "🧪", "diagnosis": "📋", "prescription": "💊", "discharge_summary": "🏥"}
                        auto_icon = cat_icons.get(auto_type, "📄")
                        user_icon = cat_icons.get(user_type, "📄")

                        mismatch_badge = ""
                        if user_type and user_type != "—" and auto_type != "?" and user_type != auto_type:
                            mismatch_badge = " ⚠️ *mismatch*"

                        st.markdown(
                            f"{status_icon} **{name}** — "
                            f"Declared: {user_icon} `{user_type.replace('_', ' ')}` → "
                            f"Detected: {auto_icon} `{auto_type.replace('_', ' ')}`{mismatch_badge} "
                            f"| status: `{status}`"
                        )

            if data.get("chronic_flags"):
                with st.expander("🔄 Chronic Condition Flags", expanded=False):
                    for flag in data["chronic_flags"]:
                        st.warning(
                            f"**{_format_test_name(flag.get('test_key', '?'))}** — "
                            f"Abnormal in {flag.get('abnormal_count', '?')} reports "
                            f"over {flag.get('span_days', '?')} days"
                        )

            if data.get("conflicts"):
                with st.expander("⚡ Data Conflicts", expanded=False):
                    for c in data["conflicts"]:
                        st.info(
                            f"**{_format_test_name(c.get('test_key', '?'))}**: "
                            f"values {c.get('values', '?')} "
                            f"(diff: {c.get('percent_diff', '?')}%)"
                        )

            # Generate diet from results tab
            st.divider()
            if not st.session_state.diet_done:
                if st.button("🥗 Generate Diet Plan from These Results", type="primary"):
                    _run_diet_generation()

    # ═══════════════════════════════════════════════════════════
    #  TAB 3: Diet Plan
    # ═══════════════════════════════════════════════════════════
    elif active_tab == "🥗 Diet Plan":
        if not st.session_state.diet_done:
            if st.session_state.analysis_done:
                st.info("Click **Generate Diet Plan** in the Lab Results tab to create your diet plan.")
            else:
                st.info("👈 Upload and analyze your reports first, then generate a diet plan.")
        else:
            diet_data = st.session_state.diet_data
            diet_plan = diet_data.get("diet_plan")
            safety = diet_data.get("safety_checks")

            if not diet_plan:
                meta = diet_data.get("diet_generation_metadata", {})
                reason = meta.get("reason") or meta.get("error", "Unknown error")
                st.error(f"Could not generate diet plan: {reason}")
            else:
                _render_diet_plan(diet_plan, safety)

                meta = diet_data.get("diet_generation_metadata", {})
                if meta:
                    with st.expander("⚙️ Generation Details", expanded=False):
                        st.json(meta)


#  Pipeline runners
def _run_analysis(categorized_files):
    """Process uploaded files through the service layer.

    Parameters
    ----------
    categorized_files : list[tuple]
        List of (UploadedFile, user_declared_type) tuples.
    """
    progress_bar = st.progress(0, text="Starting analysis...")
    status_text = st.empty()

    # Convert Streamlit UploadedFiles → (filename, bytes) tuples
    raw_files: list[tuple[str, bytes]] = []
    user_types: list[str] = []
    for f, user_type in categorized_files:
        raw_files.append((f.name, f.getvalue()))
        user_types.append(user_type)

    status_text.markdown(f"🔄 Processing **{len(raw_files)}** document(s)...")
    progress_bar.progress(0.1, text="Processing documents...")

    try:
        # Call the shared service layer (async → run in event loop)
        loop = asyncio.new_event_loop()
        output = loop.run_until_complete(
            process_multiple_reports(raw_files, user_declared_types=user_types)
        )
        loop.close()
    except PipelineError as exc:
        progress_bar.progress(1.0, text="Error!")
        status_text.empty()
        st.error(f"Pipeline error: {exc}")
        return
    except Exception as exc:
        progress_bar.progress(1.0, text="Error!")
        status_text.empty()
        logger.error("Analysis failed: %s", exc)
        st.error(f"Analysis failed: {exc}")
        return

    progress_bar.progress(0.9, text="Finalising...")

    # Preserve successful docs for diet generation
    successful_docs = output.pop("_successful_docs", [])

    # Fallback: inject manual BMI if report didn't contain height/weight
    existing_bmi = output.get("bmi")
    if not existing_bmi or not isinstance(existing_bmi, dict) or not existing_bmi.get("bmi_value"):
        manual_h = st.session_state.get("manual_height")
        manual_w = st.session_state.get("manual_weight")
        if manual_h and manual_w:
            bmi_val = round(manual_w / ((manual_h / 100) ** 2), 2)
            if bmi_val < 18.5:
                cat = "Underweight"
            elif bmi_val < 25:
                cat = "Normal weight"
            elif bmi_val < 30:
                cat = "Overweight"
            else:
                cat = "Obese"
            output["bmi"] = {
                "bmi_value": bmi_val,
                "classification": cat,
                "category": cat,
                "height_cm": manual_h,
                "weight_kg": manual_w,
                "source": "manual_input",
            }
            logger.info("Using manual BMI: %.2f (%s)", bmi_val, cat)

    progress_bar.progress(1.0, text="Analysis complete!")

    st.session_state.results = output
    st.session_state._successful_docs = successful_docs
    st.session_state.analysis_done = True
    st.session_state.diet_done = False
    st.session_state.diet_data = None

    status_text.empty()
    n_proc = output.get("documents_processed", 0)
    elapsed = output.get("processing_time_seconds", 0)
    st.success(f"✅ Analysis complete — {n_proc} document(s) processed in {elapsed}s")

    # Auto-redirect to Lab Results tab
    st.session_state.active_tab = "🧪 Lab Results"
    st.rerun()


def _run_diet_generation():
    """Generate diet plan from previously analyzed results using the service layer."""
    if not st.session_state.analysis_done:
        st.error("Please analyze reports first.")
        return

    results = st.session_state.results
    successful_docs = st.session_state.get("_successful_docs", [])

    if not successful_docs:
        st.error("No successfully processed documents to generate a diet plan from.")
        return

    progress = st.progress(0, text="Preparing clinical context...")
    status = st.empty()

    try:
        status.markdown("🥗 **Generating personalized diet plan** (this may take 30-60 seconds)...")
        progress.progress(0.3, text="AI generating diet plan...")

        # Call the shared diet service
        diet_output = generate_diet_from_results(results, successful_docs)

        progress.progress(1.0, text="Diet plan ready!")

        st.session_state.diet_data = diet_output
        st.session_state.diet_done = True

        status.empty()
        if diet_output.get("diet_plan"):
            st.success("✅ Diet plan generated successfully!")
        else:
            meta = diet_output.get("diet_generation_metadata", {})
            reason = meta.get("reason") or meta.get("error", "Unknown error")
            st.error(f"Diet generation issue: {reason}")

        # Auto-redirect to Diet Plan tab
        st.session_state.active_tab = "🥗 Diet Plan"
        st.rerun()

    except Exception as exc:
        progress.progress(1.0, text="Error!")
        logger.error("Diet generation failed: %s", exc)
        st.session_state.diet_data = {
            "diet_plan": None,
            "safety_checks": None,
            "diet_generation_metadata": {
                "skipped": False,
                "error": str(exc),
            },
        }
        st.session_state.diet_done = True
        status.empty()
        st.error(f"Diet generation failed: {exc}")

        st.session_state.active_tab = "🥗 Diet Plan"
        st.rerun()


if __name__ == "__main__":
    main()
