import streamlit as st
import json
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# ─── Page Config ────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI-NutriCare",
    page_icon="🥗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Custom CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=DM+Sans:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* Background */
.stApp {
    background: linear-gradient(135deg, #0f1117 0%, #1a1f2e 50%, #0f1117 100%);
    color: #e8eaf0;
}

/* Header */
.main-header {
    text-align: center;
    padding: 2.5rem 0 1.5rem 0;
}
.main-header h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 3rem;
    background: linear-gradient(135deg, #4ade80, #22d3ee);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 0.3rem;
}
.main-header p {
    color: #94a3b8;
    font-size: 1rem;
    font-weight: 300;
    letter-spacing: 0.05em;
}

/* Step badges */
.step-badge {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(74, 222, 128, 0.1);
    border: 1px solid rgba(74, 222, 128, 0.3);
    border-radius: 20px;
    padding: 4px 14px;
    font-size: 0.8rem;
    color: #4ade80;
    font-weight: 500;
    margin-bottom: 12px;
}

/* Cards */
.info-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 1.4rem;
    margin: 0.8rem 0;
}
.info-card h4 {
    color: #22d3ee;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.6rem;
    font-weight: 600;
}

/* Abnormal tag */
.tag-high   { background: rgba(239,68,68,0.15);  color:#f87171; border:1px solid rgba(239,68,68,0.3);  border-radius:6px; padding:2px 8px; font-size:0.78rem; }
.tag-low    { background: rgba(251,191,36,0.15); color:#fbbf24; border:1px solid rgba(251,191,36,0.3); border-radius:6px; padding:2px 8px; font-size:0.78rem; }
.tag-normal { background: rgba(74,222,128,0.15); color:#4ade80; border:1px solid rgba(74,222,128,0.3); border-radius:6px; padding:2px 8px; font-size:0.78rem; }

/* Sidebar */
section[data-testid="stSidebar"] {
    background: rgba(15,17,23,0.95) !important;
    border-right: 1px solid rgba(255,255,255,0.06);
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4ade80, #22d3ee);
    color: #0f1117;
    border: none;
    border-radius: 10px;
    font-weight: 600;
    font-family: 'DM Sans', sans-serif;
    padding: 0.55rem 1.6rem;
    transition: opacity 0.2s;
}
.stButton > button:hover { opacity: 0.85; }

/* File uploader */
[data-testid="stFileUploader"] {
    border: 2px dashed rgba(74,222,128,0.3);
    border-radius: 12px;
    padding: 1rem;
    background: rgba(74,222,128,0.03);
}

/* Chat bubbles */
.chat-user {
    background: rgba(74,222,128,0.1);
    border: 1px solid rgba(74,222,128,0.2);
    border-radius: 12px 12px 2px 12px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
    text-align: right;
}
.chat-bot {
    background: rgba(34,211,238,0.08);
    border: 1px solid rgba(34,211,238,0.2);
    border-radius: 12px 12px 12px 2px;
    padding: 0.75rem 1rem;
    margin: 0.5rem 0;
}

/* Progress */
.stProgress > div > div { background: linear-gradient(90deg,#4ade80,#22d3ee); }

/* Metric */
[data-testid="stMetric"] {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 12px;
    padding: 0.8rem;
}

/* Spinner text */
.stSpinner > div { color: #4ade80 !important; }

/* Divider */
hr { border-color: rgba(255,255,255,0.07) !important; }

/* Selectbox / text_input */
.stSelectbox > div > div, .stTextInput > div > div {
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.12) !important;
    border-radius: 10px !important;
    color: #e8eaf0 !important;
}

/* Textarea */
.stTextArea textarea {
    background: rgba(255,255,255,0.04) !important;
    border-color: rgba(255,255,255,0.12) !important;
    color: #e8eaf0 !important;
    border-radius: 10px !important;
}
</style>
""", unsafe_allow_html=True)

# ─── Imports (lazy so errors show in UI) ─────────────────────────────────────
from core.ocr import process_document
from core.diet import generate_diet_plan, calculate_bmi
from core.chat import chat_with_report

# ─── Session State ───────────────────────────────────────────────────────────
for key in ["extracted_data", "diet_plan", "chat_history", "bmi_info", "patient_profile"]:
    if key not in st.session_state:
        st.session_state[key] = None
if "chat_history" not in st.session_state or st.session_state.chat_history is None:
    st.session_state.chat_history = []

# ─── Header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div class="main-header">
  <h1>🥗 AI-NutriCare</h1>
  <p>Upload your medical report · Get a personalised diet plan · Ask anything</p>
</div>
""", unsafe_allow_html=True)

# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Patient Profile")
    st.markdown("---")

    weight = st.number_input("Weight (kg)", 30.0, 200.0, 70.0, 0.5)
    height = st.number_input("Height (cm)", 100.0, 250.0, 170.0, 0.5)
    country = st.selectbox("Country / Food Culture",
        ["India", "USA", "UK", "China", "Japan", "Mediterranean", "Middle East", "Other"])
    diet_pref = st.selectbox("Diet Preference",
        ["No Restriction", "Vegetarian", "Vegan", "Keto", "Low-Carb", "Diabetic-friendly"])

    bmi_val, bmi_cat = calculate_bmi(weight, height)
    bmi_color = {"Underweight":"#fbbf24","Normal":"#4ade80","Overweight":"#fb923c","Obese":"#f87171"}.get(bmi_cat,"#94a3b8")
    st.markdown(f"""
    <div class="info-card" style="text-align:center;">
      <h4>BMI</h4>
      <div style="font-size:2rem;font-weight:700;color:{bmi_color};">{bmi_val}</div>
      <div style="color:{bmi_color};font-size:0.9rem;margin-top:4px;">{bmi_cat}</div>
    </div>
    """, unsafe_allow_html=True)

    st.session_state.patient_profile = {
        "weight_kg": weight, "height_cm": height,
        "bmi": bmi_val, "bmi_category": bmi_cat,
        "country": country, "diet_preference": diet_pref,
    }
    st.session_state.bmi_info = {"value": bmi_val, "category": bmi_cat}

    st.markdown("---")
    st.markdown("### 🚦 Pipeline Status")
    steps = [
        ("📄 Report Upload",   st.session_state.extracted_data is not None),
        ("🔍 OCR + Extraction", st.session_state.extracted_data is not None),
        ("🥗 Diet Plan",        st.session_state.diet_plan is not None),
        ("💬 AI Chat",          len(st.session_state.chat_history) > 0),
    ]
    for label, done in steps:
        icon = "✅" if done else "⬜"
        st.markdown(f"{icon} {label}")

# ─── Main Tabs ───────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["📄 Upload & Analyse", "🥗 Diet Plan", "💬 Chat Assistant"])

# ════════════════════════════════════════════════════════════════════════════
# TAB 1 — Upload & Analyse
# ════════════════════════════════════════════════════════════════════════════
with tab1:
    col_up, col_res = st.columns([1, 1], gap="large")

    with col_up:
        st.markdown('<div class="step-badge">Step 1 → 3 · Upload · OCR · Extract</div>', unsafe_allow_html=True)
        st.markdown("#### Upload Medical Report")
        uploaded = st.file_uploader("PDF or Image (JPG / PNG)", type=["pdf","jpg","jpeg","png"])

        if uploaded:
            # Save temp file
            tmp_path = Path("temp_upload") / uploaded.name
            tmp_path.parent.mkdir(exist_ok=True)
            tmp_path.write_bytes(uploaded.getvalue())

            st.success(f"✅ File ready: **{uploaded.name}**  ({uploaded.size/1024:.1f} KB)")

            if st.button("🔬 Process Report", use_container_width=True):
                with st.spinner("Running OCR + Data Extraction — this may take 30–60 s…"):
                    try:
                        result = process_document(str(tmp_path))
                        st.session_state.extracted_data = result
                        st.success("✅ Extraction complete!")
                    except Exception as e:
                        st.error(f"❌ Error: {e}")

    with col_res:
        if st.session_state.extracted_data:
            data = st.session_state.extracted_data
            info = data.get("patient_information", {})

            st.markdown('<div class="step-badge">Extracted Results</div>', unsafe_allow_html=True)
            st.markdown("#### Patient Information")
            c1, c2 = st.columns(2)
            c1.metric("Name",   info.get("patient_name") or "—")
            c1.metric("Age",    f'{info.get("age_years") or "—"} yrs')
            c2.metric("Gender", info.get("gender") or "—")
            c2.metric("Lab",    info.get("lab_number") or "—")

            # Abnormal findings
            abnormals = data.get("abnormal_findings", [])
            if abnormals:
                st.markdown("#### ⚠️ Abnormal Findings")
                tests_index = data.get("tests_index", {})
                for ab in abnormals:
                    key  = ab["canonical_test_key"]
                    meta = tests_index.get(key, {})
                    sev  = ab.get("severity","")
                    tag_cls = "tag-high" if sev=="high" else "tag-low" if sev=="low" else "tag-normal"
                    st.markdown(f"""
                    <div class="info-card" style="padding:0.8rem 1rem;">
                      <b>{meta.get('test_name', key)}</b>
                      &nbsp;<span class="{tag_cls}">{sev.upper()}</span><br>
                      <small style="color:#94a3b8;">
                        Observed: <b style="color:#e8eaf0;">{ab['observed_value']} {meta.get('units','')}</b>
                        &nbsp;|&nbsp; Range: {ab['expected_range']}
                      </small>
                    </div>""", unsafe_allow_html=True)
            else:
                st.info("✅ No abnormal findings detected.")

            # Test summary by category
            by_cat = data.get("tests_by_category", {})
            tests  = data.get("tests_index", {})
            total  = sum(len(v) for v in by_cat.values())
            abN    = len(abnormals)
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Tests", total)
            c2.metric("Abnormal",    abN)
            c3.metric("Normal",      total - abN)

            with st.expander("📋 Raw JSON"):
                st.json(data)
        else:
            st.markdown("""
            <div class="info-card" style="text-align:center;padding:2.5rem;">
              <div style="font-size:3rem;">📋</div>
              <p style="color:#94a3b8;margin-top:0.5rem;">Upload and process a report to see results here.</p>
            </div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# TAB 2 — Diet Plan
# ════════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown('<div class="step-badge">Step 5 · AI Diet Plan Generation · Llama 3.3 70B Versatile</div>', unsafe_allow_html=True)

    if not st.session_state.extracted_data:
        st.warning("⚠️ Please upload and process a medical report first (Tab 1).")
    else:
        if st.button("🥗 Generate My Personalised Diet Plan", use_container_width=True):
            with st.spinner("Generating diet plan with Llama 3.3 70B — please wait…"):
                try:
                    plan = generate_diet_plan(
                        st.session_state.extracted_data,
                        st.session_state.patient_profile,
                    )
                    st.session_state.diet_plan = plan
                except Exception as e:
                    st.error(f"❌ {e}")

        if st.session_state.diet_plan:
            plan = st.session_state.diet_plan

            # ── Health summary ────────────────────────────────────────────
            st.markdown("### 🩺 Health Summary")
            st.markdown(f"""
            <div class="info-card">
              {plan.get("health_summary","").replace(chr(10),"<br>")}
            </div>""", unsafe_allow_html=True)

            col_a, col_b = st.columns(2)

            # Foods to include
            with col_a:
                st.markdown("### ✅ Foods to Include")
                for item in plan.get("foods_to_include", []):
                    st.markdown(f"""
                    <div class="info-card" style="padding:0.6rem 1rem;">
                      🟢 {item}
                    </div>""", unsafe_allow_html=True)

            # Foods to avoid
            with col_b:
                st.markdown("### ❌ Foods to Avoid")
                for item in plan.get("foods_to_avoid", []):
                    st.markdown(f"""
                    <div class="info-card" style="padding:0.6rem 1rem;">
                      🔴 {item}
                    </div>""", unsafe_allow_html=True)

            # Sample Meal Plan
            st.markdown("### 🍽️ Sample Meal Plan")
            meal_plan = plan.get("sample_meal_plan", {})
            for day, meals in meal_plan.items():
                with st.expander(f"📅 {day}"):
                    for meal, desc in meals.items():
                        st.markdown(f"**{meal.title()}:** {desc}")

            # Nutrition Focus & Lifestyle Tips
            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown("### 🎯 Nutrition Focus Areas")
                for tip in plan.get("nutrition_focus_areas", []):
                    st.markdown(f"• {tip}")
            with col_d:
                st.markdown("### 💡 Lifestyle Tips")
                for tip in plan.get("lifestyle_tips", []):
                    st.markdown(f"• {tip}")

            # Download JSON
            st.download_button(
                "⬇️ Download Diet Plan (JSON)",
                data=json.dumps(plan, indent=2),
                file_name="diet_plan.json",
                mime="application/json",
                use_container_width=True,
            )

# ════════════════════════════════════════════════════════════════════════════
# TAB 3 — Chat
# ════════════════════════════════════════════════════════════════════════════
with tab3:
    st.markdown('<div class="step-badge">Step 7 · AI Chat Assistant · Context-Aware</div>', unsafe_allow_html=True)

    if not st.session_state.extracted_data:
        st.warning("⚠️ Please upload and process a medical report first (Tab 1).")
    else:
        # Display history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                st.markdown(f'<div class="chat-user">🧑 {msg["content"]}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="chat-bot">🤖 {msg["content"]}</div>', unsafe_allow_html=True)

        st.markdown("---")

        # Suggested questions
        suggestions = [
            "What were my cholesterol levels?",
            "Why should I avoid sugar?",
            "What can I eat for breakfast?",
            "What does my hemoglobin level mean?",
        ]
        st.markdown("**Suggested questions:**")
        cols = st.columns(len(suggestions))
        for i, q in enumerate(suggestions):
            if cols[i].button(q, key=f"sug_{i}"):
                st.session_state._pending_question = q

        user_input = st.chat_input("Ask anything about your report or diet plan…")

        # Handle suggestion click or typed input
        question = user_input
        if hasattr(st.session_state, "_pending_question"):
            question = st.session_state._pending_question
            del st.session_state._pending_question

        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            with st.spinner("Thinking…"):
                try:
                    answer = chat_with_report(
                        question=question,
                        extracted_data=st.session_state.extracted_data,
                        diet_plan=st.session_state.diet_plan,
                        chat_history=st.session_state.chat_history[:-1],
                    )
                except Exception as e:
                    answer = f"Sorry, I hit an error: {e}"
            st.session_state.chat_history.append({"role": "assistant", "content": answer})
            st.rerun()

        if st.session_state.chat_history:
            if st.button("🗑️ Clear Chat"):
                st.session_state.chat_history = []
                st.rerun()
