import { useState } from 'react'

const DIET_TYPES = [
  { value: 'non_veg',    label: '🍗 Non-Vegetarian' },
  { value: 'veg',        label: '🥬 Vegetarian' },
  { value: 'vegan',      label: '🌱 Vegan' },
  { value: 'eggetarian', label: '🥚 Eggetarian' },
]
const MEAL_FREQ = [
  { value: '5_small', label: '5 small meals/day' },
  { value: '3_meals', label: '3 meals/day' },
  { value: '2_meals', label: '2 meals/day' },
]
const CUISINES = ['', 'North Indian', 'South Indian', 'Mediterranean', 'East Asian', 'Middle Eastern', 'Continental/Western', 'Latin American']
const BUDGETS  = [
  { value: 'no_preference',  label: '💰 No Preference' },
  { value: 'budget_friendly', label: '🪙 Budget-Friendly' },
  { value: 'moderate',        label: '💵 Moderate' },
  { value: 'premium',         label: '💎 Premium' },
]

function BmiCalculator({ onBmiChange }) {
  const [units, setUnits] = useState('metric')
  const [h, setH] = useState(170)
  const [w, setW] = useState(70)
  const [ft, setFt] = useState(5)
  const [inches, setInches] = useState(7)
  const [lbs, setLbs] = useState(154)
  const [saved, setSaved] = useState(null)

  const hCm = units === 'metric' ? h : Math.round((ft * 12 + inches) * 2.54 * 10) / 10
  const wKg = units === 'metric' ? w : Math.round(lbs * 0.453592 * 10) / 10
  const bmiVal = Math.round(wKg / Math.pow(hCm / 100, 2) * 100) / 100

  const { label, color } =
    bmiVal < 18.5 ? { label: 'Underweight', color: '#eab308' }
    : bmiVal < 25  ? { label: 'Normal', color: '#22c55e' }
    : bmiVal < 30  ? { label: 'Overweight', color: '#f97316' }
    :                { label: 'Obese', color: '#ef4444' }

  function save() {
    setSaved(bmiVal)
    onBmiChange && onBmiChange({
      bmi_value: bmiVal,
      classification: label,
      category: label,
      height_cm: hCm,
      weight_kg: wKg,
    })
  }

  return (
    <div className="sb-section">
      <div className="sb-section-title">⚖️ BMI Calculator</div>
      <details className="sb-collapse">
        <summary>🏅 Calculate Your BMI</summary>

        <div className="sb-collapse-body">
          <div className="sb-radio-row">
            {['metric', 'imperial'].map(u => (
              <label key={u} className="sb-radio">
                <input type="radio" checked={units === u} onChange={() => setUnits(u)} /> {u.charAt(0).toUpperCase() + u.slice(1)}
              </label>
            ))}
          </div>

          {units === 'metric' ? (
            <>
              <label className="sb-label">Height (cm)</label>
              <input className="sb-input" type="number" value={h} min={50} max={250} onChange={e => setH(+e.target.value)} />
              <label className="sb-label">Weight (kg)</label>
              <input className="sb-input" type="number" value={w} min={10} max={300} onChange={e => setW(+e.target.value)} />
            </>
          ) : (
            <>
              <div className="sb-row-2">
                <div>
                  <label className="sb-label">Feet</label>
                  <input className="sb-input" type="number" value={ft} min={1} max={8} onChange={e => setFt(+e.target.value)} />
                </div>
                <div>
                  <label className="sb-label">Inches</label>
                  <input className="sb-input" type="number" value={inches} min={0} max={11} onChange={e => setInches(+e.target.value)} />
                </div>
              </div>
              <label className="sb-label">Weight (lbs)</label>
              <input className="sb-input" type="number" value={lbs} min={20} max={660} onChange={e => setLbs(+e.target.value)} />
            </>
          )}

          <div className="bmi-live">
            <span className="bmi-val">{bmiVal}</span>
            <span className="bmi-lbl" style={{ color }}>{label}</span>
          </div>

          <button className="btn btn-primary sb-btn" onClick={save}>💾 Save BMI</button>
          {saved && <div className="sb-saved">✅ Saved BMI: {saved}</div>}
        </div>
      </details>
    </div>
  )
}

function DietPreferences({ prefs, onChange }) {
  const [local, setLocal] = useState({
    diet_type: 'non_veg', meal_frequency: '5_small',
    cuisine: '', calorie_target: 0, allergies: '', budget_level: 'no_preference',
  })

  function set(k, v) { setLocal(p => ({ ...p, [k]: v })) }

  function save() {
    const p = {
      diet_type: local.diet_type,
      meal_frequency: local.meal_frequency,
    }
    if (local.cuisine) p.cuisine = local.cuisine
    if (local.calorie_target > 0) p.calorie_target = local.calorie_target
    if (local.allergies.trim()) p.allergies = local.allergies.split(',').map(s => s.trim()).filter(Boolean)
    if (local.budget_level !== 'no_preference') p.budget_level = local.budget_level
    onChange(p)
  }

  return (
    <div className="sb-section">
      <div className="sb-section-title">🥗 Diet Preferences</div>
      <details className="sb-collapse">
        <summary>🧾 Customize Diet Plan</summary>

        <div className="sb-collapse-body">
          <label className="sb-label">Diet Type</label>
          <select className="sb-input" value={local.diet_type} onChange={e => set('diet_type', e.target.value)}>
            {DIET_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>

          <label className="sb-label">Meal Frequency</label>
          <select className="sb-input" value={local.meal_frequency} onChange={e => set('meal_frequency', e.target.value)}>
            {MEAL_FREQ.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
          </select>

          <label className="sb-label">Regional Cuisine</label>
          <select className="sb-input" value={local.cuisine} onChange={e => set('cuisine', e.target.value)}>
            {CUISINES.map(c => <option key={c} value={c}>{c || 'No preference'}</option>)}
          </select>

          <label className="sb-label">Calorie Target (0 = auto)</label>
          <input className="sb-input" type="number" min={0} max={5000} step={100} value={local.calorie_target} onChange={e => set('calorie_target', +e.target.value)} />

          <label className="sb-label">Allergies / Exclusions</label>
          <input className="sb-input" type="text" placeholder="e.g. peanuts, gluten" value={local.allergies} onChange={e => set('allergies', e.target.value)} />

          <label className="sb-label">Budget Level</label>
          <select className="sb-input" value={local.budget_level} onChange={e => set('budget_level', e.target.value)}>
            {BUDGETS.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
          </select>

          <button className="btn btn-primary sb-btn" onClick={save}>💾 Save Preferences</button>
          {Object.keys(prefs).length > 0 && <div className="sb-saved">✅ Preferences saved</div>}
        </div>
      </details>
    </div>
  )
}

export default function Sidebar({ prefs, onPrefsChange, onBmiChange }) {
  return (
    <aside className="sidebar">
      <div className="sb-brand">
        <div>
          <div className="sb-title">AI Diet Planner</div>
          <div className="sb-tagline">Upload reports, get a personalized diet plan powered by AI.</div>
        </div>
      </div>

      <div className="sb-section">
        <div className="sb-section-title">Supported Formats</div>
        <div className="sb-formats">PDF, JPG, JPEG, PNG — up to 20 MB each</div>
      </div>

      <BmiCalculator onBmiChange={onBmiChange} />
      <DietPreferences prefs={prefs} onChange={onPrefsChange} />

      <div className="sb-footer">v0.4.0 · Powered by Groq AI</div>
    </aside>
  )
}
