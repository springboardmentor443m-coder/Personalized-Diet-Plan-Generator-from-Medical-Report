def generate_diet(condition=None, metrics=None):

    # -----------------------------
    # FULL CONDITION-BASED PLANS
    # -----------------------------
    plans = {

        "Healthy": {
            "Breakfast": "Fruits & Oatmeal",
            "Lunch": "Balanced Home Meal",
            "Dinner": "Light Protein Diet"
        },

        "Anemia": {
            "Breakfast": "Iron-rich foods (Dates, Spinach)",
            "Lunch": "Green Vegetables & Lentils",
            "Dinner": "Beetroot / Pomegranate"
        },

        "Infection": {
            "Breakfast": "Vitamin C Fruits",
            "Lunch": "Protein & Fluids",
            "Dinner": "Light & Easily Digestible Food"
        },

        "Vitamin Deficiency": {
            "Breakfast": "Milk / Eggs",
            "Lunch": "Nuts & Seeds",
            "Dinner": "Vitamin D Rich Foods"
        },

        "Kidney Risk": {
            "Breakfast": "Low Sodium Diet",
            "Lunch": "Controlled Protein Intake",
            "Dinner": "Hydration-focused Meal"
        }
    }

    # ✅ If ML prediction available → Use it
    if condition:
        return plans.get(condition, {"Advice": "Consult Doctor"})

    # -----------------------------
    # ✅ SMART FALLBACK LOGIC 🔥
    # -----------------------------
    if metrics:

        advice = {}

        # ---- Hemoglobin Check ----
        if "Hemoglobin" in metrics:
            if metrics["Hemoglobin"] < 12:
                advice["Focus"] = "Low Hemoglobin Detected"
                advice["Diet"] = "Increase Iron-rich foods (Spinach, Dates, Beetroot)"
                return advice

        # ---- WBC Check ----
        if "WBC" in metrics:
            if metrics["WBC"] > 11000:
                advice["Focus"] = "Possible Infection"
                advice["Diet"] = "Increase Vitamin C & Fluids"
                return advice

        # ---- Vitamin D Check ----
        if "VitaminD" in metrics:
            if metrics["VitaminD"] < 20:
                advice["Focus"] = "Low Vitamin D"
                advice["Diet"] = "Sun Exposure + Milk / Eggs / Nuts"
                return advice

        # ---- Creatinine Check ----
        if "Creatinine" in metrics:
            if metrics["Creatinine"] > 1.3:
                advice["Focus"] = "High Creatinine"
                advice["Diet"] = "Low Sodium + Hydration"
                return advice

        # ---- Platelets Check ----
        if "Platelets" in metrics:
            if metrics["Platelets"] < 150000:
                advice["Focus"] = "Low Platelets"
                advice["Diet"] = "Papaya Leaf / Hydrating Foods"
                return advice

    # ✅ Default Safe Advice
    return {"Advice": "Maintain Balanced Diet & Healthy Lifestyle"}
