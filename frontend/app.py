import streamlit as st
import requests
import time
import random
import datetime
import json
import re
from fpdf import FPDF

# --- Configuration ---
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI for Health",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- Custom CSS ---
def local_css():
    st.markdown("""
    <style>
        .block-container { max-width: 90% !important; padding-top: 3rem !important; }
        .stApp { background-color: #f8fafc; }
        
        div.stContainer[data-testid="stForm"], 
        div.stContainer[data-border="true"] {
            background-color: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            padding: 1.5rem;
            border: 1px solid #e2e8f0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        div.stContainer[data-border="true"]:hover {
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        
        div.stButton > button {
            border-radius: 20px;
            border: 1px solid #cbd5e1;
            background-color: #ffffff;
            color: #334155;
            font-weight: 500;
        }
        div.stButton > button:hover {
            border-color: #0ea5e9;
            color: #0ea5e9;
            background-color: #f0f9ff;
        }
        
        .meal-reason {
            font-size: 0.9rem;
            color: #64748b;
            font-style: italic;
            margin-top: 8px;
            border-top: 1px dashed #e2e8f0;
            padding-top: 8px;
        }
        
        .center-text { text-align: center; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- Helper Functions ---

def generate_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

def display_filtered_tips_grid(diet_text):
    chunks = [chunk.strip() for chunk in diet_text.split('\n\n') if chunk.strip()]
    valid_chunks = []
    
    for chunk in chunks:
        lower_chunk = chunk.lower()
        if "breakfast" in lower_chunk and "lunch" in lower_chunk:
            continue
        valid_chunks.append(chunk)

    if not valid_chunks:
        st.info("No general tips generated. Check the Daily Planner for meals.")
        return

    st.markdown(f"<p style='font-size: 1.1rem; color: #475569;'>{valid_chunks[0].replace('#', '').replace('*', '')}</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    cols = st.columns(2)
    for i, chunk in enumerate(valid_chunks[1:]):
        col = cols[i % 2]
        with col:
            with st.container(border=True):
                lines = chunk.split('\n')
                if "###" in lines[0] or "**" in lines[0]:
                    title = lines[0].replace('#', '').replace('*', '').strip()
                    st.markdown(f"#### 💡 {title}")
                    st.markdown('\n'.join(lines[1:]))
                else:
                    st.markdown(chunk)

def get_dynamic_questions(abnormalities, tests_index):
    qs = []
    if abnormalities:
        for ab in abnormalities[:2]:
            test_name = ab.get('canonical_test_key', '').replace('_', ' ').title()
            severity = ab.get('severity', 'abnormal').lower()
            if severity == "high": qs.append(f"How can I safely lower my {test_name}?")
            elif severity == "low": qs.append(f"What foods boost {test_name}?")
            else: qs.append(f"How to manage {test_name}?")
                
    if len(qs) < 3 and tests_index:
        keys = list(tests_index.keys())
        random.shuffle(keys)
        for k in keys:
            test_name = tests_index[k].get('test_name', k).title()
            q = f"Optimal range for {test_name}?"
            if q not in qs: qs.append(q)
            if len(qs) >= 3: break
            
    fallbacks = ["Foods to avoid?", "Need supplements?", "When to retest?"]
    for f in fallbacks:
        if len(qs) < 3 and f not in qs: qs.append(f)
    return qs[:3]

def fetch_ai_meals_for_date(target_date, profile, abnormalities, session_id, avoid_meals=None):
    """Hidden API call to generate meals. Uses 'avoid_meals' with a 7-day memory window."""
    date_str = target_date.strftime('%A, %B %d')
    abnormal_names = [ab.get('canonical_test_key', '').replace('_', ' ') for ab in abnormalities]
    abnormal_str = ", ".join(abnormal_names) if abnormal_names else "None (Routine healthy diet)"

    # Build the 7-Day anti-repetition constraint
    avoid_str = ""
    if avoid_meals and len(avoid_meals) > 0:
        # Keep only the last 21 meals (3 meals/day * 7 days) to ensure a 1-week rotation
        recent_avoids = avoid_meals[-21:]
        avoid_str = f"\nCRITICAL INSTRUCTION: You MUST provide completely new recipes compared to recent days. DO NOT suggest any of these meals from the past week: {', '.join(recent_avoids)}."

    prompt = f"""You are a clinical AI nutritionist. Generate a 1-day meal plan for {date_str}.
    Patient Profile:
    - Country/Region: {profile.get('country', 'Global')} (Crucial: Use local ingredients and native cuisine)
    - Diet Preference: {profile.get('diet', 'No Restrictions')}
    - Abnormal Lab Markers to heal: {abnormal_str}
    {avoid_str}

    Return ONLY a valid JSON object in this exact format. Do not include markdown formatting or extra text outside the JSON:
    {{
        "Breakfast": {{"meal": "Name and brief description of the meal", "reason": "How it specifically helps the abnormal markers"}},
        "Snack": {{"meal": "Name and description", "reason": "Medical reason"}},
        "Lunch": {{"meal": "Name and description", "reason": "Medical reason"}},
        "Dinner": {{"meal": "Name and description", "reason": "Medical reason"}}
    }}
    """

    try:
        payload = {"session_id": session_id, "message": prompt, "chat_history": []}
        resp = requests.post(f"{API_BASE_URL}/chat", json=payload)
        
        if resp.status_code == 200:
            text = resp.json()["response"]
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                meals = json.loads(json_match.group())
                for key in ["Breakfast", "Snack", "Lunch", "Dinner"]:
                    if key not in meals: meals[key] = {"meal": "Not provided by AI", "reason": "N/A"}
                return meals
    except Exception as e:
        print(f"Meal fetch error: {e}")

    return {
        "Breakfast": {"meal": "Unavailable", "reason": "Could not generate reasoning."},
        "Snack": {"meal": "Unavailable", "reason": "Could not generate reasoning."},
        "Lunch": {"meal": "Unavailable", "reason": "Could not generate reasoning."},
        "Dinner": {"meal": "Unavailable", "reason": "Could not generate reasoning."}
    }


# --- Session State ---
if "session_id" not in st.session_state: st.session_state.session_id = None
if "analysis_result" not in st.session_state: st.session_state.analysis_result = None
if "user_profile" not in st.session_state: st.session_state.user_profile = {}
if "meal_cache" not in st.session_state: st.session_state.meal_cache = {}
if "pdf_bytes_range" not in st.session_state: st.session_state.pdf_bytes_range = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {"role": "assistant", "content": "👋 Hello! I am your AI Health Consultant. I've analyzed your lab report and prepared your dashboard. What would you like to know about your results or your new nutrition plan?"}
    ]

# --- Main Logic ---
if not st.session_state.analysis_result:
    # ==========================================
    # VIEW 1: CENTERED LANDING PAGE
    # ==========================================
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    spacer_left, center_col, spacer_right = st.columns([1, 4, 1])
    
    with center_col:
        st.markdown("<h1 class='center-text'>🩺 AI for Health</h1>", unsafe_allow_html=True)
        st.markdown("<p class='center-text' style='color:#64748b; font-size:1.1rem;'>Upload your medical report for instant, AI-driven analysis, risk detection, and a personalized nutrition strategy.</p><br>", unsafe_allow_html=True)
        
        with st.container(border=True):
            st.subheader("📥 Upload Report")
            uploaded_file = st.file_uploader("Upload Lab Report", type=["pdf", "jpg", "png"], label_visibility="collapsed")
            
            with st.form("patient_data"):
                st.markdown("**Patient Profile**")
                c1, c2 = st.columns(2)
                with c1:
                    age = st.number_input("Age", value=30, min_value=1)
                    weight = st.number_input("Weight (kg)", value=70.0, min_value=1.0)
                    gender = st.selectbox("Gender", ["Male", "Female", "Other"])
                with c2:
                    height = st.number_input("Height (cm)", value=170.0, min_value=50.0)
                    country = st.text_input("Country", value="USA")
                    diet_pref = st.selectbox("Diet", ["No Restrictions", "Vegetarian", "Vegan", "Keto", "Low Carb"])
                
                st.markdown("<br>", unsafe_allow_html=True)
                submit_btn = st.form_submit_button("🚀 Securely Analyze Report", use_container_width=True)

            if submit_btn and uploaded_file:
                st.session_state.user_profile = {"diet": diet_pref, "country": country}
                
                my_bar = st.progress(0, text="Initiating secure connection...")
                try:
                    my_bar.progress(20, text="Uploading document...")
                    files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
                    upload_resp = requests.post(f"{API_BASE_URL}/upload", files=files)
                    
                    if upload_resp.status_code == 200:
                        session_id = upload_resp.json()["session_id"]
                        st.session_state.session_id = session_id
                        
                        my_bar.progress(50, text="🧠 Extracting medical markers...")
                        payload = {"session_id": session_id, "age": age, "gender": gender, "country": country, "weight": weight, "height": height, "diet_preference": diet_pref}
                        process_resp = requests.post(f"{API_BASE_URL}/process", data=payload)
                        
                        if process_resp.status_code == 200:
                            my_bar.progress(85, text="🥗 Designing nutrition strategy...")
                            time.sleep(0.5) 
                            st.session_state.analysis_result = process_resp.json()
                            my_bar.progress(100, text="✅ Analysis Complete!")
                            time.sleep(0.5)
                            st.rerun() 
                        else:
                            st.error(f"Processing failed: {process_resp.text}")
                    else:
                        st.error("Upload failed.")
                except Exception as e:
                    st.error(f"Connection error: {e}")

else:
    # ==========================================
    # VIEW 2: DASHBOARD
    # ==========================================
    result = st.session_state.analysis_result
    structured_data = result.get("structured_data", {})
    abnormalities = structured_data.get("abnormal_findings", [])
    tests_index = structured_data.get("tests_index", {})
    
    col_h1, col_h2 = st.columns([5, 1])
    with col_h1:
        st.title("📊 Health Summary")
    with col_h2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🔄 Start New Analysis", use_container_width=True):
            st.session_state.analysis_result = None
            st.session_state.meal_cache = {}
            st.session_state.pdf_bytes_range = None
            st.session_state.chat_history = [{"role": "assistant", "content": "👋 Hello! I am your AI Health Consultant. I've analyzed your lab report and prepared your dashboard. What would you like to know about your results or your new nutrition plan?"}]
            st.rerun()

    tab1, tab_cal, tab3, tab_tips, tab4 = st.tabs(["📊 Overview", "📅 Daily Planner", "💬 AI Chat", "💡 Tips", "📄 Raw Data"])

    # --- Tab 1: Health Dashboard ---
    with tab1:
        st.subheader("🧬 Core Vitals")
        bmi_data = result.get("bmi", {})
        
        m1, m2, m3 = st.columns(3)
        m1.metric("BMI Score", bmi_data.get("bmi", "N/A"))
        m2.metric("Category", bmi_data.get("category", "N/A"))
        m3.metric("Markers Analyzed", len(structured_data.get("tests_index", {})))

        st.markdown("---")
        
        c1, c2 = st.columns([1, 1])
        with c1:
            st.subheader("⚠️ Critical Markers")
            if abnormalities:
                for item in abnormalities:
                    severity = item.get("severity", "high").lower()
                    color = "#ef4444" if severity == "critical" else "#f59e0b"
                    with st.container(border=True):
                        st.markdown(f"<span style='color:{color}; font-weight:bold;'>● {severity.upper()}</span>", unsafe_allow_html=True)
                        st.markdown(f"**{item.get('canonical_test_key', '').replace('_', ' ').title()}**")
                        st.write(f"Value: {item.get('observed_value')} (Ref: {item.get('expected_range')})")
            else:
                st.success("✅ All primary markers are within normal range.")

        with c2:
            st.subheader("📋 Lab Notes")
            notes = structured_data.get("clinical_notes", {})
            interp_text = "\n".join(notes.get("interpretations", [])) or "No specific clinical notes were found in the uploaded report."
            st.info(interp_text)


    # --- Tab 2: Calendar-Based AI Daily Planner ---
    with tab_cal:
        st.subheader("📅 Your Dynamic AI Planner")
        st.markdown("<p style='color:#64748b;'>Select a date below. The AI dynamically generates unique meals featuring native ingredients to heal your specific abnormal markers.</p>", unsafe_allow_html=True)
        
        cal_col, meal_col = st.columns([1, 2.5])
        
        with cal_col:
            st.markdown("##### 📆 Select Date")
            selected_date = st.date_input("Calendar", datetime.date.today(), label_visibility="collapsed")
            date_str = selected_date.strftime('%Y-%m-%d')
            
            today = datetime.date.today()
            if selected_date < today:
                st.warning(f"🕒 **{selected_date.strftime('%B %d, %Y')}** has passed. Here is what was scheduled:")
            elif selected_date == today:
                st.info(f"📍 **Today**, {selected_date.strftime('%B %d, %Y')}")
            else:
                st.info(f"📅 **Upcoming:** {selected_date.strftime('%B %d, %Y')}")

            st.markdown("---")
            st.markdown("##### 📥 Export Multi-Day Plan")
            st.caption("Generate a strict, non-repeating PDF diet plan.")
            
            # Sleek dropdown for PDF duration
            duration_choice = st.selectbox("Select Duration", ["Next 7 Days", "Next 15 Days", "1 Month (30 Days)"], label_visibility="collapsed")
            
            if st.button("Generate PDF Data", use_container_width=True):
                st.session_state.pdf_bytes_range = None
                
                days_map = {"Next 7 Days": 7, "Next 15 Days": 15, "1 Month (30 Days)": 30}
                total_days = days_map[duration_choice]
                
                start_date = today
                end_date = start_date + datetime.timedelta(days=total_days - 1)
                
                pdf_content = f"Tailored Nutrition Plan\n{start_date.strftime('%b %d')} to {end_date.strftime('%b %d, %Y')}\n\n"
                
                gen_bar = st.progress(0, text="Starting Generation...")
                used_meals_history = [] 
                
                for i in range(total_days):
                    step_date = start_date + datetime.timedelta(days=i)
                    step_str = step_date.strftime('%Y-%m-%d')
                    gen_bar.progress(int((i/total_days)*100), text=f"AI drafting meals for {step_date.strftime('%b %d')}...")
                    
                    if step_str not in st.session_state.meal_cache:
                        st.session_state.meal_cache[step_str] = fetch_ai_meals_for_date(
                            step_date, st.session_state.user_profile, abnormalities, st.session_state.session_id, avoid_meals=used_meals_history
                        )
                    
                    day_meals = st.session_state.meal_cache[step_str]
                    
                    # Add current meals to history to ensure the next loop is different (keeps last 21 via fetch_ai_meals_for_date)
                    used_meals_history.extend([day_meals['Breakfast']['meal'], day_meals['Lunch']['meal'], day_meals['Dinner']['meal']])
                    
                    pdf_content += f"--- {step_date.strftime('%A, %b %d')} ---\n"
                    for meal_type in ["Breakfast", "Snack", "Lunch", "Dinner"]:
                        pdf_content += f"{meal_type}: {day_meals[meal_type]['meal']}\n"
                        pdf_content += f"Reason: {day_meals[meal_type]['reason']}\n\n"
                        
                gen_bar.progress(100, text="Ready for Download!")
                st.session_state.pdf_bytes_range = generate_pdf(pdf_content)
                time.sleep(1)
                gen_bar.empty()
                st.rerun()

            if st.session_state.pdf_bytes_range:
                st.download_button(
                    label="✅ Download Prepared PDF",
                    data=st.session_state.pdf_bytes_range,
                    file_name=f"AI_Meal_Plan_{duration_choice.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

        with meal_col:
            # Build list of previously used meals across all cached days to ensure calendar clicks are also unique
            existing_meals = []
            sorted_dates = sorted(list(st.session_state.meal_cache.keys()))
            for d in sorted_dates:
                cached_day = st.session_state.meal_cache[d]
                existing_meals.extend([cached_day['Breakfast']['meal'], cached_day['Lunch']['meal'], cached_day['Dinner']['meal']])

            if date_str not in st.session_state.meal_cache:
                with st.spinner(f"🧑‍🍳 AI is crafting a highly unique {st.session_state.user_profile.get('diet', '')} menu tailored to your labs..."):
                    st.session_state.meal_cache[date_str] = fetch_ai_meals_for_date(
                        selected_date, st.session_state.user_profile, abnormalities, st.session_state.session_id, avoid_meals=existing_meals
                    )

            daily_meals = st.session_state.meal_cache[date_str]

            m_col1, m_col2 = st.columns(2)
            with m_col1:
                with st.container(border=True):
                    st.markdown("#### 🍳 Breakfast")
                    st.markdown(f"**{daily_meals['Breakfast']['meal']}**")
                    st.markdown(f"<div class='meal-reason'>🎯 {daily_meals['Breakfast']['reason']}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown("#### 🍎 Snack")
                    st.markdown(f"**{daily_meals['Snack']['meal']}**")
                    st.markdown(f"<div class='meal-reason'>🎯 {daily_meals['Snack']['reason']}</div>", unsafe_allow_html=True)
                    
            with m_col2:
                with st.container(border=True):
                    st.markdown("#### 🥗 Lunch")
                    st.markdown(f"**{daily_meals['Lunch']['meal']}**")
                    st.markdown(f"<div class='meal-reason'>🎯 {daily_meals['Lunch']['reason']}</div>", unsafe_allow_html=True)
                with st.container(border=True):
                    st.markdown("#### 🍗 Dinner")
                    st.markdown(f"**{daily_meals['Dinner']['meal']}**")
                    st.markdown(f"<div class='meal-reason'>🎯 {daily_meals['Dinner']['reason']}</div>", unsafe_allow_html=True)


    # --- Tab 3: Dynamic AI Chat ---
    with tab3:
        st.subheader("💬 Ask AI Consultant")
        
        chat_container = st.container(height=500)
        with chat_container:
            for message in st.session_state.chat_history:
                avatar = "🩺" if message["role"] == "assistant" else "👤"
                with st.chat_message(message["role"], avatar=avatar):
                    st.markdown(message["content"])

        st.caption("✨ Recommended Questions:")
        dynamic_qs = get_dynamic_questions(abnormalities, tests_index)
        q1, q2, q3 = st.columns(3)
        
        prompt = st.chat_input("Ask about your markers or diet...")
        
        if q1.button(f"🔍 {dynamic_qs[0]}", use_container_width=True): prompt = dynamic_qs[0]
        if q2.button(f"🍏 {dynamic_qs[1]}", use_container_width=True): prompt = dynamic_qs[1]
        if q3.button(f"💡 {dynamic_qs[2]}", use_container_width=True): prompt = dynamic_qs[2]

        if prompt:
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            st.rerun()

        if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
            with chat_container:
                with st.chat_message("assistant", avatar="🩺"):
                    with st.spinner("Analyzing..."):
                        try:
                            chat_payload = {
                                "session_id": st.session_state.session_id, 
                                "message": st.session_state.chat_history[-1]["content"], 
                                "chat_history": st.session_state.chat_history[:-1]
                            }
                            response = requests.post(f"{API_BASE_URL}/chat", json=chat_payload)
                            if response.status_code == 200:
                                bot_reply = response.json()["response"]
                                st.markdown(bot_reply)
                                st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
                        except Exception as e:
                            st.error(f"Connection Error: {e}")

    # --- Tab 4: Tips ---
    with tab_tips:
        st.subheader("💡 Long-Term Strategy & Tips")
        diet_text = result.get("diet_plan", "")
        # Filters out the 1-day sample plan from the general tips
        display_filtered_tips_grid(diet_text)

    # --- Tab 5: Raw Data ---
    with tab4:
        st.json(structured_data)