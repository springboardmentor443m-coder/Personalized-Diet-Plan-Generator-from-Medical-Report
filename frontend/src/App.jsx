import { useState } from 'react';
import { api } from './services/api';
import { calculateMealCalories } from './utils/nutritionCalculator';
import './App.css';

const LAB_DISPLAY_ORDER = [
  'glucose', 'hba1c', 'bmi', 'cholesterol_total', 'hdl', 'ldl', 'triglycerides',
  'bp_systolic', 'bp_diastolic', 'hemoglobin', 'pcv', 'rbc_count', 'wbc_count',
  'mcv', 'mch', 'mchc', 'esr', 'creatinine', 'uric_acid',
  'urea', 'sodium', 'potassium', 'chloride', 'vitamin_d', 'vitamin_b12',
  'tsh', 'platelets', 'weight', 'height'
];

const formatStatus = (status) => {
  if (!status) return 'Unknown';
  return status.replace(/_/g, ' ').replace(/\b\w/g, (char) => char.toUpperCase());
};

const getStatusTone = (status) => {
  const normalized = (status || '').toLowerCase();
  if (['normal', 'optimal'].includes(normalized)) return 'ok';
  if (['borderline', 'elevated', 'near_optimal', 'prediabetes', 'insufficient', 'calculated'].includes(normalized)) return 'warn';
  if (['high', 'low', 'diabetes', 'hypertension', 'obese', 'underweight', 'deficient', 'out_of_range'].includes(normalized)) return 'alert';
  return 'info';
};

const formatLabValue = (value) => {
  if (typeof value !== 'number') return value ?? 'N/A';
  return Number.isInteger(value) ? value : value.toFixed(1);
};

const getSortedLabEntries = (labValues = {}) => {
  return Object.entries(labValues).sort(([keyA], [keyB]) => {
    const indexA = LAB_DISPLAY_ORDER.indexOf(keyA);
    const indexB = LAB_DISPLAY_ORDER.indexOf(keyB);
    const safeA = indexA === -1 ? LAB_DISPLAY_ORDER.length : indexA;
    const safeB = indexB === -1 ? LAB_DISPLAY_ORDER.length : indexB;
    return safeA - safeB || keyA.localeCompare(keyB);
  });
};

const CHAT_SUGGESTIONS = [
  'Why is this diet plan suitable for my report?',
  'Which report values should I pay most attention to?',
  'What can I eat if I feel hungry between meals?',
  'How does this plan help with my abnormal lab values?'
];

