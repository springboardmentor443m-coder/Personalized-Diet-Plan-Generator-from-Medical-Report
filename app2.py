import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime

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

# --- Helper Functions ---
def get_severity_color(interpretation):
    """Return color based on test interpretation."""
    colors = {
        "normal": "🟢",
        "low": "🟡",
        "high": "🟡",
        "borderline": "🟠",
        "critical": "🔴"
    }
    return colors.get(interpretation, "⚪")

def get_category_icon(category):
    """Return icon for test category."""
    icons = {
        "complete_blood_count": "🩸",
        "liver_function": "🫀",
        "kidney_function": "🫘",
        "lipid_profile": "💊",
        "thyroid_profile": "🦋",
        "diabetes_related": "🍬",
        "vitamins_and_minerals": "💊",
        "electrolytes": "⚡",
        "other_tests": "🔬"
    }
    return icons.get(category, "📊")

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
                    st.success("✅ Analysis Complete!")
                else:
                    st.error(f"Processing failed: {process_resp.text}")
            else:
                st.error(f"Upload failed: {upload_resp.text}")
                
        except Exception as e:
            st.error(f"Connection error: {e}")

elif submit_btn and not uploaded_file:
    st.warning("⚠️ Please upload a medical report first.")

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

    # --- Tab 1: ENHANCED Health Dashboard ---
    with tab1:
        st.header("📊 Comprehensive Health Dashboard")
        
        # ========================================
        # SECTION 1: Patient Information
        # ========================================
        structured_data = result.get("structured_data", {})
        patient_info = structured_data.get("patient_information", {})
        
        if patient_info and any(patient_info.values()):
            with st.expander("👤 Patient Information", expanded=True):
                col1, col2, col3, col4 = st.columns(4)
                
                if patient_info.get("patient_name"):
                    col1.metric("Name", patient_info["patient_name"])
                if patient_info.get("age_years"):
                    col2.metric("Age", f"{patient_info['age_years']} years")
                if patient_info.get("gender"):
                    col3.metric("Gender", patient_info["gender"])
                if patient_info.get("lab_number"):
                    col4.metric("Lab Number", patient_info["lab_number"])
                
                if patient_info.get("collection_datetime") or patient_info.get("report_datetime"):
                    st.divider()
                    c1, c2, c3 = st.columns(3)
                    if patient_info.get("collection_datetime"):
                        c1.caption(f"🗓️ Sample Collected: {patient_info['collection_datetime']}")
                    if patient_info.get("report_datetime"):
                        c2.caption(f"📋 Report Date: {patient_info['report_datetime']}")
                    if patient_info.get("laboratory_name"):
                        c3.caption(f"🏥 Lab: {patient_info['laboratory_name']}")
        
        st.divider()
        
        # ========================================
        # SECTION 2: BMI & Health Metrics
        # ========================================
        st.subheader("⚖️ Body Metrics")
        bmi_data = result.get("bmi", {})
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("BMI Score", f"{bmi_data.get('bmi', 'N/A')}")
        col2.metric("Category", bmi_data.get('category', 'N/A'))
        col3.metric("Weight", f"{weight} kg")
        col4.metric("Height", f"{height} cm")
        
        # BMI Status with color coding
        bmi_val = bmi_data.get("bmi", 0)
        if bmi_val < 18.5:
            st.info("💡 Status: Underweight - Consider consulting a nutritionist for healthy weight gain strategies")
        elif 18.5 <= bmi_val < 25:
            st.success("✅ Status: Healthy Weight - Maintain your current lifestyle")
        elif 25 <= bmi_val < 30:
            st.warning("⚠️ Status: Overweight - Consider dietary modifications and increased physical activity")
        else:
            st.error("🚨 Status: Obese - Medical consultation recommended for personalized weight management")
        
        st.divider()
        
        # ========================================
        # SECTION 3: Critical Abnormalities Alert
        # ========================================
        abnormalities = structured_data.get("abnormal_findings", [])
        
        if abnormalities:
            st.subheader("🚨 Abnormal Test Results")
            st.warning(f"Found **{len(abnormalities)}** test(s) outside normal range")
            
            for item in abnormalities:
                test_name = item.get('canonical_test_key', 'Unknown Test').replace('_', ' ').title()
                severity = item.get("severity", "high")
                
                # Color coding by severity
                if severity == "critical":
                    alert_type = "error"
                    icon = "🔴"
                elif severity == "high":
                    alert_type = "warning"
                    icon = "🟡"
                else:
                    alert_type = "info"
                    icon = "🟠"
                
                with st.expander(f"{icon} {test_name}", expanded=(severity == "critical")):
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Your Value", item.get("observed_value", "N/A"))
                    c2.metric("Normal Range", item.get("expected_range", "N/A"))
                    c3.metric("Severity", severity.upper())
        else:
            st.success("✅ No critical abnormalities detected! All tests within normal ranges.")
        
        st.divider()
        
        # ========================================
        # SECTION 4: All Test Results by Category
        # ========================================
        st.subheader("🔬 Complete Test Results by Category")
        
        tests_index = structured_data.get("tests_index", {})
        tests_by_category = structured_data.get("tests_by_category", {})
        
        if tests_index and tests_by_category:
            # Create category tabs
            category_names = list(tests_by_category.keys())
            readable_names = [name.replace('_', ' ').title() for name in category_names]
            
            # Filter out empty categories
            non_empty_categories = [
                (cat_key, cat_name) for cat_key, cat_name in zip(category_names, readable_names)
                if tests_by_category.get(cat_key)
            ]
            
            if non_empty_categories:
                for cat_key, cat_name in non_empty_categories:
                    test_keys = tests_by_category[cat_key]
                    icon = get_category_icon(cat_key)
                    
                    with st.expander(f"{icon} {cat_name} ({len(test_keys)} tests)", expanded=False):
                        # Create a table for this category
                        test_data = []
                        
                        for test_key in test_keys:
                            test_info = tests_index.get(test_key, {})
                            
                            test_data.append({
                                "Status": get_severity_color(test_info.get("interpretation", "normal")),
                                "Test Name": test_info.get("test_name", test_key.replace('_', ' ').title()),
                                "Value": test_info.get("value", "N/A"),
                                "Units": test_info.get("units", ""),
                                "Reference Range": test_info.get("reference_range", "N/A"),
                                "Interpretation": (test_info.get("interpretation") or "normal").capitalize()
                            })
                        
                        if test_data:
                            df = pd.DataFrame(test_data)
                            st.dataframe(df, use_container_width=True, hide_index=True)
        else:
            st.info("No categorized test data available")
        
        st.divider()
        
        # ========================================
        # SECTION 5: Clinical Notes & Recommendations
        # ========================================
        clinical_notes = structured_data.get("clinical_notes", {})
        
        if clinical_notes and any(clinical_notes.values()):
            st.subheader("📝 Clinical Notes & Recommendations")
            
            col1, col2 = st.columns(2)
            
            with col1:
                if clinical_notes.get("interpretations"):
                    st.markdown("**🔍 Interpretations:**")
                    for note in clinical_notes["interpretations"]:
                        st.markdown(f"- {note}")
                
                if clinical_notes.get("comments"):
                    st.markdown("**💬 Comments:**")
                    for comment in clinical_notes["comments"]:
                        st.markdown(f"- {comment}")
            
            with col2:
                if clinical_notes.get("recommendations"):
                    st.markdown("**✅ Recommendations:**")
                    for rec in clinical_notes["recommendations"]:
                        st.markdown(f"- {rec}")
                
                if clinical_notes.get("notes"):
                    st.markdown("**📌 Additional Notes:**")
                    for note in clinical_notes["notes"]:
                        st.markdown(f"- {note}")
            
            if clinical_notes.get("disclaimers"):
                st.divider()
                st.caption("⚠️ **Disclaimers:**")
                for disclaimer in clinical_notes["disclaimers"]:
                    st.caption(f"- {disclaimer}")
        
        # ========================================
        # SECTION 6: Summary Statistics
        # ========================================
        st.divider()
        st.subheader("📈 Test Summary Statistics")
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_tests = len(tests_index)
        normal_count = sum(1 for t in tests_index.values() if t.get("interpretation") == "normal")
        abnormal_count = len(abnormalities)
        
        col1.metric("Total Tests", total_tests)
        col2.metric("Normal Results", normal_count, delta=None)
        col3.metric("Abnormal Results", abnormal_count, delta=None if abnormal_count == 0 else f"-{abnormal_count}")
        
        if total_tests > 0:
            health_score = int((normal_count / total_tests) * 100)
            col4.metric("Health Score", f"{health_score}%")
            
            # Progress bar for health score
            st.progress(health_score / 100, text=f"Overall Health Score: {health_score}%")

    # --- Tab 2: Diet Plan ---
    with tab2:
        st.header("🥗 Personalized Nutrition Plan")
        st.markdown(result.get("diet_plan", "No plan generated."))
        
        st.download_button(
            label="📥 Download Diet Plan",
            data=result.get("diet_plan", ""),
            file_name=f"diet_plan_{datetime.now().strftime('%Y%m%d')}.md",
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
                        "chat_history": st.session_state.chat_history[:-1]
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
        st.header("📄 Complete Extracted Medical Data")
        
        # Show metadata
        metadata = structured_data.get("metadata", {})
        if metadata:
            st.subheader("Document Metadata")
            col1, col2, col3 = st.columns(3)
            col1.metric("Total Pages", metadata.get("total_pages", "N/A"))
            col2.metric("Pages Detected", len(metadata.get("page_numbers_detected", [])))
            col3.metric("Report Complete", "✅" if metadata.get("report_end_marker_present") else "⚠️")
        
        st.divider()
        
        # Show full JSON
        st.json(structured_data)

else:
    # Landing Page State
    st.info("👈 Please upload a lab report and fill in your details to start.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("""
        ### 🎯 How it works:
        
        1. **📤 Upload** your medical lab report (PDF/Image)
        2. **✍️ Enter** your basic profile details  
        3. **🤖 AI Analysis** performs OCR and intelligent extraction
        4. **📊 Get Comprehensive Results**:
           - Complete test breakdown with normal/abnormal indicators
           - Patient information and report metadata
           - Clinical notes and doctor's recommendations
           - Customized diet plan based on your blood markers
           - Interactive chat assistant with report context
        
        ### ✨ Features:
        - 🔬 Automated test categorization (CBC, Liver, Kidney, Lipids, etc.)
        - 🎨 Color-coded health indicators
        - 📈 Health score calculation
        - 💊 Personalized nutrition recommendations
        - 💬 AI chat for questions about your results
        """)
    
    with col2:
        st.image("https://img.icons8.com/fluency/96/000000/health-book.png", width=150)
        st.metric("Supported Formats", "PDF, JPG, PNG,JPEG")
        st.metric("Processing Time", "~30 sec")