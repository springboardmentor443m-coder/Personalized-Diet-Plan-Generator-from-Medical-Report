export const uploadReport = async (file, patientData = {}) => {
  const formData = new FormData();
  formData.append("file", file);
  
  // Append explicit patient info
  if (patientData.patientName) formData.append("patient_name", patientData.patientName);

  // Append physical details for BMI synthesis (Phase 2)
  if (patientData.age) formData.append("age", patientData.age);
  if (patientData.gender) formData.append("gender", patientData.gender);
  if (patientData.weight) formData.append("weight", patientData.weight);
  if (patientData.height) formData.append("height", patientData.height);
  if (patientData.dietaryPreference) formData.append("dietary_preference", patientData.dietaryPreference);

  try {
    const response = await fetch(
      "http://127.0.0.1:8001/analyze-report/",
      {
        method: "POST",
        body: formData,
      }
    );

    return await response.json();
  } catch (error) {
    console.error("Backend error:", error);
    return { success: false };
  }
};

export const downloadStructuredPdf = async (structuredData, diet, userData) => {
  try {
    const response = await fetch("http://127.0.0.1:8001/download-report/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        structured_data: structuredData,
        diet: diet,
        user_info: userData
      })
    });

    if (!response.ok) {
        console.error("Failed to generate PDF");
        return;
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'AI_NutriCare_Diagnostic_Report.pdf';
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);

  } catch (error) {
    console.error("PDF Download Error:", error);
  }
};

export const sendChatMessage = async (query, structuredData, diet, chatHistory = []) => {
  try {
    const response = await fetch("http://127.0.0.1:8001/chat/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        query: query,
        structured_data: structuredData,
        diet: diet,
        chat_history: chatHistory
      })
    });
    
    if (!response.ok) {
        throw new Error("Chat request failed");
    }

    const data = await response.json();
    if (data.success) {
        return data.reply;
    } else {
        throw new Error("Backend returned failure");
    }
  } catch (error) {
    console.error("Chat Error:", error);
    return "I'm having trouble connecting to my medical database. Check your connection.";
  }
};