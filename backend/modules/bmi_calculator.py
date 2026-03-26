def calculate_bmi(weight: float, height: float):
    if not weight or not height:
        return None
    try:
        if height > 3:
            height_m = height / 100
        else:
            height_m = height
        bmi = weight / (height_m ** 2)
        
        if bmi < 18.5:
            category = "Underweight"
        elif bmi < 25:
            category = "Normal"
        elif bmi < 30:
            category = "Overweight"
        else:
            category = "Obese"
            
        return {
            "bmi_value": float(f"{bmi:.2f}"),
            "bmi_category": category
        }
    except:
        return None
