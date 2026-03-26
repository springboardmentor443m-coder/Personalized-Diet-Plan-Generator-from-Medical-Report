import streamlit as st
import requests
import time
import random
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
        /* Expand the main dashboard width */
        .block-container {
            max-width: 90% !important;
            padding-top: 3rem !important;
        }
        
        .stApp { background-color: #f8fafc; }
        
        /* Modern White Cards for Forms & Containers */
        div.stContainer[data-testid="stForm"], 
        div.stContainer[data-border="true"] {
            background-color: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
            padding: 1.5rem;
            border: 1px solid #e2e8f0;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        
        /* Subtle hover effect for the new diet cards */
        div.stContainer[data-border="true"]:hover {
            box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
        }
        
        /* Pill Buttons for Chat */
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
        
        .center-text { text-align: center; }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- Helper Function: FPDF ---
def generate_pdf(text_content):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    clean_text = text_content.encode('latin-1', 'replace').decode('latin-1')
    pdf.multi_cell(0, 8, txt=clean_text)
    return pdf.output(dest='S').encode('latin-1')

# --- Helper Function: NEW Diet Plan Card Grid ---
def display_appealing_diet_grid(diet_text):
    """Parses text into chunks and displays them in a clean 2-column grid of white cards."""
    # Split the AI output into distinct paragraphs/sections
    chunks = [chunk.strip() for chunk in diet_text.split('\n\n') if chunk.strip()]
    
    if not chunks:
        st.info("No diet plan generated yet.")
        return

    # Print the introductory text (usually the first chunk) across the full width
    st.markdown(f"<p style='font-size: 1.1rem; color: #475569;'>{chunks[0].replace('#', '').replace('*', '')}</p>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Create a 2-column grid for the rest of the points/meals
    cols = st.columns(2)
    for i, chunk in enumerate(chunks[1:]):
        col = cols[i % 2] # Alternate columns
        with col:
            with st.container(border=True):
                # If the chunk has a markdown header or bold start, emphasize it
                lines = chunk.split('\n')
                if "###" in lines[0] or "**" in lines[0]:
                    title = lines[0].replace('#', '').replace('*', '').strip()
                    st.markdown(f"#### 🍽️ {title}")
                    st.markdown('\n'.join(lines[1:]))
                else:
                    st.markdown(chunk)

# --- Helper Function: Dynamic FAQs ---
def get_dynamic_questions(abnormalities, tests_index):
    qs = []
    if abnormalities:
        for ab in abnormalities[:2]:
            test_name = ab.get('canonical_test_key', '').replace('_', ' ').title()
            severity = ab.get('severity', 'abnormal').lower()
            if severity == "high":
                qs.append(f"How can I safely lower my {test_name}?")
            elif severity == "low":
                qs.append(f"What foods boost {test_name}?")
            else:
                qs.append(f"How to manage {test_name}?")
                
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

# --- Session State ---
if "session_id" not in st.session_state: st.session_state.session_id = None
if "analysis_result" not in st.session_state: st.session_state.analysis_result = None

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [
        {
            "role": "assistant", 
            "content": "👋 Hello! I am your AI Health Consultant. I've analyzed your lab report and prepared your dashboard. What would you like to know about your results or your new nutrition plan?"
        }
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
                            my_bar.progress(85, text="🥗 Designing nutrition plan...")
                            time.sleep(0.5) 
                            st.session_state.analysis_result = process_resp.json()
                            my_bar.progress(100, text="✅ Analysis Complete!")
                            time.sleep(0.5)
                            st.rerun() 
                        else:
                            st.error("Processing failed.")
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
            st.session_state.chat_history = [{"role": "assistant", "content": "👋 Hello! I am your AI Health Consultant. I've analyzed your lab report and prepared your dashboard. What would you like to know about your results or your new nutrition plan?"}]
            st.rerun()

    tab1, tab2, tab3, tab4 = st.tabs(["📊 Overview", "🥗 Nutrition Plan", "💬 AI Chat", "📄 Raw Data"])

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

    # --- Tab 2: Nutrition Plan (NEW GRID LAYOUT) ---
    with tab2:
        st.subheader("🥗 Your Custom Nutrition Strategy")
        diet_text = result.get("diet_plan", "")
        
        # Deploy the new grid card layout
        display_appealing_diet_grid(diet_text)

        st.markdown("<br>", unsafe_allow_html=True)
        try:
            st.download_button("📥 Download Plan as PDF", data=generate_pdf(diet_text), file_name="AI_Health_Diet_Plan.pdf", mime="application/pdf")
        except:
            pass

    # --- Tab 3: Dynamic AI Chat ---
    with tab3:
        st.subheader("💬 Ask AI")
        
        # Container for chat history
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
        
        # Interactive FAQ Buttons
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

    with tab4:
        st.json(structured_data)