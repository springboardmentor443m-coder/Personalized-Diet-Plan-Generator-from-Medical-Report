import streamlit as st
from pipeline import extract_data

st.title("AI Medical Diet Analyzer")

uploaded_file = st.file_uploader("Upload Medical Report", type=["pdf"])

if uploaded_file is not None:

    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.getbuffer())

    result = extract_data("temp.pdf")

    st.subheader("Extracted Medical Values")

    for key, value in result["medical_values"].items():
        st.write(f"{key.upper()} : {value}")

    st.subheader("Health Analysis")

    for test, status in result["health_analysis"].items():
        st.write(f"{test.upper()} : {status}")

    st.subheader("BMI Information")

    st.write("BMI:", result["BMI"])
    st.write("Category:", result["BMI_category"])

    st.subheader("Diet Recommendation")

    for item in result["diet_recommendation"]:
        st.write("•", item)

    st.subheader("AI Medical Insights")

    st.write(result["ai_analysis"])