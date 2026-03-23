import streamlit as st
import re
import uuid

from backend.report_parser import extract_text
from backend.health_analyzer import analyze_numeric_values
from backend.llm_engine import interpret_report
from backend.diet_generator import generate_diet_plan
from backend.pdf_export import create_pdf
from backend.rag_chat import rag_chat

# ---------------- SESSION ----------------
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

if "data_added" not in st.session_state:
    st.session_state.data_added = False

# ---------------- PAGE ----------------
st.set_page_config(page_title="Diet Generator", page_icon="🩺", layout="wide")

st.title("🩺 Diet Generator")
st.subheader("AI-Based Personalized Diet Plan")

# ---------------- INPUT ----------------
col1, col2 = st.columns(2)

with col1:
    diet_type = st.radio("Diet Type", ["Vegetarian", "Non-Vegetarian"])

with col2:
    height = st.number_input("Height (cm)", 50, 250)
    weight = st.number_input("Weight (kg)", 20, 200)

bmi_manual = None

def get_bmi_category(bmi):
    if bmi < 18.5:
        return "Underweight"
    elif bmi < 25:
        return "Normal"
    elif bmi < 30:
        return "Overweight"
    else:
        return "Obese"

if height and weight:
    bmi_manual = weight / ((height/100) ** 2)
    st.success(f"BMI: {bmi_manual:.2f} ({get_bmi_category(bmi_manual)})")

# ---------------- FILE ----------------
uploaded_file = st.file_uploader("Upload Medical Report")

extracted_text = ""
diet = ""

# ---------------- MAIN ----------------
if uploaded_file:
    extracted_text = extract_text(uploaded_file) or ""

    if extracted_text.strip():

        st.success("Report processed")

        numeric = analyze_numeric_values(extracted_text)

        st.write("Blood Sugar:", numeric["Blood Sugar"])
        st.write("Cholesterol:", numeric["Cholesterol"])

        analysis = interpret_report(extracted_text)
        st.write("### AI Analysis")
        st.write(analysis)

        diet = generate_diet_plan(analysis, diet_type)
        st.write("### Diet Plan")
        st.write(diet)

        # ✅ Add to RAG only once
        if not st.session_state.data_added:
            rag_chat.add_context(
                session_id=st.session_state.session_id,
                markdown_text=extracted_text,
                structured_data=numeric,
                diet_plan=diet,
                patient_profile=f"Height: {height}, Weight: {weight}, Diet: {diet_type}"
            )
            st.session_state.data_added = True

        pdf = create_pdf(diet)
        with open(pdf, "rb") as f:
            st.download_button("Download PDF", f)

    else:
        st.error("No text detected")

# ---------------- CHAT (NO HISTORY) ----------------
st.markdown("---")
st.subheader("💬 Smart AI Assistant")

user_input = st.text_input("Ask about your health/diet and press Enter")

if user_input:
    if st.session_state.data_added:
        
        # 🔥 Loading spinner
        with st.spinner("Thinking... 🤖"):
            response = rag_chat.chat(
                session_id=st.session_state.session_id,
                user_message=user_input
            )

    else:
        response = "⚠️ Please upload report first"

    # ✅ Clean output
    st.markdown("### 🤖 Answer")
    st.write(response)