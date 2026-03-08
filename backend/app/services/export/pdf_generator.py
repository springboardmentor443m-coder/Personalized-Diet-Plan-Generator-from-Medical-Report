from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from datetime import datetime
import os

class PDFGenerator:
    def generate_diet_plan_pdf(self, health_data, diet_result, output_path):
        c = canvas.Canvas(output_path, pagesize=letter)
        width, height = letter
        
        y = height - 1*inch
        
        c.setFont("Helvetica-Bold", 20)
        c.drawString(1*inch, y, "AI-NutriCare: Personalized Diet Plan")
        y -= 0.5*inch
        
        c.setFont("Helvetica", 10)
        c.drawString(1*inch, y, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        y -= 0.5*inch
        
        patient_info = health_data.get('patient_info', {})
        if patient_info:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, y, "Patient Information")
            y -= 0.25*inch
            c.setFont("Helvetica", 10)
            if 'name' in patient_info:
                c.drawString(1*inch, y, f"Name: {patient_info['name']}")
                y -= 0.2*inch
            if 'age' in patient_info:
                c.drawString(1*inch, y, f"Age: {patient_info['age']} years")
                y -= 0.3*inch
        
        summary = diet_result.get('summary', {})
        conditions = summary.get('detected_conditions', [])
        
        if conditions:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, y, "Health Analysis")
            y -= 0.25*inch
            c.setFont("Helvetica", 10)
            for cond in conditions:
                c.drawString(1*inch, y, f"• {cond['name'].title()}: {cond['risk']} risk ({cond['probability']:.0%})")
                y -= 0.2*inch
            y -= 0.2*inch
        
        abnormal_labs = summary.get('abnormal_labs', [])
        if abnormal_labs:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, y, "Lab Results")
            y -= 0.25*inch
            c.setFont("Helvetica", 10)
            for lab in abnormal_labs[:5]:
                c.drawString(1*inch, y, f"• {lab['test']}: {lab['value']} ({lab['status']})")
                y -= 0.2*inch
            y -= 0.2*inch
        
        c.setFont("Helvetica-Bold", 14)
        c.drawString(1*inch, y, "Personalized Diet Plan")
        y -= 0.4*inch
        
        diet_plan = diet_result.get('diet_plan', {})
        day_keys = sorted([k for k, v in diet_plan.items() if k.startswith('day_') and isinstance(v, dict)])
        for day_key in day_keys:
            if y < 2*inch:
                c.showPage()
                y = height - 1*inch
            
            day_num = day_key.split('_')[1]
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, y, f"Day {day_num}")
            y -= 0.3*inch
            
            day_meals = diet_plan.get(day_key, {})
            c.setFont("Helvetica", 10)
            
            for meal_type in ['breakfast', 'lunch', 'snack', 'dinner']:
                if meal_type in day_meals:
                    meal = day_meals[meal_type]
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(1.2*inch, y, f"{meal_type.title()}:")
                    y -= 0.2*inch
                    c.setFont("Helvetica", 9)
                    c.drawString(1.4*inch, y, f"{meal.get('meal', 'N/A')} ({meal.get('portion', 'N/A')})")
                    y -= 0.15*inch
                    c.drawString(1.4*inch, y, f"Why: {meal.get('reason', 'Recommended for health goals')}")
                    y -= 0.25*inch
            
            y -= 0.2*inch
        
        if y < 3*inch:
            c.showPage()
            y = height - 1*inch
        
        recommendations = summary.get('recommendations', [])
        if recommendations:
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, y, "Health Recommendations")
            y -= 0.3*inch
            c.setFont("Helvetica", 10)
            for rec in recommendations:
                c.drawString(1*inch, y, f"• {rec}")
                y -= 0.2*inch
        
        c.save()
        return output_path

if __name__ == "__main__":
    generator = PDFGenerator()
    
    sample_health = {
        'patient_info': {'name': 'Test Patient', 'age': 45},
        'ml_predictions': {
            'diabetes': {'detected': True, 'risk': 'medium', 'probability': 0.63}
        }
    }
    
    sample_diet = {
        'summary': {
            'detected_conditions': [{'name': 'diabetes', 'risk': 'medium', 'probability': 0.63}],
            'abnormal_labs': [{'test': 'glucose', 'value': 145, 'status': 'prediabetes'}],
            'recommendations': ['Monitor blood sugar', 'Follow low-carb diet']
        },
        'diet_plan': {
            'day_1': {
                'breakfast': {'meal': 'Oats', 'portion': '1 bowl', 'reason': 'Low GI'},
                'lunch': {'meal': 'Brown rice', 'portion': '1 plate', 'reason': 'Fiber'},
                'snack': {'meal': 'Nuts', 'portion': 'handful', 'reason': 'Protein'},
                'dinner': {'meal': 'Roti', 'portion': '2 rotis', 'reason': 'Light'}
            }
        }
    }
    
    output = generator.generate_diet_plan_pdf(sample_health, sample_diet, 'test_diet_plan.pdf')
    print(f"PDF generated: {output}")
