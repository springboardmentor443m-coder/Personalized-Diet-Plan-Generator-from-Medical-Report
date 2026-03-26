import sys
import os

# Add the current directory to sys.path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.rag_chatbot import generate_chat_response

def test_chatbot_logic():
    print("--- Starting AI Clinical Assistant Logic Test ---")
    
    # Mock Structured Data
    mock_structured_data = {
        "patient_information": {
            "patient_name": "John Doe",
            "age_years": 45,
            "gender": "Male",
            "calculated_bmi": 28.5,
            "bmi_category": "Overweight"
        },
        "abnormal_findings": [
            {
                "canonical_test_key": "cholesterol_total",
                "observed_value": "240",
                "expected_range": "< 200",
                "severity": "high"
            },
            {
                "canonical_test_key": "hdl_cholesterol",
                "observed_value": "35",
                "expected_range": "> 40",
                "severity": "low"
            }
        ],
        "tests_index": {
            "cholesterol_total": {"test_name": "Total Cholesterol", "value": "240", "units": "mg/dL", "reference_range": "< 200 mg/dL"},
            "hdl_cholesterol": {"test_name": "HDL Cholesterol", "value": "35", "units": "mg/dL", "reference_range": "> 40 mg/dL"}
        },
        "tests_by_category": {
            "lipid_profile": ["cholesterol_total", "hdl_cholesterol"]
        }
    }
    
    # Mock Diet Plan
    mock_diet = {
        "executive_summary": "User has high total cholesterol and low HDL. Focus on heart-healthy fats and fiber.",
        "superfoods": ["Walnuts", "Oats", "Fatty Fish", "Avocado"],
        "foods_to_avoid": ["Saturated Fats", "Trans Fats", "Sugary Snacks"],
        "daily_plan": {
            "breakfast": "Oatmeal with walnuts",
            "lunch": "Grilled salmon salad with avocado",
            "dinner": "Lentil soup with spinach"
        }
    }
    
    # Test Query 1: Abnormal findings
    query1 = "What are the most critical abnormal findings in my report?"
    print(f"\nQUERY: {query1}")
    try:
        response1 = generate_chat_response(query1, mock_structured_data, mock_diet)
        print(f"RESPONSE: {response1}")
    except Exception as e:
        print(f"ERROR: {e}")

    # Test Query 2: Dietary advice
    query2 = "What superfoods should I eat for my cholesterol?"
    print(f"\nQUERY: {query2}")
    try:
        response2 = generate_chat_response(query2, mock_structured_data, mock_diet)
        print(f"RESPONSE: {response2}")
    except Exception as e:
        print(f"ERROR: {e}")

    print("\n--- Test Complete ---")

if __name__ == "__main__":
    test_chatbot_logic()
