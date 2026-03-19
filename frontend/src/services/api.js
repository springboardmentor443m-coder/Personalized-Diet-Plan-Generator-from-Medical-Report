const API_URL = 'http://localhost:8000';

export const api = {
  async extract(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_URL}/api/upload`, {
      method: 'POST',
      body: formData
    });
    return res.json();
  },

  async generate(extracted, allergies, preferences, height, weight, activityLevel) {
    const payload = { extracted, allergies, preferences };
    if (height && weight) {
      payload.height = height;
      payload.weight = weight;
      payload.activityLevel = activityLevel || 'moderate';
    }
    const res = await fetch(`${API_URL}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(error);
    }
    return res.json();
  },

  async chat(question, extracted, dietPlan, history = []) {
    const res = await fetch(`${API_URL}/api/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        question,
        extracted,
        diet_plan: dietPlan || {},
        history
      })
    });
    if (!res.ok) {
      const error = await res.text();
      throw new Error(error);
    }
    return res.json();
  },

  downloadPDF() {
    window.open(`${API_URL}/api/download-pdf`, '_blank');
  }
};
