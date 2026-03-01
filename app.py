"""Streamlit frontend for the AI Diet Plan Generator."""

import asyncio
import json
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
    """Render the full diet plan with all subsections."""
    if not diet_plan:
        st.error("No diet plan was generated.")
        return

    # ── Active preferences badge ──────────────────────────────
    active_prefs = st.session_state.get("dietary_preferences", {})
    if active_prefs:
        pref_badges = []
        dt = active_prefs.get("diet_type", "")
        dt_icons = {"veg": "🥬", "non_veg": "🍗", "vegan": "🌱", "eggetarian": "🥚"}
        if dt:
            pref_badges.append(f"{dt_icons.get(dt, '🍽️')} {dt.replace('_', '-').title()}")
        mf = active_prefs.get("meal_frequency", "")
        if mf:
            pref_badges.append(f"🕐 {mf.replace('_', ' ')}")
        cu = active_prefs.get("cuisine", "")
        if cu:
            pref_badges.append(f"🌍 {cu}")
        ct = active_prefs.get("calorie_target")
        if ct:
            pref_badges.append(f"🔥 {ct} kcal")
        al = active_prefs.get("allergies", [])
        if al:
            pref_badges.append(f"🚫 {', '.join(al)}")
        if pref_badges:
            st.info("**Preferences applied:** " + " · ".join(pref_badges))

    # ── Clinical Reasoning ────────────────────────────────────
    reasoning = diet_plan.get("clinical_reasoning")
    if reasoning and isinstance(reasoning, dict):
        with st.expander("🧠 Clinical Reasoning", expanded=False):
            # Primary concerns — render as severity-tagged cards
            concerns = reasoning.get("primary_concerns", [])
            if concerns and isinstance(concerns, list):
                st.markdown("**Primary Concerns**")
                for c in concerns:
                    if not isinstance(c, dict):
                        st.markdown(f"- {c}")
                        continue
                    sev = c.get("severity", "")
                    trend = c.get("trend", "")
                    concern = c.get("concern", "")
                    implication = c.get("dietary_implication", "")
                    labs = c.get("driving_lab_values", [])

                    sev_icon = {"mild": "🟡", "moderate": "🟠", "severe": "🔴", "critical": "🚨"}.get(sev, "⚪")
                    trend_icon = {"improving": "📈", "worsening": "📉", "stable": "➡️"}.get(trend, "")

                    line = f"{sev_icon} **{concern}** — {sev}"
                    if trend:
                        line += f" {trend_icon} {trend}"
                    if labs:
                        line += f" | Labs: {', '.join(labs)}"
                    st.markdown(line)
                    if implication:
                        st.caption(f"→ {implication}")

            # Comorbidity interactions
            interactions = reasoning.get("comorbidity_interactions", [])
            if interactions and isinstance(interactions, list):
                st.markdown("**Comorbidity Interactions**")
                for i in interactions:
                    if not isinstance(i, dict):
                        st.markdown(f"- {i}")
                        continue
                    conditions = i.get("conditions", [])
                    conflict = i.get("conflict_type", "")
                    resolution = i.get("resolution", "")
                    conf = i.get("confidence", "")
                    cond_str = " ↔ ".join(conditions) if isinstance(conditions, list) else str(conditions)
                    st.warning(f"**{cond_str}** — {conflict}")
                    if resolution:
                        st.caption(f"Resolution: {resolution} (confidence: {conf})")

            # Medication-diet interactions
            med_interactions = reasoning.get("medication_diet_interactions", [])
            if med_interactions and isinstance(med_interactions, list):
                st.markdown("**Medication–Diet Interactions**")
                for m in med_interactions:
                    if not isinstance(m, dict):
                        st.markdown(f"- {m}")
                        continue
                    med = m.get("medication", "")
                    consideration = m.get("dietary_consideration", "")
                    action = m.get("action", "")
                    st.info(f"💊 **{med}**: {consideration}")
                    if action:
                        st.caption(f"Action: {action}")

    elif reasoning and isinstance(reasoning, str):
        with st.expander("🧠 Clinical Reasoning", expanded=False):
            st.write(reasoning)

    # ── Dietary Guidelines ────────────────────────────────────
    guidelines = diet_plan.get("dietary_guidelines", {})
    if guidelines and isinstance(guidelines, dict):
        st.subheader("📊 Dietary Guidelines")

        # Caloric target + Macronutrient split — side by side
        caloric = guidelines.get("caloric_target", {})
        macro = guidelines.get("macronutrient_split", {})

        if caloric or macro:
            gc1, gc2 = st.columns(2)
            with gc1:
                if caloric and isinstance(caloric, dict):
                    range_kcal = caloric.get("range_kcal", "—")
                    rationale = caloric.get("rationale", "")
                    st.metric(label="🔥 Daily Calorie Target", value=str(range_kcal) + " kcal")
                    if rationale:
                        st.caption(rationale)
            with gc2:
                if macro and isinstance(macro, dict):
                    p = macro.get("protein_percent", "?")
                    c = macro.get("carbs_percent", "?")
                    f = macro.get("fat_percent", "?")
                    st.markdown(f"**Macronutrient Split**")
                    mc1, mc2, mc3 = st.columns(3)
                    with mc1:
                        st.metric("Protein", f"{p}%")
                    with mc2:
                        st.metric("Carbs", f"{c}%")
                    with mc3:
                        st.metric("Fat", f"{f}%")
                    rationale = macro.get("rationale", "")
                    if rationale:
                        st.caption(rationale)

        # Key nutrients to increase
        nutrients_up = guidelines.get("key_nutrients_to_increase", [])
        if nutrients_up and isinstance(nutrients_up, list):
            with st.expander("✅ Key Nutrients to Increase", expanded=False):
                for n in nutrients_up:
                    if isinstance(n, dict):
                        nutrient = n.get("nutrient", "")
                        reason = n.get("reason", "")
                        sources = n.get("food_sources", [])
                        st.success(f"**{nutrient}**: {reason}")
                        if sources:
                            st.caption(f"Sources: {', '.join(sources)}")
                    elif isinstance(n, str):
                        st.success(f"• {n}")

        # Key nutrients to limit
        nutrients_down = guidelines.get("key_nutrients_to_limit", [])
        if nutrients_down and isinstance(nutrients_down, list):
            with st.expander("⚠️ Key Nutrients to Limit", expanded=False):
                for n in nutrients_down:
                    if isinstance(n, dict):
                        nutrient = n.get("nutrient", "")
                        reason = n.get("reason", "")
                        max_daily = n.get("max_daily", "")
                        msg = f"**{nutrient}**: {reason}"
                        if max_daily:
                            msg += f" (max: {max_daily})"
                        st.warning(msg)
                    elif isinstance(n, str):
                        st.warning(f"• {n}")

        # Foods to avoid
        foods_avoid = guidelines.get("foods_to_avoid", [])
        if foods_avoid and isinstance(foods_avoid, list):
            with st.expander("🚫 Foods to Avoid", expanded=False):
                for f in foods_avoid:
                    if isinstance(f, dict):
                        food = f.get("food_or_category") or f.get("food") or f.get("name", "")
                        reason = f.get("reason", "")
                        severity = f.get("severity", "")
                        sev_icon = {"avoid_completely": "🔴", "limit_significantly": "🟠", "moderate": "🟡"}.get(severity, "⚠️")
                        st.error(f"{sev_icon} **{food}** — {reason}" + (f" [{severity.replace('_', ' ')}]" if severity else ""))
                    elif isinstance(f, str):
                        st.error(f"• {f}")

        # Foods to emphasize
        foods_emph = guidelines.get("foods_to_emphasize", [])
        if foods_emph and isinstance(foods_emph, list):
            with st.expander("💚 Foods to Emphasize", expanded=False):
                for f in foods_emph:
                    if isinstance(f, dict):
                        food = f.get("food_or_category") or f.get("food") or f.get("name", "")
                        reason = f.get("reason", "")
                        freq = f.get("frequency", "")
                        msg = f"**{food}**: {reason}"
                        if freq:
                            msg += f" — {freq}"
                        st.success(msg)
                    elif isinstance(f, str):
                        st.success(f"• {f}")

    # ── Safety Assessment ─────────────────────────────────────
    if safety:
        st.subheader("🛡️ Safety Assessment")
        is_safe = safety.get("safe", True)
        if is_safe:
            st.success("✅ Diet plan passed all safety checks.")
        else:
            st.error("⚠️ Safety concerns detected — review warnings below.")

        warnings_list = safety.get("warnings", [])
        if warnings_list:
            with st.expander(f"Safety Warnings ({len(warnings_list)})", expanded=not is_safe):
                for w in warnings_list:
                    w_sev = w.get("severity", "info") if isinstance(w, dict) else "info"
                    msg = w.get("message") or w.get("description") or str(w) if isinstance(w, dict) else str(w)
                    rec = w.get("recommendation", "") if isinstance(w, dict) else ""
                    if "critical" in str(w_sev).lower():
                        st.error(f"🚨 {msg}")
                    elif "high" in str(w_sev).lower():
                        st.warning(f"⚠️ {msg}")
                    else:
                        st.info(f"ℹ️ {msg}")
                    if rec:
                        st.caption(f"→ {rec}")

    # ── Weekly Meal Plan ──────────────────────────────────────
    st.subheader("🍽️ Your Personalized Meal Plan")

    weekly = diet_plan.get("weekly_meal_plan", {})
    meals = diet_plan.get("meals") or diet_plan.get("meal_plan", [])

    meal_icons = {
        "breakfast": "🌅", "mid-morning snack": "🍎", "mid morning snack": "🍎",
        "morning snack": "🍎", "mid_morning_snack": "🍎",
        "lunch": "☀️", "afternoon snack": "🥜", "evening snack": "🥜",
        "evening_snack": "🥜", "snack": "🥜",
        "dinner": "🌙", "bedtime snack": "🌜",
    }

    if weekly and isinstance(weekly, dict):
        days = list(weekly.keys())
        if days:
            tabs = st.tabs([d.replace("_", " ").title() if isinstance(d, str) else str(d) for d in days])
            for tab, day in zip(tabs, days):
                with tab:
                    day_data = weekly[day]
                    day_meals = []
                    if isinstance(day_data, dict):
                        day_meals = day_data.get("meals", [])
                        if not day_meals:
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
                    if totals and isinstance(totals, dict):
                        parts = []
                        for key in ["calories", "protein_g", "carbs_g", "fat_g"]:
                            v = totals.get(key)
                            if v is not None:
                                parts.append(f"{key.replace('_g','').title()}: {v}")
                        if parts:
                            st.caption(f"📊 Day totals: {' · '.join(parts)}")

    elif isinstance(meals, list) and meals:
        for meal in meals:
            _render_single_meal(meal, meal_icons)
    elif isinstance(meals, dict) and meals:
        for name, meal in meals.items():
            meal_data = meal if isinstance(meal, dict) else {"items": [meal]}
            meal_data["meal_name"] = name
            _render_single_meal(meal_data, meal_icons)
    else:
        st.json(diet_plan)

    # ── Monitoring Recommendations ────────────────────────────
    monitoring = diet_plan.get("monitoring_recommendations", [])
    if monitoring and isinstance(monitoring, list):
        st.subheader("📋 Monitoring Recommendations")
        import pandas as pd
        rows = []
        for m in monitoring:
            if isinstance(m, dict):
                rows.append({
                    "Test": m.get("test", "—"),
                    "Current Status": m.get("current_status", "—"),
                    "Recheck In": m.get("recheck_in", "—"),
                    "Dietary Goal": m.get("dietary_goal", "—"),
                })
            elif isinstance(m, str):
                rows.append({"Test": m, "Current Status": "—", "Recheck In": "—", "Dietary Goal": "—"})
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)

    # ── Confidence Assessment ─────────────────────────────────
    confidence = diet_plan.get("confidence_assessment")
    if confidence and isinstance(confidence, dict):
        with st.expander("📊 Confidence Assessment", expanded=False):
            overall = confidence.get("overall_confidence", "")
            if overall:
                conf_icon = {"high": "🟢", "moderate": "🟡", "low": "🔴"}.get(overall, "⚪")
                st.markdown(f"**Overall Confidence:** {conf_icon} {overall.title()}")

            notes = confidence.get("data_quality_notes", [])
            if notes and isinstance(notes, list):
                st.markdown("**Data Quality Notes:**")
                for n in notes:
                    st.markdown(f"- {n}")

            limitations = confidence.get("limitations", [])
            if limitations and isinstance(limitations, list):
                st.markdown("**Limitations:**")
                for l in limitations:
                    st.caption(f"⚠ {l}")
    elif confidence:
        with st.expander("📊 Confidence Assessment", expanded=False):
            st.write(confidence)

    # ── Disclaimer ────────────────────────────────────────────
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
    """Render one meal block — supports both old ('meal' string) and new ('items' list) format."""
    name = meal.get("meal_name") or meal.get("name") or meal.get("meal_type") or meal.get("meal", "Meal")
    # Normalise underscore names for icon lookup
    name_display = name.replace("_", " ").title()
    icon = icons.get(name.lower().replace("_", " "), "🍽️")
    timing = meal.get("time") or meal.get("timing", "")
    cals = meal.get("calories_approx") or meal.get("calories") or meal.get("estimated_calories", "")
    notes = meal.get("notes") or meal.get("clinical_note", "")

    # New structured items list
    items = meal.get("items") or meal.get("foods") or meal.get("food_items", [])
    # Legacy single-string meal field
    legacy_meal = meal.get("meal")

    header = f"{icon} **{name_display}**"
    if cals:
        header += f" · ~{cals} kcal"
    if timing:
        header += f" · ⏰ {timing}"

    # Show per-meal macros if available
    macros_parts = []
    for macro_key, label in [("protein_g", "P"), ("carbs_g", "C"), ("fat_g", "F")]:
        val = meal.get(macro_key)
        if val is not None:
            macros_parts.append(f"{label}: {val}g")
    if macros_parts:
        header += f" · ({' | '.join(macros_parts)})"

    with st.container():
        st.markdown(header)
        if isinstance(items, list) and items:
            for item in items:
                if isinstance(item, str):
                    st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {item}")
                elif isinstance(item, dict):
                    food = item.get("food") or item.get("name") or str(item)
                    portion = item.get("portion") or item.get("quantity") or item.get("amount", "")
                    prep = item.get("preparation", "")
                    line = f"&nbsp;&nbsp;&nbsp;&nbsp;• **{food}**"
                    if portion:
                        line += f" — {portion}"
                    if prep:
                        line += f" *({prep})*"
                    st.markdown(line)
        elif isinstance(legacy_meal, str) and legacy_meal:
            st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;• {legacy_meal}")
        if notes:
            st.caption(f"💡 {notes}")
        st.markdown("---")


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
    if "dietary_preferences" not in st.session_state:
        st.session_state.dietary_preferences = {}

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
        st.markdown("##### 🥗 Diet Preferences")

        with st.expander("🎛️ Customize Diet Plan", expanded=False):
            pref_diet_type = st.selectbox(
                "Diet Type",
                options=["non_veg", "veg", "vegan", "eggetarian"],
                format_func=lambda x: {
                    "non_veg": "🍗 Non-Vegetarian",
                    "veg": "🥬 Vegetarian",
                    "vegan": "🌱 Vegan",
                    "eggetarian": "🥚 Eggetarian",
                }.get(x, x),
                index=0,
                key="_pref_diet_type",
            )

            pref_meal_freq = st.selectbox(
                "Meal Frequency",
                options=["5_small", "3_meals", "2_meals"],
                format_func=lambda x: {
                    "5_small": "5 small meals/day",
                    "3_meals": "3 meals/day",
                    "2_meals": "2 meals/day",
                }.get(x, x),
                index=0,
                key="_pref_meal_freq",
            )

            pref_cuisine = st.selectbox(
                "Regional Cuisine",
                options=[
                    "", "North Indian", "South Indian", "Mediterranean",
                    "East Asian", "Middle Eastern", "Continental/Western",
                    "Latin American",
                ],
                format_func=lambda x: x if x else "No preference",
                index=0,
                key="_pref_cuisine",
            )

            pref_calories = st.number_input(
                "Calorie Target (kcal/day) — 0 = auto",
                min_value=0, max_value=5000, value=0, step=100,
                key="_pref_calories",
            )

            pref_allergies = st.text_input(
                "Allergies / Exclusions (comma-separated)",
                placeholder="e.g. peanuts, shellfish, gluten",
                key="_pref_allergies",
            )

            if st.button("💾 Save Preferences", key="_save_prefs", type="primary"):
                prefs: dict = {
                    "diet_type": pref_diet_type,
                    "meal_frequency": pref_meal_freq,
                }
                if pref_cuisine:
                    prefs["cuisine"] = pref_cuisine
                if pref_calories and pref_calories > 0:
                    prefs["calorie_target"] = pref_calories
                if pref_allergies and pref_allergies.strip():
                    prefs["allergies"] = [
                        a.strip() for a in pref_allergies.split(",") if a.strip()
                    ]
                st.session_state.dietary_preferences = prefs
                st.success("Preferences saved!")

            # Show current prefs
            current_prefs = st.session_state.dietary_preferences
            if current_prefs:
                parts = []
                dt = current_prefs.get("diet_type", "")
                if dt:
                    parts.append(dt.replace("_", "-").title())
                mf = current_prefs.get("meal_frequency", "")
                if mf:
                    parts.append(mf.replace("_", " "))
                cu = current_prefs.get("cuisine", "")
                if cu:
                    parts.append(cu)
                al = current_prefs.get("allergies", [])
                if al:
                    parts.append(f"avoid: {', '.join(al)}")
                if parts:
                    st.caption(f"✅ {' · '.join(parts)}")

        st.divider()
        st.caption("v0.4.0 · Powered by Groq AI")

    st.markdown(
        "<h1 style='text-align:center; margin-bottom:0;'>🏥 AI-Powered Diet Plan Generator</h1>"
        "<p style='text-align:center; color:#64748b; margin-top:4px;'>"
        "Upload medical reports → Extract lab data → Get personalized diet recommendations"
        "</p>",
        unsafe_allow_html=True,
    )

    # ── Workflow progress stepper ─────────────────────────────
    step_done = [False, False, False]
    step_done[0] = True  # upload always available
    step_done[1] = st.session_state.analysis_done
    step_done[2] = st.session_state.diet_done

    step_labels = ["📄 Upload", "🧪 Analyze", "🥗 Diet Plan"]
    step_cols = st.columns(3)
    for i, col in enumerate(step_cols):
        with col:
            if step_done[i]:
                color, icon = "#22c55e", "✅"
            elif i == 1 and not step_done[1]:
                color, icon = "#94a3b8", "⏳"
            elif i == 2 and not step_done[2]:
                color, icon = "#94a3b8", "⏳"
            else:
                color, icon = "#94a3b8", "⏳"
            st.markdown(
                f"<div style='text-align:center; padding:6px 0;'>"
                f"<span style='font-size:1.1em; color:{color}; font-weight:600;'>"
                f"{icon} {step_labels[i]}</span></div>",
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
                st.session_state.dietary_preferences = {}
                st.session_state.active_tab = "📄 Upload Reports"
                st.rerun()

    # ═══════════════════════════════════════════════════════════
    #  TAB 2: Lab Results
    # ═══════════════════════════════════════════════════════════
    elif active_tab == "🧪 Lab Results":
        if not st.session_state.analysis_done:
            st.markdown(
                "<div style='text-align:center; padding:3em 0;'>"
                "<h3 style='color:#94a3b8;'>🧪 No Lab Results Yet</h3>"
                "<p style='color:#94a3b8;'>Upload your medical reports in the <b>Upload Reports</b> tab "
                "and click <b>Analyze</b> to extract lab data.</p>"
                "</div>",
                unsafe_allow_html=True,
            )
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
                st.markdown(
                    "<div style='text-align:center; padding:2em 0;'>"
                    "<h3>🥗 Ready to Generate</h3>"
                    "<p style='color:#64748b;'>Your reports have been analyzed. "
                    "Generate a personalized diet plan based on your lab results.</p>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                c1, c2, c3 = st.columns([1, 2, 1])
                with c2:
                    if st.button("🥗 Generate Diet Plan Now", type="primary", use_container_width=True):
                        _run_diet_generation()
            else:
                st.markdown(
                    "<div style='text-align:center; padding:3em 0;'>"
                    "<h3 style='color:#94a3b8;'>📄 Upload Reports First</h3>"
                    "<p style='color:#94a3b8;'>Go to the <b>Upload Reports</b> tab to upload your medical "
                    "documents, then analyze them to unlock diet plan generation.</p>"
                    "</div>",
                    unsafe_allow_html=True,
                )
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

                # ── Action buttons: Regenerate & Download ─────────
                st.divider()
                btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])

                with btn_col1:
                    if st.button("🔄 Regenerate Diet Plan", type="secondary", use_container_width=True,
                                 help="Re-generate with current preferences"):
                        st.session_state.diet_done = False
                        st.session_state.diet_data = None
                        _run_diet_generation()

                with btn_col2:
                    diet_json = json.dumps(diet_data, indent=2, ensure_ascii=False, default=str)
                    st.download_button(
                        label="📥 Download Diet Plan (JSON)",
                        data=diet_json,
                        file_name="diet_plan.json",
                        mime="application/json",
                        use_container_width=True,
                    )

                with btn_col3:
                    # Markdown export
                    md_lines = ["# 🥗 Personalized Diet Plan\n"]
                    guidelines = diet_plan.get("dietary_guidelines", {})
                    caloric = guidelines.get("caloric_target", {})
                    if caloric:
                        md_lines.append(f"**Calorie Target:** {caloric.get('range_kcal', '—')} kcal\n")
                    macro = guidelines.get("macronutrient_split", {})
                    if macro:
                        md_lines.append(
                            f"**Macros:** Protein {macro.get('protein_percent', '?')}% | "
                            f"Carbs {macro.get('carbs_percent', '?')}% | "
                            f"Fat {macro.get('fat_percent', '?')}%\n"
                        )
                    weekly = diet_plan.get("weekly_meal_plan", {})
                    if weekly:
                        for day, day_data in weekly.items():
                            md_lines.append(f"\n## {day.replace('_', ' ').title()}\n")
                            day_meals = []
                            if isinstance(day_data, dict):
                                day_meals = day_data.get("meals", [])
                                if not day_meals:
                                    day_meals = [
                                        {"meal_name": k, **(v if isinstance(v, dict) else {})}
                                        for k, v in day_data.items() if k != "daily_totals"
                                    ]
                            elif isinstance(day_data, list):
                                day_meals = day_data
                            for meal in day_meals:
                                mname = meal.get("meal_name") or meal.get("name", "Meal")
                                md_lines.append(f"\n### {mname.replace('_',' ').title()}\n")
                                items = meal.get("items", [])
                                for item in items:
                                    if isinstance(item, dict):
                                        food = item.get("food", "")
                                        portion = item.get("portion", "")
                                        md_lines.append(f"- {food} — {portion}")
                                    elif isinstance(item, str):
                                        md_lines.append(f"- {item}")
                    disclaimer = diet_plan.get("disclaimer", "")
                    if disclaimer:
                        md_lines.append(f"\n---\n⚠️ *{disclaimer}*\n")
                    md_text = "\n".join(md_lines)
                    st.download_button(
                        label="📝 Download as Markdown",
                        data=md_text,
                        file_name="diet_plan.md",
                        mime="text/markdown",
                        use_container_width=True,
                    )

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

    # Collect dietary preferences from session state
    dietary_prefs = st.session_state.get("dietary_preferences", {}) or {}

    try:
        pref_summary = ""
        if dietary_prefs:
            parts = [dietary_prefs.get("diet_type", ""), dietary_prefs.get("cuisine", "")]
            pref_summary = " (" + ", ".join(p for p in parts if p) + ")"
        status.markdown(
            f"🥗 **Generating personalized diet plan{pref_summary}** "
            "(this may take 30-60 seconds)..."
        )
        progress.progress(0.3, text="AI generating diet plan...")

        # Call the shared diet service with preferences
        diet_output = generate_diet_from_results(
            results, successful_docs, dietary_prefs,
        )

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
