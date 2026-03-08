import { useState } from 'react';
import { api } from './services/api';
import { calculateMealCalories } from './utils/nutritionCalculator';
import './App.css';

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

  const allergyOptions = ['Gluten', 'Dairy', 'Nuts', 'Eggs', 'Soy', 'Shellfish'];
  const preferenceOptions = ['Vegetarian', 'Veg + Non-Veg', 'Non-Veg', 'Vegan'];

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
      
      const hasBMI = data.lab_values?.bmi?.value;
      if (!hasBMI) {
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
      console.log('Generated diet plan:', data);
      setDietPlan(data);
      setActiveDay(0);
      setShowPatientForm(false);
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

  const dayKeys = dietPlan?.diet_plan
    ? Object.keys(dietPlan.diet_plan).filter(key => key.startsWith('day_')).sort()
    : [];
  const selectedDayIndex = dayKeys.length > 0 ? Math.min(activeDay, dayKeys.length - 1) : 0;
  const activeDayMeals = dayKeys.length > 0 ? dietPlan.diet_plan[dayKeys[selectedDayIndex]] : null;
  const macroTargets = dietPlan?.diet_plan?._macro_targets || { carbs_pct: 45, protein_pct: 25, fat_pct: 30 };
  const totalCalories = dietPlan?.diet_plan?._calories || 1800;
  const donutCircumference = 2 * Math.PI * 52;
  const carbsArc = Math.round((macroTargets.carbs_pct / 100) * donutCircumference);
  const proteinArc = Math.round((macroTargets.protein_pct / 100) * donutCircumference);
  const fatArc = Math.round((macroTargets.fat_pct / 100) * donutCircumference);

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
          <a className="nav-link active">Dashboard</a>
          <a className="nav-link">Analysis</a>
          <a className="nav-link">Diet Plans</a>
          <a className="nav-link">Reports</a>
          <a className="nav-link">History</a>
        </div>
      </nav>

      <div className="main-layout">
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

          {extracted && !showPatientForm && (
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
              {extracted.lab_values?.glucose && (
                <div className="data-row">
                  <span>Blood Sugar</span>
                  <span className={`val-${extracted.lab_values.glucose.status}`}>
                    {extracted.lab_values.glucose.value} mg/dL
                  </span>
                </div>
              )}
              {extracted.lab_values?.cholesterol_total && (
                <div className="data-row">
                  <span>Cholesterol</span>
                  <span className={`val-${extracted.lab_values.cholesterol_total.status}`}>
                    {extracted.lab_values.cholesterol_total.value} mg/dL
                  </span>
                </div>
              )}
              {extracted.lab_values?.bmi && (
                <div className="data-row">
                  <span>BMI</span>
                  <span className={`val-${extracted.lab_values.bmi.status}`}>
                    {extracted.lab_values.bmi.value}
                  </span>
                </div>
              )}
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
                {dietPlan.lab_values?.glucose && (
                  <div className={`metric-card ${dietPlan.lab_values.glucose.status === 'diabetes' || dietPlan.lab_values.glucose.status === 'prediabetes' ? 'border-alert' : 'border-ok'}`}>
                    <span className="metric-badge">{dietPlan.lab_values.glucose.status === 'normal' ? 'Normal' : 'High'}</span>
                    <div className="metric-val">{dietPlan.lab_values.glucose.value}</div>
                    <div className="metric-unit">mg/dL</div>
                    <div className="metric-label">Blood Sugar</div>
                  </div>
                )}
                {dietPlan.lab_values?.cholesterol_total && (
                  <div className={`metric-card ${dietPlan.lab_values.cholesterol_total.status === 'high' || dietPlan.lab_values.cholesterol_total.status === 'borderline' ? 'border-warn' : 'border-ok'}`}>
                    <span className="metric-badge">{dietPlan.lab_values.cholesterol_total.status === 'normal' ? 'Normal' : 'Elevated'}</span>
                    <div className="metric-val">{dietPlan.lab_values.cholesterol_total.value}</div>
                    <div className="metric-unit">mg/dL</div>
                    <div className="metric-label">Cholesterol</div>
                  </div>
                )}
                {dietPlan.lab_values?.bmi && (
                  <div className={`metric-card ${dietPlan.lab_values.bmi.status === 'normal' ? 'border-ok' : 'border-warn'}`}>
                    <span className="metric-badge">{dietPlan.lab_values.bmi.status === 'normal' ? 'Normal' : dietPlan.lab_values.bmi.status}</span>
                    <div className="metric-val">{dietPlan.lab_values.bmi.value}</div>
                    <div className="metric-unit"></div>
                    <div className="metric-label">BMI</div>
                  </div>
                )}
                {dietPlan.lab_values?.hba1c && (
                  <div className={`metric-card ${dietPlan.lab_values.hba1c.status === 'diabetes' || dietPlan.lab_values.hba1c.status === 'prediabetes' ? 'border-alert' : 'border-ok'}`}>
                    <span className="metric-badge">{dietPlan.lab_values.hba1c.status === 'normal' ? 'Normal' : 'High'}</span>
                    <div className="metric-val">{dietPlan.lab_values.hba1c.value}</div>
                    <div className="metric-unit">%</div>
                    <div className="metric-label">HbA1c</div>
                  </div>
                )}
              </div>

              <div className="glass-card diet-plan-card">
                <div className="plan-header">
                  <h2>{dietPlan.patient_info?.name || 'Patient'}</h2>
                  <div className="plan-meta">{dietPlan.diet_plan?._calories || 1800} kcal/day • {dietPlan.patient_info?.age || 'N/A'} years • BMI: {dietPlan.diet_plan?._patient_bmi || 'N/A'}</div>
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

              {dietPlan.doctor_notes && dietPlan.doctor_notes.length > 0 && (
                <div className="glass-card fade-up">
                  <h3>Doctor's Notes</h3>
                  <div className="notes-box">
                    <p>"{dietPlan.doctor_notes[0].substring(0, 200)}{dietPlan.doctor_notes[0].length > 200 ? '...' : ''}"</p>
                  </div>
                  <div className="notes-badge">
                    {dietPlan.doctor_notes[0].includes('[AI Generated]') ? '🤖 AI Generated' : '⚡ From Report'}
                  </div>
                </div>
              )}

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
    </>
  );
}

export default App;
