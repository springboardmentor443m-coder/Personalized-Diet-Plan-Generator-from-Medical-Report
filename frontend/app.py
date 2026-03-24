import streamlit as st
import requests
import pandas as pd
import json

# --- Configuration ---
API_BASE_URL = "http://localhost:8000"

st.set_page_config(
    page_title="AI Nutritionist & Medical Analyzer",
    page_icon="🩺",
    layout="wide"
)

# --- Session State Management ---
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Sidebar: Input & Configuration ---
with st.sidebar:
    st.title("📋 Patient Details")
    
    uploaded_file = st.file_uploader("Upload Lab Report", type=["pdf", "jpg", "png"])
    
    st.markdown("---")
    
    with st.form("patient_data"):
        c1, c2 = st.columns(2)
        with c1:
            age = st.number_input("Age", min_value=1, max_value=120, value=30)
            weight = st.number_input("Weight (kg)", min_value=1.0, value=70.0)
        with c2:
            gender = st.selectbox("Gender", ["Male", "Female", "Other"])
            height = st.number_input("Height (cm)", min_value=50.0, value=170.0)
            
        country = st.text_input("Country/Region", value="USA")
        diet_pref = st.selectbox("Diet Preference", 
            ["No Restrictions", "Vegetarian", "Vegan", "Keto", "Low Carb", "Gluten Free"]
        )
        
        submit_btn = st.form_submit_button("🚀 Analyze & Generate Plan")

# --- Logic: Handle Submission ---
if submit_btn and uploaded_file:
    with st.spinner("Uploading and analyzing document... This may take a moment."):
        try:
            # 1. Upload File
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            upload_resp = requests.post(f"{API_BASE_URL}/upload", files=files)
            
            if upload_resp.status_code == 200:
                session_id = upload_resp.json()["session_id"]
                st.session_state.session_id = session_id
                
                # 2. Process Document
                payload = {
                    "session_id": session_id,
                    "age": age,
                    "gender": gender,
                    "country": country,
                    "weight": weight,
                    "height": height,
                    "diet_preference": diet_pref
                }
                
                process_resp = requests.post(f"{API_BASE_URL}/process", data=payload)
                
                if process_resp.status_code == 200:
                    st.session_state.analysis_result = process_resp.json()
                    st.success("Analysis Complete!")
                else:
                    st.error(f"Processing failed: {process_resp.text}")
            else:
                st.error(f"Upload failed: {upload_resp.text}")
                
        except Exception as e:
            st.error(f"Connection error: {e}")

elif submit_btn and not uploaded_file:
    st.warning("Please upload a medical report first.")

# --- Main Interface ---
st.title("🩺 AI Medical & Nutrition Assistant")

if st.session_state.analysis_result:
    result = st.session_state.analysis_result
    
    # Create Tabs
    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Health Dashboard", 
        "🥗 Diet Plan", 
        "💬 AI Consultant", 
        "📄 Full Report"
    ])

