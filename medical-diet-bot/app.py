import streamlit as st
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# 1. Setup the AI Model
llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key="https://console.cloud.google.com/iam-admin/serviceaccounts/details/115498264582495852921;edit=true?previousPage=%2Fapis%2Fcredentials%3Fproject%3Dpossible-jetty-468110-r8&project=possible-jetty-468110-r8")

# 2. Define the Prompt (Using the role you provided)
diet_prompt_template = """
### ROLE
You are an expert Clinical Nutritionist...
[Insert the rest of your prompt here]

### INPUT DATA
1. MEDICAL DATA (JSON): {extracted_json}
2. BMI INFO: {bmi_value} ({bmi_category})
3. PATIENT PROFILE: Age: {age}, Gender: {gender}, Country: {country}
4. DIET PREFERENCE: {diet_preference}

### REQUIRED OUTPUT FORMAT
...
"""

def generate_diet_plan(json_data, bmi, age, gender, country, preference):
    prompt = PromptTemplate.from_template(diet_prompt_template)
    # Simple logic to determine BMI category
    category = "Overweight" if bmi > 25 else "Normal" 
    
    chain = prompt | llm
    response = chain.invoke({
        "extracted_json": json_data,
        "bmi_value": bmi,
        "bmi_category": category,
        "age": age,
        "gender": gender,
        "country": country,
        "diet_preference": preference
    })
    return response.content
    
    # Continuing 
st.title("🥗 AI Medical Diet Assistant")

with st.sidebar:
    st.header("Patient Info")
    age = st.number_input("Age", min_value=1, max_value=100, value=23)
    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
    weight = st.number_input("Weight (kg)", value=60.0)
    height = st.number_input("Height (m)", value=5.02)
    bmi = round(weight / (height ** 2), 2)
    st.write(f"Your BMI: {bmi}")
    country = st.text_input("Country", "India")
    pref = st.selectbox("Diet Preference", ["Vegetarian", "Non-Vegetarian", "Vegan"])

# File Uploader for your JSON dataset
uploaded_file = st.file_uploader("Upload Medical Report (JSON)", type=["json"])

if uploaded_file and st.button("Generate Diet Plan"):
    json_content = uploaded_file.read().decode("utf-8")
    with st.spinner("Analyzing report..."):
        plan = generate_diet_plan(json_content, bmi, age, gender, country, pref)
        st.markdown(plan)