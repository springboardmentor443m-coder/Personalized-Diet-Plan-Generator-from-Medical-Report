import streamlit as st
from modules.extractor import extract_text

from modules.utils import extract_metrics
from modules.ml_model import predict_condition
from modules.diet_generator import generate_diet
from modules.pdf_exporter import generate_pdf

st.set_page_config(page_title="AI-NutriCare")

st.title("🥗 AI-NutriCare")
st.subheader("AI/ML-Based Personalized Diet Plan Generator")

uploaded_file = st.file_uploader(
    "Upload Medical Report",
    type=["pdf", "png", "jpg", "jpeg", "txt"]
)

if uploaded_file:

    file_type = uploaded_file.name.split(".")[-1]

    extracted_text = extract_text(uploaded_file, file_type)

    st.subheader("📄 Extracted Text")

    # ✅ Debug View
    st.write("RAW TEXT FROM REPORT 👇")
    st.text(extracted_text)

    # ---- Metric Extraction ----
    metrics = extract_metrics(extracted_text)

    st.subheader("🧪 Detected Metrics")

    if metrics:
        st.success("Metrics Detected ✅")
        st.write(metrics)

        # ✅ ML Prediction
        try:
            condition = predict_condition(metrics)

            st.subheader("⚠ Predicted Condition")
            st.success(condition)

            # ✅ Diet Generation (ML Based)
            diet = generate_diet(condition, metrics)

        except:
            # ✅ Fallback if ML fails
            st.warning("Using Smart Diet Inference ⚡")
            diet = generate_diet(None, metrics)

    else:
        st.warning("Limited Data Detected ⚡")
        diet = generate_diet(None, metrics)

    # ---- Diet Display ----
    st.subheader("🥗 Personalized Diet Plan")
    st.write(diet)

    # ---- PDF Generation ----
    pdf_file = generate_pdf(diet)

    st.success("PDF Generated Successfully ✅")

    # ✅ Download Button
    st.download_button(
        label="📥 Download Diet Plan",
        data=pdf_file,
        file_name="DietPlan.pdf",
        mime="application/pdf"
    )

    # ✅ Extra Debugging Help
    st.write("🔍 DEBUG: Numbers detected in text:")

    import re
    numbers = re.findall(r"\d+", extracted_text)
    st.write(numbers)
