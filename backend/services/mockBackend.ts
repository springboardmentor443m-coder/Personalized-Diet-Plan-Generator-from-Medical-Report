import { HealthMetrics, PredictionResult, DietPlanFull, Language } from '../types';

// This simulates the processing your Python backend would do with PIMA Diabetes & Heart Disease datasets
export const analyzeMedicalReport = async (file: File): Promise<{ metrics: HealthMetrics; predictions: PredictionResult }> => {
  return new Promise((resolve) => {
    // Simulating API latency / OCR processing time
    setTimeout(() => {
      // MOCK DATA: In a real app, this comes from the Python ML model
      const metrics: HealthMetrics = {
        glucose: 145, // High (Diabetes Dataset)
        bloodPressure: 88, // Normal-High
        cholesterol: 260, // High (Heart Disease Dataset)
        bmi: 31.5, // Obese
        age: 45,
        insulin: 180
      };

      const hasDiabetes = metrics.glucose > 125;
      const riskHeartDisease = metrics.cholesterol > 240 || metrics.bloodPressure > 140;

      const alerts: string[] = [];
      if (metrics.glucose > 140) alerts.push("⚠️ Critical: Blood Sugar extremely high – Consult Doctor immediately.");
      if (metrics.cholesterol > 240) alerts.push("⚠️ Critical: High Cholesterol detected.");
      if (metrics.bmi > 30) alerts.push("⚠️ Warning: Obesity detected (BMI > 30).");

      resolve({
        metrics,
        predictions: {
          hasDiabetes,
          diabetesProbability: 0.89,
          riskHeartDisease,
          heartRiskProbability: 0.72,
          criticalAlerts: alerts
        }
      });
    }, 2500);
  });
};

const dietContent = {
  en: {
    rec: [
      "Low Glycemic Index (GI) foods to manage glucose.",
      "High fiber intake to reduce cholesterol absorption.",
      "Sodium restriction (<2300mg) for blood pressure control.",
      "Plant-based proteins preferred over red meat."
    ],
    b1: "Oats Upma with Vegetables", w1: "High fiber oats slow sugar absorption.",
    b2: "Ragi Porridge", w2: "Ragi has low glycemic index.",
    l1: "Multigrain Roti (2) + Methi Dal", w3: "Fenugreek (Methi) helps improve insulin sensitivity.",
    l2: "Brown Rice + Rajma", w4: "Complex carbs provide sustained energy.",
    s1: "Roasted Chana (Chickpeas)", w5: "High protein, low fat crunch.",
    s2: "Cucumber & Carrot Sticks", w6: "Zero cholesterol hydration.",
    d1: "Grilled Paneer Salad", w7: "Light protein for easier digestion at night.",
    d2: "Moong Dal Khichdi", w8: "Easy to digest gut-friendly meal."
  },
  hi: {
    rec: [
      "ग्लूकोज को नियंत्रित करने के लिए कम ग्लाइसेमिक इंडेक्स (GI) वाले खाद्य पदार्थ।",
      "कोलेस्ट्रॉल को कम करने के लिए उच्च फाइबर सेवन।",
      "रक्तचाप नियंत्रण के लिए नमक का कम सेवन (<2300mg)।",
      "रेड मीट की जगह प्लांट-बेस्ड प्रोटीन को प्राथमिकता दें।"
    ],
    b1: "सब्जियों के साथ ओट्स उपमा", w1: "उच्च फाइबर ओट्स शुगर को धीरे अवशोषित करते हैं।",
    b2: "रागी दलिया", w2: "रागी का ग्लाइसेमिक इंडेक्स कम होता है।",
    l1: "मल्टीग्रेन रोटी (2) + मेथी दाल", w3: "मेथी इंसुलिन संवेदनशीलता में सुधार करती है।",
    l2: "ब्राउन राइस + राजमा", w4: "कॉम्प्लेक्स कार्ब्स निरंतर ऊर्जा प्रदान करते हैं।",
    s1: "भुने हुए चने", w5: "उच्च प्रोटीन, कम वसा वाला नाश्ता।",
    s2: "खीरा और गाजर", w6: "शून्य कोलेस्ट्रॉल, शरीर को हाइड्रेट रखता है।",
    d1: "ग्रिल्ड पनीर सलाद", w7: "रात में आसानी से पचने वाला हल्का प्रोटीन।",
    d2: "मूंग दाल खिचड़ी", w8: "पेट के लिए हल्की और सुपाच्य।"
  },
  gu: {
    rec: [
      "ગ્લુકોઝને નિયંત્રિત કરવા માટે ઓછા ગ્લાયકેમિક ઇન્ડેક્સ (GI) ખોરાક.",
      "કોલેસ્ટ્રોલ શોષણ ઘટાડવા માટે ઉચ્ચ ફાઇબર.",
      "બ્લડ પ્રેશર નિયંત્રણ માટે મીઠું ઓછું લેવું (<2300mg).",
      "રેડ મીટને બદલે પ્લાન્ટ-આધારિત પ્રોટીન શ્રેષ્ઠ."
    ],
    b1: "શાકભાજી સાથે ઓટ્સ ઉપમા", w1: "હાઈ ફાઈબર ઓટ્સ સુગર શોષણ ધીમું કરે છે.",
    b2: "રાગી પોરીજ", w2: "રાગીનો ગ્લાયકેમિક ઇન્ડેક્સ ઓછો છે.",
    l1: "મલ્ટીગ્રેન રોટલી (2) + મેથી દાળ", w3: "મેથી ઇન્સ્યુલિન સુધારવામાં મદદ કરે છે.",
    l2: "બ્રાઉન રાઇસ + રાજમા", w4: "જટિલ કાર્બોહાઇડ્રેટ્સ સતત ઊર્જા આપે છે.",
    s1: "શેકેલા ચણા", w5: "ઉચ્ચ પ્રોટીન, ઓછી ચરબી.",
    s2: "કાકડી અને ગાજર", w6: "શૂન્ય કોલેસ્ટ્રોલ.",
    d1: "ગ્રીલ્ડ પનીર સલાડ", w7: "રાત્રે પચવામાં સરળ પ્રોટીન.",
    d2: "મગ દાળ ખીચડી", w8: "પચવામાં સરળ અને હળવો ખોરાક."
  },
  te: {
    rec: [
      "గ్లూకోజ్‌ను నిర్వహించడానికి తక్కువ గ్లైసెమిక్ ఇండెక్స్ (GI) ఆహారాలు.",
      "కొలెస్ట్రాల్ శోషణను తగ్గించడానికి అధిక ఫైబర్ తీసుకోవడం.",
      "రక్తపోటు నియంత్రణకు సోడియం నియంత్రణ (<2300mg).",
      "రెడ్ మీట్ కంటే మొక్కల ఆధారిత ప్రోటీన్లకు ప్రాధాన్యత."
    ],
    b1: "కూరగాయలతో ఓట్స్ ఉప్మా", w1: "అధిక ఫైబర్ చక్కెర శోషణను నెమ్మదిస్తుంది.",
    b2: "రాగి జావ", w2: "రాగి తక్కువ గ్లైసెమిక్ ఇండెక్స్ కలిగి ఉంటుంది.",
    l1: "మల్టీగ్రెయిన్ రోటీ (2) + మెంతి పప్పు", w3: "మెంతి ఇన్సులిన్ సున్నితత్వాన్ని మెరుగుపరుస్తుంది.",
    l2: "బ్రౌన్ రైస్ + రాజ్మా", w4: "కాంప్లెక్స్ పిండి పదార్థాలు శక్తిని ఇస్తాయి.",
    s1: "వేయించిన శనగలు", w5: "అధిక ప్రోటీన్, తక్కువ కొవ్వు.",
    s2: "కీర దోసకాయ & క్యారెట్", w6: "సున్నా కొలెస్ట్రాల్.",
    d1: "గ్రిల్డ్ పన్నీర్ సలాడ్", w7: "రాత్రిపూట సులభంగా జీర్ణమయ్యే ప్రోటీన్.",
    d2: "పెసర పప్పు కిచిడీ", w8: "జీర్ణం కావడం సులభం."
  }
};

