from app.services.nlp.groq_service import GroqService
import json

class DietPlanGenerator:
    def __init__(self):
        self.groq = GroqService()
    
    def generate(self, health_data, days=3, preferences=None):
        if preferences is None:
            preferences = {'vegetarian': True}
        
        diet_plan = self.groq.generate_diet_plan(health_data, days, preferences)
        
        summary = self._create_summary(health_data, [])
        
        return {
            'diet_plan': diet_plan,
            'summary': summary,
            'dietary_restrictions': [],
            'preferences': preferences
        }
    
    def _create_summary(self, health_data, restrictions):
        conditions = []
        for condition, data in health_data.get('ml_predictions', {}).items():
            if data.get('detected'):
                conditions.append({
                    'name': condition,
                    'risk': data['risk'],
                    'probability': data['probability']
                })
        
        abnormal_labs = []
        for lab, data in health_data.get('lab_values', {}).items():
            if data['status'] not in ['normal', 'optimal', 'unknown']:
                abnormal_labs.append({
                    'test': lab,
                    'value': data['value'],
                    'status': data['status']
                })
        
        return {
            'detected_conditions': conditions,
            'abnormal_labs': abnormal_labs,
            'dietary_restrictions': restrictions,
            'recommendations': health_data.get('recommendations', [])
        }

if __name__ == "__main__":
    generator = DietPlanGenerator()
    
    sample_data = {
        'ml_predictions': {
            'diabetes': {'detected': True, 'risk': 'medium', 'probability': 0.63}
        },
        'lab_values': {
            'glucose': {'value': 145, 'status': 'prediabetes'}
        },
        'recommendations': ['Monitor blood sugar', 'Follow low-carb diet']
    }
    
    result = generator.generate(sample_data, days=3)
    print(json.dumps(result, indent=2))
