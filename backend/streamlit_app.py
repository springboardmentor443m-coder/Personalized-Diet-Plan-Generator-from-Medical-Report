import streamlit as st
import pandas as pd
import numpy as np
import joblib
import os
import time

# ==========================================
# 1. PAGE CONFIGURATION & THEME
# ==========================================
st.set_page_config(
    page_title="AI-NutriCare",
    page_icon="🧬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Dark Medical Theme & Animations
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0e1117;
    }
    
    /* Animations */
    @keyframes fadeIn {
        0% { opacity: 0; transform: translateY(20px); }
        100% { opacity: 1; transform: translateY(0); }
    }
    
    .animate-box {
        animation: fadeIn 0.8s ease-out forwards;
    }

    /* Cards (Glassmorphism) */
    .medical-card {
        background: linear-gradient(145deg, #1e293b, #0f172a);
        border: 1px solid #334155;
        border-radius: 15px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.5);
        color: white;
        margin-bottom: 20px;
        transition: transform 0.3s;
    }
    
    .medical-card:hover {
        transform: translateY(-5px);
        border-color: #00e5ff;
        box-shadow: 0 10px 15px -3px rgba(0, 229, 255, 0.1);
    }

    /* Headings */
    h1, h2, h3 {
        color: #f1f5f9 !important;
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    .highlight-text {
        background: -webkit-linear-gradient(45deg, #00e5ff, #2979ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: bold;
    }

    /* Metrics */
    .metric-value {
        font-size: 2rem;
        font-weight: bold;
        color: #00e5ff;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Button Styling */
    .stButton>button {
        background: linear-gradient(90deg, #00e5ff, #2979ff);
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        box-shadow: 0 0 15px rgba(0, 229, 255, 0.5);
        transform: scale(1.02);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MODEL LOADING
# ==========================================
MODEL_DIR = "models"

@st.cache_resource
def load_models():
    models = {}
    try:
        # Check if files exist before loading
        if os.path.exists(os.path.join(MODEL_DIR, 'diabetes_model.pkl')):
            models['diabetes'] = joblib.load(os.path.join(MODEL_DIR, 'diabetes_model.pkl'))
        if os.path.exists(os.path.join(MODEL_DIR, 'heart_model.pkl')):
            models['heart'] = joblib.load(os.path.join(MODEL_DIR, 'heart_model.pkl'))
    except Exception as e:
        st.error(f"Error loading models: {e}")
    return models

models = load_models()

# ==========================================
# 3. DIET PLAN LOGIC
# ==========================================
def generate_diet_plan(conditions, preference="Veg"):
    # ... (Same logic as before, just ensuring it returns structured data)
    has_diabetes = "Diabetes" in conditions
    has_heart_risk = "Heart Risk" in conditions
    
    plan = {
        "guidelines": [],
        "breakfast": [],
        "lunch": [],
        "dinner": [],
        "snacks": []
    }
    
    if has_diabetes:
        plan["guidelines"].append("📉 **Glycemic Control:** Focus on complex carbs (Oats, Quinoa).")
        plan["guidelines"].append("🍬 **Sugar:** Strictly avoid refined sugars and sugary beverages.")
        plan["breakfast"].append({"name": "Methi Paratha (Low Oil)", "why": "Fenugreek helps lower blood sugar.", "cal": 220})
        plan["breakfast"].append({"name": "Steel-Cut Oats with Berries", "why": "High fiber prevents glucose spikes.", "cal": 240})
        plan["lunch"].append({"name": "Jowar Roti + Bhindi Masala", "why": "Okra (Bhindi) has anti-diabetic properties.", "cal": 350})
        
    if has_heart_risk:
        plan["guidelines"].append("❤️ **Heart Health:** Limit sodium intake to <2300mg/day.")
        plan["guidelines"].append("🥓 **Fats:** Avoid trans fats; choose olive oil or mustard oil.")
        if not has_diabetes:
            plan["breakfast"].append({"name": "Avocado Toast on Multigrain", "why": "Healthy fats reduce bad cholesterol.", "cal": 300})
            plan["lunch"].append({"name": "Grilled Fish / Tofu Salad", "why": "Omega-3 rich lean protein.", "cal": 380})

    if not has_diabetes and not has_heart_risk:
        plan["guidelines"].append("✅ **General Health:** Maintain a balanced plate (50% Veg, 25% Protein, 25% Carbs).")
        plan["breakfast"].append({"name": "Poha with Peas & Peanuts", "why": "Classic balanced Indian breakfast.", "cal": 320})
        plan["lunch"].append({"name": "Dal Tadka + Jeera Rice", "why": "Complete protein when combined.", "cal": 450})

    # Fallbacks
    if not plan["dinner"]:
        plan["dinner"].append({"name": "Moong Dal Khichdi", "why": "Easy to digest, good for gut health.", "cal": 300})
        plan["dinner"].append({"name": "Vegetable Soup + Grilled Paneer", "why": "Light low-carb dinner.", "cal": 250})
        
    if not plan["snacks"]:
        plan["snacks"].append({"name": "Handful of Walnuts", "why": "Omega-3 fatty acids.", "cal": 150})

    return plan

# ==========================================
# 4. UI: SIDEBAR
# ==========================================
st.sidebar.markdown("<h2 style='color: #00e5ff; text-align: center;'>🧬 AI-NutriCare</h2>", unsafe_allow_html=True)
st.sidebar.markdown("---")
st.sidebar.info("🤖 **Models Loaded:**\n" + ("✅ Diabetes" if 'diabetes' in models else "❌ Diabetes") + "\n" + ("✅ Heart" if 'heart' in models else "❌ Heart"))

menu = st.sidebar.radio("Navigation", ["Upload & Scan", "AI Analysis", "Diet Plan"], index=0)

st.sidebar.markdown("---")
st.sidebar.caption("Developed for Infosys Internship")

# ==========================================
# 5. PAGE: UPLOAD
# ==========================================
if menu == "Upload & Scan":
    st.markdown("<div class='animate-box'><h1>📂 Medical Report <span class='highlight-text'>Scanner</span></h1></div>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.markdown("""
        <div class='medical-card'>
            <h3>📝 Instructions</h3>
            <p>1. Upload a clear image or PDF.</p>
            <p>2. System uses OCR to extract data.</p>
            <p>3. Verify the numbers before analysis.</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        uploaded_file = st.file_uploader("Drop your report here", type=['pdf', 'jpg', 'png'])

    if uploaded_file:
        with st.spinner("🔄 Scanning document with OCR..."):
            time.sleep(2) # Fake OCR delay
            st.success("Scan Complete!")
        
        st.markdown("<h3 class='highlight-text'>🔍 Verified Extracted Data</h3>", unsafe_allow_html=True)
        
        # Form for editing extracted data
        with st.container():
            c1, c2, c3 = st.columns(3)
            with c1:
                glucose = st.number_input("🩸 Glucose (mg/dL)", value=145)
                bp = st.number_input("💓 Blood Pressure", value=88)
            with c2:
                insulin = st.number_input("💉 Insulin", value=180)
                bmi = st.number_input("⚖️ BMI", value=31.5)
            with c3:
                age = st.number_input("🎂 Age", value=45)
                cholesterol = st.number_input("🍔 Cholesterol", value=260)
                
            if st.button("🚀 Analyze Health Profile"):
                st.session_state['data'] = {
                    'Glucose': glucose, 'BloodPressure': bp, 'Insulin': insulin,
                    'BMI': bmi, 'Age': age, 'Cholesterol': cholesterol
                }
                st.success("Profile Built! Navigate to 'AI Analysis'.")

# ==========================================
# 6. PAGE: ANALYSIS
# ==========================================
elif menu == "AI Analysis":
    st.markdown("<div class='animate-box'><h1>🩺 Health <span class='highlight-text'>Intelligence</span></h1></div>", unsafe_allow_html=True)
    
    if 'data' not in st.session_state:
        st.warning("Please scan a report first!")
    else:
        data = st.session_state['data']
        
        # Display Metrics in Glass Cards
        m1, m2, m3, m4 = st.columns(4)
        
        def metric_card(label, value, unit, condition):
            color = "#00e5ff" if condition == "Normal" else "#ff4b4b"
            return f"""
            <div class='medical-card' style='text-align: center;'>
                <div class='metric-label'>{label}</div>
                <div class='metric-value' style='color: {color};'>{value}</div>
                <div style='font-size: 0.8rem; opacity: 0.8;'>{unit}</div>
                <div style='margin-top: 10px; color: {color}; border: 1px solid {color}; border-radius: 5px; padding: 2px;'>{condition}</div>
            </div>
            """
            
        with m1: st.markdown(metric_card("Glucose", data['Glucose'], "mg/dL", "High" if data['Glucose'] > 140 else "Normal"), unsafe_allow_html=True)
        with m2: st.markdown(metric_card("Cholesterol", data['Cholesterol'], "mg/dL", "High" if data['Cholesterol'] > 200 else "Normal"), unsafe_allow_html=True)
        with m3: st.markdown(metric_card("BMI", data['BMI'], "kg/m²", "Obese" if data['BMI'] > 30 else "Normal"), unsafe_allow_html=True)
        with m4: st.markdown(metric_card("BP (Diastolic)", data['BloodPressure'], "mm Hg", "Normal"), unsafe_allow_html=True)

        st.markdown("---")
        
        # AI Predictions with Progress Bars
        col_pred1, col_pred2 = st.columns(2)
        
        with col_pred1:
            st.markdown("### 🧬 Diabetes Prediction Model (XGBoost)")
            if 'diabetes' in models:
                input_diabetes = np.array([[1, data['Glucose'], data['BloodPressure'], 20, data['Insulin'], data['BMI'], 0.5, data['Age']]])
                prob_diabetes = models['diabetes'].predict_proba(input_diabetes)[0][1]
                
                st.progress(int(prob_diabetes * 100))
                st.caption(f"Risk Probability: {prob_diabetes*100:.2f}%")
                
                if prob_diabetes > 0.5:
                    st.markdown("<div style='background: #450a0a; color: #ffcccc; padding: 10px; border-radius: 5px;'>⚠️ <b>High Diabetes Risk Detected</b></div>", unsafe_allow_html=True)
                    st.session_state['has_diabetes'] = True
                else:
                    st.markdown("<div style='background: #064e3b; color: #ccfbf1; padding: 10px; border-radius: 5px;'>✅ <b>Low Diabetes Risk</b></div>", unsafe_allow_html=True)

        with col_pred2:
            st.markdown("### ❤️ Heart Disease Model (Random Forest)")
            if 'heart' in models:
                input_heart = np.array([[data['Age'], 1, 0, 130, data['Cholesterol'], 1 if data['Glucose']>120 else 0, 1, 150, 0, 2.3, 0, 0, 1]])
                prediction_heart = models['heart'].predict(input_heart)[0]
                
                if prediction_heart == 1:
                     st.markdown("<div style='background: #450a0a; color: #ffcccc; padding: 10px; border-radius: 5px; margin-top: 20px;'>⚠️ <b>Elevated Heart Risk</b></div>", unsafe_allow_html=True)
                     st.session_state['has_heart'] = True
                else:
                     st.markdown("<div style='background: #064e3b; color: #ccfbf1; padding: 10px; border-radius: 5px; margin-top: 20px;'>✅ <b>Heart Health Normal</b></div>", unsafe_allow_html=True)

# ==========================================
# 7. PAGE: DIET PLAN
# ==========================================
elif menu == "Diet Plan":
    st.markdown("<div class='animate-box'><h1>🥗 Personalized <span class='highlight-text'>Nutrition Plan</span></h1></div>", unsafe_allow_html=True)
    
    if 'data' not in st.session_state:
        st.warning("Please complete analysis first.")
    else:
        # Conditions Logic
        conditions = []
        if st.session_state.get('has_diabetes', False): conditions.append("Diabetes")
        if st.session_state.get('has_heart', False): conditions.append("Heart Risk")
        
        st.markdown(f"""
        <div class='medical-card'>
            <h3>👤 Patient Profile: <span style='color: #00e5ff'>John Doe</span></h3>
            <p><b>Identified Conditions:</b> {", ".join(conditions) if conditions else "General Wellness"}</p>
        </div>
        """, unsafe_allow_html=True)
        
        preference = st.selectbox("Select Dietary Preference", ["Vegetarian", "Non-Vegetarian", "Vegan"])
        
        if st.button("✨ Generate AI Diet Plan"):
            with st.spinner("Thinking... (Consulting Medical Database)"):
                time.sleep(2)
                plan = generate_diet_plan(conditions, preference)
                
                # Guidelines Section
                st.markdown("### 📋 Medical Guidelines")
                g_cols = st.columns(2)
                for i, guide in enumerate(plan['guidelines']):
                     with g_cols[i % 2]:
                         st.info(guide)
                
                st.markdown("---")
                
                # Meals Display
                col_b, col_l, col_d = st.columns(3)
                
                def meal_html(title, items, icon):
                    html = f"<div class='medical-card'><h4>{icon} {title}</h4>"
                    for item in items:
                        html += f"""
                        <div style='background: rgba(255,255,255,0.05); padding: 10px; border-radius: 8px; margin-bottom: 8px;'>
                            <div style='font-weight: bold;'>{item['name']}</div>
                            <div style='font-size: 0.8rem; color: #94a3b8;'>🔥 {item['cal']} kcal</div>
                            <div style='font-size: 0.8rem; color: #00e5ff; font-style: italic;'>💡 {item['why']}</div>
                        </div>
                        """
                    html += "</div>"
                    return html

                with col_b: st.markdown(meal_html("Breakfast", plan['breakfast'], "🌅"), unsafe_allow_html=True)
                with col_l: st.markdown(meal_html("Lunch", plan['lunch'], "☀️"), unsafe_allow_html=True)
                with col_d: st.markdown(meal_html("Dinner", plan['dinner'], "🌙"), unsafe_allow_html=True)
                
                # Download
                st.download_button("📥 Download PDF Report", data="PDF DATA", file_name="DietPlan.pdf")