# --- Tab 1: Health Dashboard ---
    with tab1:
        st.header("Health Overview")
        
        # 1. GET DATA HANDLES
        structured_data = result.get("structured_data", {})
        patient_info = structured_data.get("patient_information", {})
        clinical_notes = structured_data.get("clinical_notes", {})
        
        # 2. PATIENT INFO CARD (New!)
        # Shows the metadata extracted from the top of the PDF
        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            c1.caption(f"**Patient Name:**\n{patient_info.get('patient_name', 'Unknown')}")
            c2.caption(f"**Report Date:**\n{patient_info.get('collection_datetime', 'Unknown')}")
            c3.caption(f"**Lab Name:**\n{patient_info.get('laboratory_name', 'Unknown')}")
            c4.caption(f"**Report Status:**\n{patient_info.get('report_status', 'Final')}")
        
        st.divider()

        # 3. BMI SECTION (Existing)
        bmi_data = result.get("bmi", {})
        col1, col2, col3 = st.columns(3)
        col1.metric("BMI Score", bmi_data.get("bmi", "N/A"))
        col2.metric("Category", bmi_data.get("category", "N/A"))
        
        bmi_val = bmi_data.get("bmi", 0)
        if bmi_val < 18.5:
            st.info("Underweight")
        elif 18.5 <= bmi_val < 25:
            st.success("Healthy Weight")
        elif 25 <= bmi_val < 30:
            st.warning("Overweight")
        else:
            st.error("Obese")

        st.divider()

        # 4. ABNORMAL FINDINGS (Existing - Visual Polish)
        st.subheader("⚠️ Critical Findings")
        abnormalities = structured_data.get("abnormal_findings", [])

        if abnormalities:
            for item in abnormalities:
                # Use a red box for critical, yellow for high
                severity = item.get("severity", "high")
                color = "red" if severity == "critical" else "orange"
                
                with st.expander(f"🚨 {item.get('canonical_test_key', '').replace('_', ' ').title()}", expanded=True):
                    c1, c2 = st.columns(2)
                    c1.markdown(f"**Value:** {item.get('observed_value')} (Range: {item.get('expected_range')})")
                    c2.markdown(f"**Severity:** :{color}[{severity.upper()}]")
        else:
            st.success("✅ No abnormal findings detected.")

        st.divider()

        # 5. CLINICAL INTERPRETATION (New!)
        # Shows the summary/notes the lab doctor wrote
        st.subheader("📋 Lab Interpretations & Notes")
        
        interpretations = clinical_notes.get("interpretations", [])
        comments = clinical_notes.get("comments", [])
        
        if interpretations:
            st.info("\n".join(interpretations))
        elif comments:
            st.info("\n".join(comments))
        else:
            st.caption("No specific clinical notes extracted from the report.")

        st.divider()

        # 6. FULL TEST BREAKDOWN BY CATEGORY (New!)
        # Shows every single test grouped by category (Lipid, Liver, etc.)
        st.subheader("🔬 Comprehensive Test Results")
        
        categories = structured_data.get("tests_by_category", {})
        tests_index = structured_data.get("tests_index", {})

        if categories:
            for category_name, test_keys in categories.items():
                # Only show category if it has tests
                if test_keys:
                    with st.expander(f"📂 {category_name.replace('_', ' ').title()} ({len(test_keys)} tests)"):
                        # Create a clean table-like view
                        for key in test_keys:
                            test = tests_index.get(key, {})
                            if test:
                                uc1, uc2, uc3 = st.columns([2, 1, 1])
                                uc1.text(test.get("test_name", key))
                                uc2.markdown(f"**{test.get('value')}** {test.get('units') or ''}")
                                
                                # Visual indicator for Normal/High/Low
                                interp = test.get("interpretation", "normal")
                                if interp == "high":
                                    uc3.warning("High")
                                elif interp == "low":
                                    uc3.warning("Low")
                                else:
                                    uc3.success("Normal")
        else:
            st.write("No categorized test data available.")

    # --- Tab 2: Diet Plan ---
    with tab2:
        st.header("🥗 Personalized Nutrition Plan")
        st.markdown(result.get("diet_plan", "No plan generated."))
        
        st.download_button(
            label="Download Diet Plan",
            data=result.get("diet_plan", ""),
            file_name="diet_plan.md",
            mime="text/markdown"
        )

    # --- Tab 3: Chat Interface ---
    with tab3:
        st.header("💬 Chat with your Report")
        
        # Display chat messages
        for message in st.session_state.chat_history:
            with st.chat_message(message["role"]):
                st.markdown(message["content"])

        # Chat input
        if prompt := st.chat_input("Ask about your blood test or diet plan..."):
            # Add user message to history
            st.session_state.chat_history.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            # Get bot response
            with st.spinner("Thinking..."):
                try:
                    chat_payload = {
                        "session_id": st.session_state.session_id,
                        "message": prompt,
                        "chat_history": st.session_state.chat_history[:-1] # Send history excluding current msg
                    }
                    
                    response = requests.post(f"{API_BASE_URL}/chat", json=chat_payload)
                    
                    if response.status_code == 200:
                        bot_reply = response.json()["response"]
                        st.session_state.chat_history.append({"role": "assistant", "content": bot_reply})
                        with st.chat_message("assistant"):
                            st.markdown(bot_reply)
                    else:
                        st.error("Failed to get response from AI.")
                except Exception as e:
                    st.error(f"Chat Error: {e}")

    # --- Tab 4: Full Report (Raw Data) ---
    with tab4:
        st.header("📄 Extracted Medical Data")
        st.json(result.get("structured_data", {}))

else:
    # Landing Page State
    st.info("👈 Please upload a lab report and fill in your details to start.")
    st.markdown("""
    ### How it works:
    1. **Upload** your medical lab report (PDF/Image).
    2. **Enter** your basic profile details.
    3. **AI Analysis** performs OCR to read your report.
    4. **Get Results**:
        - 📊 structured breakdown of abnormal values.
        - 🥗 customized diet plan based on your specific blood markers.
        - 💬 chat assistant that knows your report context.
    """)