function App() {
  const [file, setFile] = useState(null);
  const [extracting, setExtracting] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [extracted, setExtracted] = useState(null);
  const [dietPlan, setDietPlan] = useState(null);
  const [allergies, setAllergies] = useState([]);
  const [dietPreference, setDietPreference] = useState('Vegetarian');
  const [otherAllergyInput, setOtherAllergyInput] = useState('');
  const [activeDay, setActiveDay] = useState(0);
  const [showPatientForm, setShowPatientForm] = useState(false);
  const [patientData, setPatientData] = useState({ height: '', weight: '', activityLevel: 'moderate' });
  const [activeNav, setActiveNav] = useState('dashboard');
  const [chatMessages, setChatMessages] = useState([]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  const allergyOptions = ['Gluten', 'Dairy', 'Nuts', 'Eggs', 'Soy', 'Shellfish'];
  const preferenceOptions = ['Vegetarian', 'Veg + Non-Veg', 'Non-Veg', 'Vegan'];

  const handleNavChange = (sectionId) => {
    setActiveNav(sectionId);
    if (sectionId === 'assistant') return;
    window.requestAnimationFrame(() => {
      const section = document.getElementById(sectionId);
      if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    });
  };

  const handleFileSelect = async (e) => {
    const selectedFile = e.target.files[0];
    if (!selectedFile) return;
    
    setFile(selectedFile);
    setExtracting(true);
    setDietPlan(null);
    setShowPatientForm(false);
    
    try {
      const data = await api.extract(selectedFile);
      setExtracted(data);
      setChatMessages([]);

      const extractedHeight = data.lab_values?.height?.value || '';
      const extractedWeight = data.lab_values?.weight?.value || '';
      setPatientData((prev) => ({
        ...prev,
        height: extractedHeight ? String(extractedHeight) : '',
        weight: extractedWeight ? String(extractedWeight) : '',
        activityLevel: prev.activityLevel
      }));

      const hasBMI = data.lab_values?.bmi?.value;
      const hasHeight = data.lab_values?.height?.value;
      const hasWeight = data.lab_values?.weight?.value;
      if (!hasBMI || !hasHeight || !hasWeight) {
        setShowPatientForm(true);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setExtracting(false);
    }
  };

  const handleGenerate = async () => {
    if (showPatientForm && (!patientData.height || !patientData.weight)) {
      alert('Please enter height and weight');
      return;
    }
    
    setGenerating(true);
    try {
      const customAllergies = otherAllergyInput
        .split(',')
        .map(item => item.trim())
        .filter(Boolean);
      const mergedAllergies = [...new Set([...allergies, ...customAllergies])];

      const payload = {
        extracted,
        allergies: mergedAllergies,
        preferences: [dietPreference],
        ...(showPatientForm && {
          height: parseFloat(patientData.height),
          weight: parseFloat(patientData.weight),
          activityLevel: patientData.activityLevel
        })
      };
      
      const data = await api.generate(payload.extracted, payload.allergies, payload.preferences, payload.height, payload.weight, payload.activityLevel);
      setDietPlan(data);
      setActiveDay(0);
      setShowPatientForm(false);
      setChatMessages([]);
    } catch (err) {
      console.error('Generation error:', err);
      alert('Failed to generate diet plan: ' + err.message);
    } finally {
      setGenerating(false);
    }
  };

  const toggleAllergy = (item) => {
    setAllergies(prev => 
      prev.includes(item) ? prev.filter(a => a !== item) : [...prev, item]
    );
  };

  const togglePreference = (item) => {
    setDietPreference(item);
  };

  const sendChatMessage = async (question) => {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || !extracted || chatLoading) return;

    const nextMessages = [...chatMessages, { role: 'user', content: trimmedQuestion }];
    setChatMessages(nextMessages);
    setChatInput('');
    setChatLoading(true);

    try {
      const history = nextMessages
        .filter((message) => ['user', 'assistant'].includes(message.role))
        .map((message) => ({ role: message.role, content: message.content }));
      const response = await api.chat(trimmedQuestion, extracted, dietPlan, history);
      setChatMessages([
        ...nextMessages,
        { role: 'assistant', content: response.answer, source: response.source }
      ]);
    } catch (err) {
      console.error('Chat error:', err);
      setChatMessages([
        ...nextMessages,
        {
          role: 'assistant',
          content: err.message || 'The assistant could not answer that right now.',
          source: 'fallback'
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const handleSuggestionClick = (suggestion) => {
    setChatInput(suggestion);
  };

  const handleChatKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (chatInput.trim() && !chatLoading && extracted) {
        sendChatMessage(chatInput);
      }
    }
  };

  const dayKeys = dietPlan?.diet_plan
    ? Object.keys(dietPlan.diet_plan).filter(key => key.startsWith('day_')).sort()
    : [];
  const selectedDayIndex = dayKeys.length > 0 ? Math.min(activeDay, dayKeys.length - 1) : 0;
  const activeDayMeals = dayKeys.length > 0 ? dietPlan.diet_plan[dayKeys[selectedDayIndex]] : null;
  const macroTargets = dietPlan?.diet_plan?._macro_targets || { carbs_pct: 45, protein_pct: 25, fat_pct: 30 };
  const totalCalories = dietPlan?.diet_plan?._calories || 1800;
  const extractedLabEntries = getSortedLabEntries(extracted?.lab_values);
  const generatedLabEntries = getSortedLabEntries(dietPlan?.lab_values);
  const planJustification = dietPlan?.diet_plan?.plan_justification;
  // Use the strongest BMI source after generation.
  const resolvedPatientBMI = dietPlan?.diet_plan?._patient_bmi
    ?? dietPlan?.lab_values?.bmi?.value
    ?? extracted?.lab_values?.bmi?.value
    ?? 'N/A';
  const donutCircumference = 2 * Math.PI * 52;
  const carbsArc = Math.round((macroTargets.carbs_pct / 100) * donutCircumference);
  const proteinArc = Math.round((macroTargets.protein_pct / 100) * donutCircumference);
  const fatArc = Math.round((macroTargets.fat_pct / 100) * donutCircumference);
  const assistantPanel = (
    <div className="assistant-page" id="assistant">
      <div className="assistant-grid">
        {dietPlan && (
          <div className="glass-card fade-up assistant-plan-preview">
            <div className="assistant-plan-header">
              <h3>Current Diet Plan</h3>
              <span>{totalCalories} kcal/day • BMI {resolvedPatientBMI}</span>
            </div>

            <div className="day-tabs assistant-day-tabs">
              {dayKeys.map((day, idx) => (
                <button
                  key={day}
                  className={`day-tab ${activeDay === idx ? 'active' : ''}`}
                  onClick={() => setActiveDay(idx)}
                >
                  Day {idx + 1}
                </button>
              ))}
            </div>

            <div className="meals-grid assistant-meals-grid">
              {activeDayMeals && Object.entries(activeDayMeals).map(([type, meal]) => (
                <div key={type} className="meal-tile">
                  <div className="meal-header">
                    <span>{type.charAt(0).toUpperCase() + type.slice(1)}</span>
                    <span className="meal-kcal">~{calculateMealCalories(meal?.macros?.protein || 0, meal?.macros?.carbs || 0, meal?.macros?.fat || 0)} kcal</span>
                  </div>
                  <div className="meal-name">{meal.meal}</div>
                  <div className="meal-reason">{meal.reason}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        <div className="glass-card fade-up assistant-chat-card">
          <div className="chat-header-row">
            <h3>Ask the Assistant</h3>
          </div>

          <div className="suggestion-grid">
            {CHAT_SUGGESTIONS.map((suggestion) => (
              <button
                key={suggestion}
                className="suggestion-chip"
                onClick={() => handleSuggestionClick(suggestion)}
                disabled={!extracted || chatLoading}
              >
                {suggestion}
              </button>
            ))}
          </div>

          <div className="chat-thread">
            {chatMessages.map((message, index) => (
              <div key={`${message.role}-${index}`} className={`chat-bubble chat-${message.role}`}>
                <div className="chat-role">{message.role === 'assistant' ? 'AI Assistant' : 'You'}</div>
                <div>{message.content}</div>
              </div>
            ))}
            {chatLoading && (
              <div className="chat-bubble chat-assistant">
                <div className="chat-role">AI Assistant</div>
                <div>Thinking through the report and diet plan...</div>
              </div>
            )}
          </div>

          <div className="chat-composer">
            <textarea
              value={chatInput}
              onChange={(e) => setChatInput(e.target.value)}
              onKeyDown={handleChatKeyDown}
              placeholder={extracted ? 'Ask a question about your report or diet plan' : 'Upload a report to start chatting'}
              rows="3"
              disabled={!extracted || chatLoading}
            />
            <button onClick={() => sendChatMessage(chatInput)} disabled={!extracted || !chatInput.trim() || chatLoading}>
              {chatLoading ? 'Sending...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <div className="blob blob-1"></div>
      <div className="blob blob-2"></div>
      <div className="blob blob-3"></div>

      <nav className="navbar">
        <div className="nav-left">
          <div className="logo-box">🍃</div>
          <div>
            <div className="app-name">AI-NutriCare</div>
            <div className="app-tagline">Medical Diet Intelligence</div>
          </div>
        </div>
        <div className="nav-center">
          <button className={`nav-link ${activeNav === 'dashboard' ? 'active' : ''}`} onClick={() => handleNavChange('dashboard')}>Dashboard</button>
          <button className={`nav-link ${activeNav === 'diet-plan' ? 'active' : ''}`} onClick={() => handleNavChange('diet-plan')}>Diet Plan</button>
          <button className={`nav-link ${activeNav === 'assistant' ? 'active' : ''}`} onClick={() => handleNavChange('assistant')}>Assistant</button>
        </div>
      </nav>

      {activeNav === 'assistant' ? assistantPanel : (
      <div className="main-layout" id="dashboard">
        <aside className="left-col">
          <div className="glass-card fade-up">
            <h3>Medical Report Upload</h3>
            <label className="upload-zone">
              <input type="file" accept=".pdf,.png,.jpg,.txt" onChange={handleFileSelect} hidden />
              <div className="upload-icon">📄</div>
              <p>{file ? file.name : 'Drop file or click to upload'}</p>
              <span className="upload-hint">PDF, PNG, JPG, TXT</span>
            </label>
            {extracting && <div className="extracting">Extracting patient data...</div>}
          </div>

          {extracted && showPatientForm && (
            <div className="glass-card fade-up patient-form-card">
              <h3>Complete Your Profile</h3>
              <p className="form-subtitle">We need height and weight to calculate your BMI and personalized calorie needs</p>
              
              <div className="form-group">
                <label>Height (cm)</label>
                <input
                  type="number"
                  value={patientData.height}
                  onChange={(e) => setPatientData({...patientData, height: e.target.value})}
                  placeholder="170"
                  min="100"
                  max="220"
                />
              </div>

              <div className="form-group">
                <label>Weight (kg)</label>
                <input
                  type="number"
                  value={patientData.weight}
                  onChange={(e) => setPatientData({...patientData, weight: e.target.value})}
                  placeholder="70"
                  min="30"
                  max="200"
                />
              </div>

              <div className="form-group">
                <label>Activity Level</label>
                <select
                  value={patientData.activityLevel}
                  onChange={(e) => setPatientData({...patientData, activityLevel: e.target.value})}
                >
                  <option value="sedentary">Sedentary (little/no exercise)</option>
                  <option value="light">Light (1-3 days/week)</option>
                  <option value="moderate">Moderate (3-5 days/week)</option>
                  <option value="active">Active (6-7 days/week)</option>
                </select>
              </div>
            </div>
          )}

          {extracted && (
            <div className="glass-card fade-up patient-card">
              <div className="card-header-row">
                <h3>Extracted Patient Data</h3>
                <span className="badge-auto">✦ AUTO-PARSED</span>
              </div>
              {extracted.patient_info?.name && (
                <div className="data-row">
                  <span>Name</span>
                  <span className="val-info">{extracted.patient_info.name}</span>
                </div>
              )}
              {extracted.patient_info?.age && (
                <div className="data-row">
                  <span>Age / Gender</span>
                  <span className="val-info">{extracted.patient_info.age} / {extracted.patient_info.gender || 'N/A'}</span>
                </div>
              )}
              {extractedLabEntries.map(([key, lab]) => (
                <div className="data-row" key={key}>
                  <span>{lab.label || key.replace(/_/g, ' ')}</span>
                  <span className={`val-${getStatusTone(lab.status)}`}>
                    {formatLabValue(lab.value)}{lab.unit ? ` ${lab.unit}` : ''} · {formatStatus(lab.status)}
                  </span>
                </div>
              ))}
            </div>
          )}

          <div className="glass-card fade-up">
            <h3>Preferences & Restrictions</h3>
            <div className="pref-section">
              <label>Allergies</label>
              <div className="pill-group">
                {allergyOptions.map(item => (
                  <button
                    key={item}
                    className={`pill ${allergies.includes(item) ? 'pill-rose' : ''}`}
                    onClick={() => toggleAllergy(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
              <input
                type="text"
                value={otherAllergyInput}
                onChange={(e) => setOtherAllergyInput(e.target.value)}
                placeholder="Other allergies (comma separated)"
                style={{ marginTop: '10px', width: '100%' }}
              />
            </div>
            <div className="pref-section">
              <label>Dietary Preference (choose one)</label>
              <div className="pill-group">
                {preferenceOptions.map(item => (
                  <button
                    key={item}
                    className={`pill ${dietPreference === item ? 'pill-cyan' : ''}`}
                    onClick={() => togglePreference(item)}
                  >
                    {item}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <button 
            className="btn-generate" 
            disabled={!extracted || generating}
            onClick={handleGenerate}
          >
            {generating ? 'Generating...' : '✦ Generate Diet Plan'}
          </button>
        </aside>

        <main className="center-col">
          {dietPlan ? (
            <>
              <div className="metrics-strip">
                {generatedLabEntries.map(([key, lab]) => (
                  <div key={key} className={`metric-card border-${getStatusTone(lab.status)}`}>
                    <span className={`metric-badge badge-${getStatusTone(lab.status)}`}>{formatStatus(lab.status)}</span>
                    <div className="metric-val">{formatLabValue(lab.value)}</div>
                    <div className="metric-unit">{lab.unit || ''}</div>
                    <div className="metric-label">{lab.label || key.replace(/_/g, ' ')}</div>
                  </div>
                ))}
              </div>

              <div className="glass-card diet-plan-card" id="diet-plan">
                <div className="plan-header">
                  <h2>{dietPlan.patient_info?.name || 'Patient'}</h2>
                  <div className="plan-meta">{dietPlan.diet_plan?._calories || 1800} kcal/day • {dietPlan.patient_info?.age || 'N/A'} years • BMI: {resolvedPatientBMI}</div>
                </div>
                <div className="condition-chips">
                  {extracted.ml_predictions?.diabetes?.detected && (
                    <span className="chip chip-rose">Diabetes</span>
                  )}
                  {extracted.ml_predictions?.high_cholesterol?.detected && (
                    <span className="chip chip-gold">High Cholesterol</span>
                  )}
                  <span className="chip chip-cyan">AI Generated</span>
                </div>

                {planJustification && (
                  <div className="plan-justification">
                    <h3>Why This Plan Fits</h3>
                    <p>{planJustification.summary}</p>
                    <div className="justification-list">
                      {Array.isArray(planJustification.condition_support) && planJustification.condition_support.map((point, index) => (
                        <div key={index} className="justification-item">{point}</div>
                      ))}
                      {planJustification.preference_support && (
                        <div className="justification-item">{planJustification.preference_support}</div>
                      )}
                      {planJustification.allergy_support && (
                        <div className="justification-item">{planJustification.allergy_support}</div>
                      )}
                    </div>
                  </div>
                )}

                <div className="day-tabs">
                  {dayKeys.map((day, idx) => (
                    <button
                      key={day}
                      className={`day-tab ${activeDay === idx ? 'active' : ''}`}
                      onClick={() => setActiveDay(idx)}
                    >
                      Day {idx + 1}
                    </button>
                  ))}
                </div>

                <div className="meals-grid">
                  {activeDayMeals && (
                    <>
                      {Object.entries(activeDayMeals).map(([type, meal]) => (
                        <div key={type} className="meal-tile">
                          <div className="meal-header">
                            <span>{type === 'breakfast' ? '🌤' : type === 'lunch' ? '☀️' : type === 'snack' ? '🍏' : '🌙'} {type.charAt(0).toUpperCase() + type.slice(1)}</span>
                            <span className="meal-kcal">~{calculateMealCalories(meal?.macros?.protein || 0, meal?.macros?.carbs || 0, meal?.macros?.fat || 0)} kcal</span>
                          </div>
                          <div className="meal-name">{meal.meal}</div>
                          <div className="meal-reason">{meal.reason}</div>
                          <div className="macro-pills">
                            <span>P: {meal?.macros?.protein || 0}g</span>
                            <span>C: {meal?.macros?.carbs || 0}g</span>
                            <span>F: {meal?.macros?.fat || 0}g</span>
                          </div>
                        </div>
                      ))}
                    </>
                  )}
                </div>

                <div className="export-bar">
                  <button onClick={() => api.downloadPDF()}>⬇ Export PDF</button>
                  <button>{'{ }'} Export JSON</button>
                  <button>📤 Share</button>
                  <button onClick={() => setDietPlan(null)}>✕ Clear</button>
                </div>
              </div>
            </>
          ) : (
            <div className="glass-card empty-state">
              <h2>Your plan appears here</h2>
              <p>Upload a medical report and generate your personalized diet plan</p>
            </div>
          )}
        </main>

        <aside className="right-col">
          {dietPlan && (
            <>
              <div className="glass-card fade-up">
                <h3>Macro Breakdown</h3>
                <svg className="donut-chart" viewBox="0 0 120 120">
                  <circle cx="60" cy="60" r="52" fill="none" stroke="var(--cyan)" strokeWidth="20" strokeDasharray={`${carbsArc} ${donutCircumference}`} transform="rotate(-90 60 60)" />
                  <circle cx="60" cy="60" r="52" fill="none" stroke="var(--teal)" strokeWidth="20" strokeDasharray={`${proteinArc} ${donutCircumference}`} strokeDashoffset={`-${carbsArc}`} transform="rotate(-90 60 60)" />
                  <circle cx="60" cy="60" r="52" fill="none" stroke="var(--gold)" strokeWidth="20" strokeDasharray={`${fatArc} ${donutCircumference}`} strokeDashoffset={`-${carbsArc + proteinArc}`} transform="rotate(-90 60 60)" />
                  <text x="60" y="55" textAnchor="middle" fill="var(--text-2)" fontSize="10">kcal/day</text>
                  <text x="60" y="70" textAnchor="middle" fill="var(--text-1)" fontSize="16" fontWeight="600">{totalCalories}</text>
                </svg>
                <div className="donut-legend">
                  <div><span className="dot dot-cyan"></span> Carbs {macroTargets.carbs_pct}%</div>
                  <div><span className="dot dot-teal"></span> Protein {macroTargets.protein_pct}%</div>
                  <div><span className="dot dot-gold"></span> Fat {macroTargets.fat_pct}%</div>
                </div>
              </div>

              <div className="glass-card fade-up">
                <h3>Daily Targets</h3>
                <div className="target-row">
                  <span>Calories</span>
                  <span>{totalCalories} / {totalCalories} kcal</span>
                  <div className="target-bar"><div className="target-fill" style={{width: '100%', background: 'var(--cyan)'}}></div></div>
                </div>
                <div className="target-row">
                  <span>Water</span>
                  <span>2.5 / 3.0 L</span>
                  <div className="target-bar"><div className="target-fill" style={{width: '83%', background: 'var(--teal)'}}></div></div>
                </div>
                <div className="target-row">
                  <span>Fiber</span>
                  <span>28 / 30 g</span>
                  <div className="target-bar"><div className="target-fill" style={{width: '93%', background: 'var(--gold)'}}></div></div>
                </div>
                <div className="target-row">
                  <span>Sodium</span>
                  <span>1800 / 2300 mg</span>
                  <div className="target-bar"><div className="target-fill" style={{width: '78%', background: 'var(--violet)'}}></div></div>
                </div>
              </div>
            </>
          )}
        </aside>
      </div>
      )}
    </>
  );
}

export default App;
