from groq import Groq
import os
from dotenv import load_dotenv
import json

load_dotenv()

class GroqService:
    def __init__(self):
        api_key = os.getenv('GROQ_API_KEY')
        self.client = None
        self.model = "llama-3.3-70b-versatile"
        if not api_key:
            return
        try:
            self.client = Groq(api_key=api_key)
        except Exception:
            self.client = None
    
    def generate_ai_doctor_note(self, health_data):
        conditions = []
        for condition, data in health_data.get('ml_predictions', {}).items():
            if data.get('detected'):
                conditions.append(f"{condition.replace('_', ' ')} ({data['risk']} risk)")
        
        lab_issues = []
        for lab, data in health_data.get('lab_values', {}).items():
            if data['status'] not in ['normal', 'optimal', 'unknown']:
                lab_issues.append(f"{lab.replace('_', ' ')}: {data['status']}")
        
        if not conditions and not lab_issues:
            return "Patient's lab values are within normal range. Continue maintaining a balanced diet and regular exercise routine."
        
        prompt = f"""As a medical doctor, write a brief clinical note (2-3 sentences) for a patient with:
Conditions: {', '.join(conditions) if conditions else 'None'}
Lab Issues: {', '.join(lab_issues) if lab_issues else 'None'}

Provide medical advice and dietary recommendations. Be professional and concise.

Output:"""
        
        if not self.client:
            return f"Patient shows signs of {', '.join(conditions) if conditions else 'normal health'}. Recommend dietary modifications and regular monitoring."

        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.6,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception:
            return f"Patient shows signs of {', '.join(conditions) if conditions else 'normal health'}. Recommend dietary modifications and regular monitoring."
    
    def generate_diet_plan(self, health_data, days=3, preferences=None):
        import re
        
        age = health_data.get('patient_info', {}).get('age', 30)
        gender = health_data.get('patient_info', {}).get('gender', 'M')
        bmi_data = health_data.get('lab_values', {}).get('bmi', {})
        
        if isinstance(bmi_data, dict):
            bmi = bmi_data.get('value', 23)
        elif isinstance(bmi_data, (int, float)):
            bmi = bmi_data
        else:
            bmi = 23

        condition_tags = set(health_data.get('_conditions', []))
        for condition, data in health_data.get('ml_predictions', {}).items():
            if data.get('detected'):
                condition_tags.add(condition)
        
        calories = health_data.get('_calculated_calories')
        used_manual_calories = bool(calories)
        if not calories:
            if bmi < 18.5:
                calories = 2200
            elif bmi < 25:
                calories = 1800
            elif bmi < 30:
                calories = 1600
            else:
                calories = 1400
            if age > 50:
                calories -= 200
            if gender and gender.upper() == 'F':
                calories -= 200

        if not used_manual_calories:
            cond_text = " ".join(condition_tags).lower()
            if 'diabetes' in cond_text:
                calories -= 150
            if 'cholesterol' in cond_text:
                calories -= 100
            if 'obesity' in cond_text:
                calories -= 250
        calories = int(max(1200, calories))
        
        conditions = []
        for condition, data in health_data.get('ml_predictions', {}).items():
            if data.get('detected'):
                conditions.append(f"{condition.replace('_', ' ').title()} ({data['risk']} risk - {data['probability']:.0%})")
        
        lab_summary = []
        for lab, data in health_data.get('lab_values', {}).items():
            if data['status'] not in ['normal', 'optimal', 'unknown']:
                lab_summary.append(f"{lab.replace('_', ' ').title()}: {data['value']} ({data['status']})")
        
        diet_type = "vegetarian"
        if preferences and preferences.get('mixed_diet'):
            diet_type = "mixed vegetarian and non-vegetarian"
        elif preferences and preferences.get('non_veg'):
            diet_type = "non-vegetarian"
        elif preferences and preferences.get('vegan'):
            diet_type = "vegan"
        
        allergy_text = ""
        if preferences and preferences.get('allergies'):
            allergy_text = f" AVOID: {', '.join(preferences['allergies'])}"

        macro_targets = self._calculate_macro_targets(calories, conditions, diet_type)
        macro_text = (
            f"Daily macro targets: carbs {macro_targets['carbs_pct']}% ({macro_targets['carbs_g']} g), "
            f"protein {macro_targets['protein_pct']}% ({macro_targets['protein_g']} g), "
            f"fat {macro_targets['fat_pct']}% ({macro_targets['fat_g']} g)."
        )
        
        conditions_str = ', '.join(conditions) if conditions else 'No health issues'
        labs_str = ', '.join(lab_summary) if lab_summary else 'Normal'
        
        cal_dist = {
            'breakfast': int(calories * 0.25),
            'lunch': int(calories * 0.35),
            'dinner': int(calories * 0.30),
            'snack': int(calories * 0.10)
        }
        
        prompt = f"""Create {days}-day {diet_type} Indian diet ({calories} kcal/day).
Patient: Age {age}, Gender {gender}, BMI {bmi}, {conditions_str}, Labs: {labs_str}{allergy_text}

Calorie distribution: Breakfast {cal_dist['breakfast']} kcal, Lunch {cal_dist['lunch']} kcal, Dinner {cal_dist['dinner']} kcal, Snack {cal_dist['snack']} kcal

IMPORTANT:
- Follow {diet_type} strictly.
- Respect allergies strictly.{allergy_text if allergy_text else ' None'}
- Keep each meal macros realistic and aligned with the macro targets.
- Do NOT use apostrophes. Write "patient" not "patient's". Write "helps" not "it's".
{macro_text}

Return ONLY valid JSON with NO markdown:
{{
"day_1":{{"breakfast":{{"meal":"name","portion":"amount","reason":"why it helps patient health","ingredients":["item1","item2"],"macros":{{"protein":20,"carbs":45,"fat":10}}}},"lunch":{{...}},"snack":{{...}},"dinner":{{...}}}},
"day_2":{{...}},
"day_3":{{...}}
}}"""
        
        print(f"\n=== CALLING GROQ AI ===")
        print(f"Patient: Age {age}, BMI {bmi}, Calories {calories}")
        
        if not self.client:
            return self._fallback_diet_plan(conditions, days, calories, diet_type, preferences.get('allergies', []) if preferences else [])

        try:
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.7,
                max_tokens=2500
            )
            
            result = response.choices[0].message.content.strip()
            
            result = re.sub(r'```json?', '', result)
            result = re.sub(r'```', '', result)
            result = result.strip()
            
            start = result.find('{')
            end = result.rfind('}') + 1
            if start != -1 and end > start:
                result = result[start:end]
            
            result = re.sub(r',\s*}', '}', result)
            result = re.sub(r',\s*]', ']', result)
            
            result = re.sub(r"([a-zA-Z])'([a-zA-Z])", r"\1\2", result)
            result = re.sub(r"it's", "it is", result, flags=re.IGNORECASE)
            result = re.sub(r"patient's", "patient", result, flags=re.IGNORECASE)
            result = re.sub(r"([a-z])'s\b", r"\1", result, flags=re.IGNORECASE)
            
            diet_plan = json.loads(result)
            print(f" GROQ SUCCESS - Generated AI diet plan")
            
            diet_plan['_calories'] = calories
            diet_plan['_macro_targets'] = macro_targets
            diet_plan['_patient_bmi'] = bmi
            diet_plan['_source'] = 'groq'
            return diet_plan
            
        except Exception as e:
            print(f" GROQ FAILED: {e}")
            print("Using fallback")
            return self._fallback_diet_plan(conditions, days, calories, diet_type, preferences.get('allergies', []) if preferences else [])
    
    def _fallback_diet_plan(self, conditions, days, calories=1800, diet_type='vegetarian', allergies=None):
        import random
        import re
        allergies = allergies or []
        
        cal_dist = {
            'breakfast': int(calories * 0.25),
            'lunch': int(calories * 0.35),
            'dinner': int(calories * 0.30),
            'snack': int(calories * 0.10)
        }
        
        veg_meals = {
            "breakfast": [
                {"meal": "Oats porridge with berries and flaxseeds", "portion": "1 bowl (250g)", "reason": "High fiber helps control blood sugar and cholesterol", "ingredients": ["oats", "berries", "flaxseeds"], "macros": {"protein": 12, "carbs": 55, "fat": 8}},
                {"meal": "Moong dal cheela with mint chutney", "portion": "2 pieces", "reason": "Protein rich, low fat, good for diabetes management", "ingredients": ["moong dal", "mint", "spices"], "macros": {"protein": 15, "carbs": 48, "fat": 6}},
                {"meal": "Vegetable poha with peanuts", "portion": "1 plate (200g)", "reason": "Light, nutritious, provides sustained energy", "ingredients": ["poha", "vegetables", "peanuts"], "macros": {"protein": 10, "carbs": 52, "fat": 7}},
                {"meal": "Idli with sambar and coconut chutney", "portion": "3 idlis", "reason": "Fermented food, easy to digest, low GI", "ingredients": ["rice", "urad dal", "vegetables"], "macros": {"protein": 11, "carbs": 50, "fat": 5}},
                {"meal": "Upma with vegetables", "portion": "1 bowl", "reason": "Whole grain, fiber rich, controls hunger", "ingredients": ["semolina", "vegetables", "spices"], "macros": {"protein": 9, "carbs": 54, "fat": 6}},
            ],
            "lunch": [
                {"meal": "Brown rice with dal and mixed vegetables", "portion": "1 plate (150g rice)", "reason": "Balanced meal with fiber, protein, and nutrients", "ingredients": ["brown rice", "dal", "vegetables"], "macros": {"protein": 18, "carbs": 75, "fat": 10}},
                {"meal": "Quinoa pulao with raita", "portion": "1 bowl (200g)", "reason": "High protein, complete amino acids, low GI", "ingredients": ["quinoa", "vegetables", "yogurt"], "macros": {"protein": 20, "carbs": 70, "fat": 12}},
                {"meal": "Roti with palak paneer and salad", "portion": "2 rotis", "reason": "Iron and calcium rich, good for overall health", "ingredients": ["wheat", "spinach", "paneer"], "macros": {"protein": 22, "carbs": 68, "fat": 14}},
                {"meal": "Grilled chicken with brown rice and vegetables", "portion": "120g chicken, 100g rice", "reason": "Lean protein, complex carbs, balanced nutrition", "ingredients": ["chicken", "brown rice", "vegetables"], "macros": {"protein": 35, "carbs": 65, "fat": 8}},
                {"meal": "Fish curry with quinoa", "portion": "150g fish, 100g quinoa", "reason": "Omega-3 fatty acids, helps reduce cholesterol", "ingredients": ["fish", "quinoa", "spices"], "macros": {"protein": 38, "carbs": 60, "fat": 10}},
            ],
            "snack": [
                {"meal": "Roasted makhana", "portion": "1 cup (30g)", "reason": "Low calorie, high protein snack", "ingredients": ["makhana", "spices"], "macros": {"protein": 5, "carbs": 18, "fat": 2}},
                {"meal": "Fresh fruit salad", "portion": "1 bowl (150g)", "reason": "Vitamins, minerals, and natural fiber", "ingredients": ["apple", "banana", "orange"], "macros": {"protein": 2, "carbs": 22, "fat": 1}},
                {"meal": "Sprouts chaat with lemon", "portion": "1 bowl (100g)", "reason": "Protein, minerals, aids digestion", "ingredients": ["sprouts", "lemon", "spices"], "macros": {"protein": 8, "carbs": 15, "fat": 2}},
                {"meal": "Cucumber and carrot sticks with hummus", "portion": "1 cup", "reason": "Low calorie, hydrating, nutritious", "ingredients": ["cucumber", "carrot", "hummus"], "macros": {"protein": 6, "carbs": 16, "fat": 4}},
                {"meal": "Roasted chickpeas", "portion": "50g", "reason": "Protein and fiber rich, satisfying snack", "ingredients": ["chickpeas", "spices"], "macros": {"protein": 9, "carbs": 20, "fat": 3}},
            ],
            "dinner": [
                {"meal": "Vegetable soup with multigrain bread", "portion": "1 bowl soup, 2 slices bread", "reason": "Light, easy to digest, nutrient dense", "ingredients": ["vegetables", "bread", "herbs"], "macros": {"protein": 12, "carbs": 58, "fat": 6}},
                {"meal": "Roti with mixed vegetables curry", "portion": "2 rotis, 1 bowl curry", "reason": "Fiber rich, low calorie, balanced meal", "ingredients": ["wheat", "vegetables", "spices"], "macros": {"protein": 14, "carbs": 60, "fat": 8}},
                {"meal": "Khichdi with curd", "portion": "1 bowl (200g)", "reason": "Comfort food, probiotic, easy digestion", "ingredients": ["rice", "dal", "yogurt"], "macros": {"protein": 16, "carbs": 55, "fat": 7}},
                {"meal": "Grilled fish with steamed vegetables", "portion": "150g fish, 150g vegetables", "reason": "Lean protein, omega-3, low calorie", "ingredients": ["fish", "vegetables", "herbs"], "macros": {"protein": 32, "carbs": 45, "fat": 9}},
                {"meal": "Dal with roti and salad", "portion": "1 bowl dal, 2 rotis", "reason": "Complete protein, fiber, vitamins", "ingredients": ["dal", "wheat", "vegetables"], "macros": {"protein": 18, "carbs": 62, "fat": 6}},
            ]
        }
        
        non_veg_keywords = ['chicken', 'fish', 'egg', 'mutton', 'meat', 'prawn', 'shrimp']
        vegan_block_keywords = non_veg_keywords + ['milk', 'paneer', 'curd', 'yogurt', 'cheese', 'ghee', 'butter']
        allergy_keywords = {
            'nuts': ['almond', 'walnut', 'cashew', 'peanut', 'pistachio', 'hazelnut'],
            'dairy': ['milk', 'cheese', 'paneer', 'yogurt', 'curd', 'butter', 'ghee', 'cream'],
            'eggs': ['egg', 'omelette'],
            'gluten': ['wheat', 'roti', 'chapati', 'bread', 'pasta', 'noodles'],
            'soy': ['soy', 'tofu', 'soya'],
            'shellfish': ['shrimp', 'prawn', 'crab', 'lobster']
        }

        def is_allowed(meal):
            text = " ".join([
                meal.get('meal', ''),
                meal.get('portion', ''),
                meal.get('reason', ''),
                " ".join(meal.get('ingredients', []))
            ]).lower()

            if diet_type == 'vegetarian' and any(k in text for k in non_veg_keywords):
                return False
            if diet_type == 'vegan' and any(k in text for k in vegan_block_keywords):
                return False

            for allergy in allergies:
                a = allergy.lower().strip()
                terms = allergy_keywords.get(a, [a])
                if any(re.search(rf'\b{re.escape(term)}\b', text) for term in terms):
                    return False
            return True

        macro_targets = self._calculate_macro_targets(calories, conditions, diet_type)

        plan = {}
        for i in range(days):
            day = {}
            plan[f"day_{i+1}"] = {
                "breakfast": None,
                "lunch": None,
                "snack": None,
                "dinner": None
            }
            for meal_type in ["breakfast", "lunch", "snack", "dinner"]:
                pool = [m for m in veg_meals[meal_type] if is_allowed(m)] or veg_meals[meal_type]
                day[meal_type] = random.choice(pool)
            plan[f"day_{i+1}"] = day
        
        plan['_calories'] = calories
        plan['_distribution'] = cal_dist
        plan['_macro_targets'] = macro_targets
        plan['_source'] = 'fallback'
        return plan

    def _calculate_macro_targets(self, calories, conditions, diet_type):
        carbs_pct, protein_pct, fat_pct = 45, 25, 30

        cond_text = " ".join(conditions).lower()
        if 'diabetes' in cond_text:
            carbs_pct, protein_pct, fat_pct = 40, 30, 30
        if 'cholesterol' in cond_text:
            carbs_pct, protein_pct, fat_pct = 45, 30, 25
        if 'obesity' in cond_text:
            carbs_pct, protein_pct, fat_pct = 35, 35, 30
        if diet_type == 'vegan' and protein_pct < 28:
            protein_pct = 28
            carbs_pct = 100 - protein_pct - fat_pct
        if diet_type == 'non-vegetarian' and protein_pct < 30:
            protein_pct = 30
            carbs_pct = 100 - protein_pct - fat_pct
        if diet_type == 'mixed vegetarian and non-vegetarian' and protein_pct < 28:
            protein_pct = 28
            carbs_pct = 100 - protein_pct - fat_pct

        carbs_g = int(round((calories * carbs_pct / 100) / 4))
        protein_g = int(round((calories * protein_pct / 100) / 4))
        fat_g = int(round((calories * fat_pct / 100) / 9))
        return {
            'carbs_pct': carbs_pct,
            'protein_pct': protein_pct,
            'fat_pct': fat_pct,
            'carbs_g': carbs_g,
            'protein_g': protein_g,
            'fat_g': fat_g
        }
