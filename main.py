from extraction_module import extract_health_data
from ml_module import analyze_health
from diet_generator import generate_diet
from chatbot_module import chatbot_response

sample_text = "Glucose: 140 Cholesterol: 220 BMI: 27"

data = extract_health_data(sample_text)

condition = analyze_health(data)

diet = generate_diet(condition)

advice = chatbot_response(condition)

print("Health Data:", data)
print("Condition:", condition)
print("Diet Plan:", diet)
print("Chatbot Advice:", advice)