export const generateDietPlan = async (metrics: HealthMetrics, lang: Language = 'en'): Promise<DietPlanFull> => {
  return new Promise((resolve) => {
    const content = dietContent[lang] || dietContent['en'];
    
    setTimeout(() => {
      resolve({
        confidenceScore: 85,
        recommendations: content.rec,
        weeklyPlan: [
          {
            day: lang === 'hi' ? "सोमवार" : lang === 'gu' ? "સોમવાર" : lang === 'te' ? "సోమవారం" : "Monday",
            breakfast: { name: content.b1, calories: 280, why: content.w1 },
            breakfastAlt: { name: content.b2, calories: 250, why: content.w2 },
            lunch: { name: content.l1, calories: 450, why: content.w3 },
            lunchAlt: { name: content.l2, calories: 480, why: content.w4 },
            snack: { name: content.s1, calories: 120, why: content.w5 },
            snackAlt: { name: content.s2, calories: 60, why: content.w6 },
            dinner: { name: content.d1, calories: 300, why: content.w7 },
            dinnerAlt: { name: content.d2, calories: 320, why: content.w8 }
          },
          // Repeating logic for demo purposes (usually would be unique per day)
          {
            day: lang === 'hi' ? "मंगलवार" : lang === 'gu' ? "મંગળવાર" : lang === 'te' ? "మంగళవారం" : "Tuesday",
            breakfast: { name: "Besan Chilla", calories: 260, why: "Protein-rich start." }, 
            breakfastAlt: { name: "Idli Sambar", calories: 240, why: "Steamed food." },
            lunch: { name: "Quinoa Salad", calories: 420, why: "Lowers cholesterol." },
            lunchAlt: { name: "Bajra Roti", calories: 440, why: "Iron rich." },
            snack: { name: "Green Tea", calories: 50, why: "Antioxidants." },
            snackAlt: { name: "Apple", calories: 80, why: "Lowers cholesterol." },
            dinner: { name: "Soya Curry", calories: 350, why: "Reduces LDL." },
            dinnerAlt: { name: "Lentil Soup", calories: 280, why: "Low calorie." }
          }
        ]
      });
    }, 1500);
  });
};