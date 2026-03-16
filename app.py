import streamlit as st
from extraction_module import extract_health_data
from ml_module import analyze_health
from diet_generator import generate_diet
from chatbot_module import chatbot_response

st.title("AI NutriCare - Personalized Diet Plan Generator")

st.write("Upload your medical report text to generate a diet plan.")

report_text = st.text_area("Paste Medical Report Text")

if st.button("Generate Diet Plan"):

    data = extract_health_data(report_text)

    condition = analyze_health(data)

    diet = generate_diet(condition)

    advice = chatbot_response(condition)

    st.subheader("Extracted Health Data")
    st.write(data)

    st.subheader("Detected Conditions")
    st.write(condition)

    st.subheader("Recommended Diet Plan")
    st.write(diet)

    st.subheader("Chatbot Advice")
    st.write(advice)
