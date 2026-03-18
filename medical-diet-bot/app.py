import streamlit as st
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv
from PIL import Image
import io
import pypdf

# Load variables from the local .env file
load_dotenv()

# Securely grab the key
api_key = os.getenv("GOOGLE_API_KEY")

# Safety Check: If the key is missing, show a friendly message, not a crash
if not api_key:
    st.warning("Please set your GOOGLE_API_KEY in the environment or .env file.")
    st.stop() # Stops the app from running further without a key

llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=api_key)

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
    
    # We add a unique 'key' to each input to prevent the DuplicateElementId error
    age = st.number_input("Age", value=23, key="patient_age")
    gender = st.selectbox("Gender", ["Male", "Female", "Other"], key="patient_gender")
    
    # BMI Math Fix:
    weight_kg = st.number_input("Weight (kg)", value=60.0, key="patient_weight")
    height_ft = st.number_input("Height (ft)", value=5.50, key="patient_height")
    
    # Convert feet to meters for correct BMI: 1 foot = 0.3048 meters
    height_m = height_ft * 0.3048
    bmi = round(weight_kg / (height_m ** 2), 2)
    
    st.write(f"**Your Calculated BMI: {bmi}**")
    
    # BMI Category logic for your AI prompt
    if bmi < 18.5: category = "Underweight"
    elif bmi < 25: category = "Normal"
    else: category = "Overweight"
    country = st.text_input("Country", "India")
    pref = st.selectbox("Diet Preference", ["Vegetarian", "Non-Vegetarian", "Vegan"])
 
# ... (keep your existing imports and LLM setup)

# Update the uploader to accept everything
uploaded_file = st.file_uploader(
    "Upload Medical Report", 
    type=["json", "pdf", "jpg", "jpeg", "png", "ppt", "pptx"]
)
if uploaded_file:
    report_text = ""
    
    try:
        # 1. HANDLE JSON FILES
        if uploaded_file.name.endswith('.json'):
            import json
            data = json.load(uploaded_file)
            report_text = json.dumps(data, indent=2)
            st.success("JSON file loaded successfully!")

        # 2. HANDLE PDF FILES (Requires: pip install pypdf)
        elif uploaded_file.name.endswith('.pdf'):
            import pypdf
            reader = pypdf.PdfReader(uploaded_file)
            for page in reader.pages:
                report_text += page.extract_text()
            st.success("PDF text extracted successfully!")
            
    except Exception as e:
        st.error(f"Could not read file: {e}")

    # 3. THE BUTTON (Now it will show up as long as report_text is not empty)
    if report_text:
        if st.button("Generate My Personalized Diet Plan"):
            with st.spinner("AI Nutritionist is thinking..."):
                # Your prompt logic
                final_prompt = f"Analyze this report and provide a diet plan: {report_text}"
                
                # Send to Gemini
                response = llm.invoke(final_prompt)
                st.markdown(response.content)
    else:
        st.warning("Please upload a valid JSON or PDF report to proceed.")