import { useEffect, useState } from 'react'

const MEAL_ICONS = {
  breakfast: '🌅', 'mid-morning snack': '🍎', 'morning snack': '🍎',
  lunch: '☀️', 'afternoon snack': '🥜', 'evening snack': '🥜',
  snack: '🥜', dinner: '🌙', 'bedtime snack': '🌜',
}

const DIET_TYPES = [
  { value: 'non_veg', label: '🍗 Non-Vegetarian' },
  { value: 'veg', label: '🥬 Vegetarian' },
  { value: 'vegan', label: '🌱 Vegan' },
  { value: 'eggetarian', label: '🥚 Eggetarian' },
]

const MEAL_FREQ = [
  { value: '5_small', label: '5 small meals/day' },
  { value: '3_meals', label: '3 meals/day' },
  { value: '2_meals', label: '2 meals/day' },
]

const CUISINES = [
  '',
  'North Indian',
  'South Indian',
  'Mediterranean',
  'East Asian',
  'Middle Eastern',
  'Continental/Western',
  'Latin American',
]

const BUDGETS = [
  { value: 'no_preference', label: '💰 No Preference' },
  { value: 'budget_friendly', label: '🪙 Budget-Friendly' },
  { value: 'moderate', label: '💵 Moderate' },
  { value: 'premium', label: '💎 Premium' },
]

const DEFAULT_FILTERS = {
  diet_type: 'non_veg',
  meal_frequency: '5_small',
  cuisine: '',
  calorie_target: 0,
  allergies: '',
  budget_level: 'no_preference',
}

function toArray(value) {
  if (Array.isArray(value)) return value
  if (value === null || value === undefined || value === '') return []
  return [value]
}

function toText(value) {
  if (value === null || value === undefined || value === '') return ''
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value)
  }
  if (typeof value === 'object') {
    const preferred = value.message ?? value.text ?? value.name ?? value.item ?? value.value
    if (preferred !== null && preferred !== undefined) return String(preferred)
    try {
      return JSON.stringify(value)
    } catch {
      return ''
    }
  }
  return String(value)
}

function asStringList(value) {
  return toArray(value).map(toText).filter(Boolean)
}

function formatNutrientItem(item) {
  if (typeof item === 'string') return item
  if (!item || typeof item !== 'object') return toText(item)

  const nutrient = toText(item.nutrient ?? item.name)
  const reason = toText(item.reason)
  const maxDaily = toText(item.max_daily)
  const sources = asStringList(item.food_sources)

  const parts = []
  if (nutrient) parts.push(nutrient)
  if (reason) parts.push(reason)
  if (maxDaily) parts.push(`Max daily: ${maxDaily}`)
  if (sources.length) parts.push(`Sources: ${sources.join(', ')}`)

  return parts.join(' - ') || toText(item)
}

function formatFoodItem(item) {
  if (typeof item === 'string') return item
  if (!item || typeof item !== 'object') return toText(item)

  const food = toText(item.food_or_category ?? item.food ?? item.name)
  const reason = toText(item.reason)
  const frequency = toText(item.frequency)
  const severity = toText(item.severity)

  const parts = []
  if (food) parts.push(food)
  if (reason) parts.push(reason)
  if (frequency) parts.push(`Frequency: ${frequency}`)
  if (severity) parts.push(`Level: ${severity}`)

  return parts.join(' - ') || toText(item)
}

function normalizeWarnings(value) {
  return toArray(value)
    .map((w) => {
      if (w && typeof w === 'object') {
        const msg = toText(w.message ?? w.warning ?? w.note ?? w.details ?? w.value)
        const sev = w.severity ? String(w.severity).toUpperCase() : ''
        if (sev && msg) return `[${sev}] ${msg}`
        return msg || toText(w)
      }
      return toText(w)
    })
    .filter(Boolean)
}

function MealCard({ meal }) {
  const name = meal.meal_name || meal.name || meal.meal_type || 'Meal'
  const icon = MEAL_ICONS[name.toLowerCase().replace(/_/g, ' ')] || '🍽️'
  const display = name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  const rawItems = meal.items ?? meal.foods ?? meal.food_items ?? []
  const items = Array.isArray(rawItems)
    ? rawItems
    : rawItems
      ? [rawItems]
      : []
  const legacyMeal = meal.meal
  const cals = meal.calories_approx || meal.calories || meal.estimated_calories
  const macros = ['protein_g', 'carbs_g', 'fat_g']
    .filter(k => meal[k] != null)
    .map(k => `${k[0].toUpperCase()}: ${meal[k]}g`)
    .join(' | ')

  return (
    <div className="meal-card">
      <div className="meal-header">
        <span className="meal-icon">{icon}</span>
        <span className="meal-name">{display}</span>
        {meal.time && <span className="meal-meta">({meal.time})</span>}
        {cals && <span className="meal-meta">~{cals} kcal</span>}
        {macros && <span className="meal-meta">{macros}</span>}
      </div>
      <ul className="meal-items">
        {items.map((item, i) => {
          if (typeof item === 'string') return <li key={i}>{item}</li>
          if (item === null || item === undefined) return null
          if (typeof item !== 'object') return <li key={i}>{String(item)}</li>
          const food = item.food || item.name || JSON.stringify(item)
          const portion = item.portion || item.quantity || item.amount || ''
          const prep = item.preparation || ''
          return <li key={i}><strong>{food}</strong>{portion && ` — ${portion}`}{prep && ` (${prep})`}</li>
        })}
        {!items.length && legacyMeal && <li>{toText(legacyMeal)}</li>}
      </ul>
      {meal.notes && <div className="meal-note">💡 {meal.notes}</div>}
    </div>
  )
}

function DayPanel({ dayData }) {
  let meals = []
  if (dayData && typeof dayData === 'object' && !Array.isArray(dayData)) {
    meals = dayData.meals || Object.entries(dayData)
      .filter(([k]) => k !== 'daily_totals')
      .map(([k, v]) => ({ meal_name: k, ...(typeof v === 'object' ? v : { items: [v] }) }))
  } else if (Array.isArray(dayData)) {
    meals = dayData
  }
  const totals = dayData && typeof dayData === 'object' && !Array.isArray(dayData) ? dayData.daily_totals : null

  return (
    <div className="day-panel">
      {meals.map((m, i) => <MealCard key={i} meal={m} />)}
      {totals && typeof totals === 'object' && (
        <div className="day-totals">
          📊 Day totals: {['calories', 'protein_g', 'carbs_g', 'fat_g']
            .filter(k => totals[k] != null)
            .map(k => `${k.replace('_g', '').replace(/\b\w/g, c => c.toUpperCase())}: ${totals[k]}`)
            .join(' · ')}
        </div>
      )}
    </div>
  )
}

function WeeklyTabs({ weekly }) {
  const days = Object.keys(weekly || {})
  const [activeDay, setActiveDay] = useState(days[0] || '')

  useEffect(() => {
    if (!days.length) return
    if (!activeDay || !weekly[activeDay]) {
      setActiveDay(days[0])
    }
  }, [days, activeDay, weekly])

  if (!days.length) {
    return <div className="small-subtext">No daily meal breakdown found.</div>
  }

  return (
    <div>
      <div className="day-tabs">
        {days.map(d => (
          <button key={d} className={`day-tab${activeDay === d ? ' active' : ''}`} onClick={() => setActiveDay(d)}>
            {String(d).replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </button>
        ))}
      </div>
      <DayPanel dayData={weekly[activeDay]} />
    </div>
  )
}

function renderDietContent(plan) {
  if (!plan) return null
  if (typeof plan === 'string') return <pre className="plan-text">{plan}</pre>

  const weekly =
    plan.weekly_meal_plan ||
    plan.weekly_plan ||
    plan.weekly ||
    plan.days ||
    plan.meal_plan

  if (weekly && typeof weekly === 'object' && !Array.isArray(weekly)) {
    return <WeeklyTabs weekly={weekly} />
  }
  if (Array.isArray(plan)) {
    return plan.map((m, i) => <MealCard key={i} meal={m} />)
  }
  return <pre className="plan-text">{JSON.stringify(plan, null, 2)}</pre>
}

function Percentage({ value }) {
  if (value === null || value === undefined || value === '') return '--'
  const str = String(value)
  return str.includes('%') ? str : `${str}%`
}

export default function DietTab({ data, onReload, prefs = {} }) {
  const [localPrefs, setLocalPrefs] = useState(DEFAULT_FILTERS)

  useEffect(() => {
    const next = { ...DEFAULT_FILTERS }
    if (prefs && typeof prefs === 'object') {
      if (prefs.diet_type) next.diet_type = prefs.diet_type
      if (prefs.meal_frequency) next.meal_frequency = prefs.meal_frequency
      if (prefs.cuisine) next.cuisine = prefs.cuisine
      if (prefs.budget_level) next.budget_level = prefs.budget_level

      const cals = Number(prefs.calorie_target)
      if (!Number.isNaN(cals) && cals > 0) next.calorie_target = cals

      if (Array.isArray(prefs.allergies)) {
        next.allergies = prefs.allergies.join(', ')
      } else if (typeof prefs.allergies === 'string') {
        next.allergies = prefs.allergies
      }
    }
    setLocalPrefs(next)
  }, [prefs])

  function setFilter(key, value) {
    setLocalPrefs((prev) => ({ ...prev, [key]: value }))
  }

  function buildFilterPayload() {
    const payload = {
      diet_type: localPrefs.diet_type,
      meal_frequency: localPrefs.meal_frequency,
    }

    if (localPrefs.cuisine) payload.cuisine = localPrefs.cuisine
    if (Number(localPrefs.calorie_target) > 0) payload.calorie_target = Number(localPrefs.calorie_target)

    const allergies = String(localPrefs.allergies || '')
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean)
    if (allergies.length) payload.allergies = allergies

    if (localPrefs.budget_level && localPrefs.budget_level !== 'no_preference') {
      payload.budget_level = localPrefs.budget_level
    }

    return payload
  }

  function applyFiltersAndReload() {
    if (!onReload) return
    onReload(buildFilterPayload())
  }

  if (!data) return (
    <div className="empty-state">
      <h3>🥗 No Diet Plan Yet</h3>
      <p>Upload reports and click Analyze & Generate Diet Plan.</p>
    </div>
  )

  const generationError = toText(data?.diet_generation_metadata?.error)
  if (!data?.diet_plan && generationError) {
    return (
      <div className="empty-state">
        <h3>⚠️ Unable To Generate Diet Plan</h3>
        <p>{generationError}</p>
        <p className="small-subtext">Try again later or switch to a smaller/fallback model in backend settings.</p>
        <div className="action-row" style={{ marginTop: 12 }}>
          <button className="btn btn-primary" onClick={() => onReload && onReload(buildFilterPayload())}>
            Retry With Current Filters
          </button>
        </div>
      </div>
    )
  }

  const plan = data.diet_plan || {}
  const guidelines = plan?.dietary_guidelines || plan?.guidelines || {}
  const macros = guidelines?.macronutrient_split || plan?.macronutrient_split || {}
  const nutrientsToIncrease = toArray(guidelines?.key_nutrients_to_increase || plan?.key_nutrients_to_increase)
    .map(formatNutrientItem)
    .filter(Boolean)
  const nutrientsToLimit = toArray(guidelines?.key_nutrients_to_limit || plan?.key_nutrients_to_limit)
    .map(formatNutrientItem)
    .filter(Boolean)
  const foodsToEmphasize = toArray(guidelines?.foods_to_emphasize || plan?.foods_to_emphasize)
    .map(formatFoodItem)
    .filter(Boolean)
  const foodsToAvoid = toArray(guidelines?.foods_to_avoid || plan?.foods_to_avoid)
    .map(formatFoodItem)
    .filter(Boolean)

  const safety = data?.safety_checks || plan?.safety_assessment || {}
  const warnings = normalizeWarnings(safety?.safety_warnings || safety?.warnings)

  const confidence = plan?.confidence_assessment
  const disclaimer = toText(plan?.disclaimer)
  const qualityNotes = asStringList(confidence?.data_quality_notes)
  const limitations = asStringList(confidence?.limitations)

  // Extract caloric target (can be object with range_kcal or string)
  const caloricTargetObj = 
    guidelines?.caloric_target ||
    guidelines?.daily_calorie_target ||
    plan?.caloric_target ||
    plan?.daily_calorie_target ||
    plan?.calorie_target
  
  const dailyCalorie = 
    (typeof caloricTargetObj === 'object' && caloricTargetObj?.range_kcal) ||
    caloricTargetObj ||
    '--'

  return (
    <div>
      <section className="result-section">
        <h2 className="section-heading">📊 Dietary Guidelines</h2>
        <div className="guideline-grid">
          <div className="guideline-card">
            <div className="small-subtext">🔥 Daily Calorie Target</div>
            <div className="guideline-main">{dailyCalorie}</div>
            <div className="small-subtext">Maintain a balanced caloric intake based on your profile.</div>
          </div>
          <div className="guideline-card">
            <div className="small-subtext">Macronutrient Split</div>
            <div className="macro-grid">
              <div><span>Protein</span><strong><Percentage value={macros.protein_percent ?? macros.protein} /></strong></div>
              <div><span>Carbs</span><strong><Percentage value={macros.carbs_percent ?? macros.carbs} /></strong></div>
              <div><span>Fat</span><strong><Percentage value={macros.fat_percent ?? macros.fat} /></strong></div>
            </div>
          </div>
        </div>

        <details className="collapse-panel">
          <summary>✅ Key Nutrients to Increase</summary>
          <div className="collapse-body">
            {nutrientsToIncrease.length
              ? nutrientsToIncrease.map((n, i) => <div key={i} className="list-line">• {n}</div>)
              : <div className="small-subtext">No nutrient-specific suggestion found.</div>}
          </div>
        </details>

        <details className="collapse-panel">
          <summary>💚 Foods to Emphasize</summary>
          <div className="collapse-body">
            {foodsToEmphasize.length
              ? foodsToEmphasize.map((f, i) => <div key={i} className="list-line">• {f}</div>)
              : <div className="small-subtext">No food emphasis list found.</div>}
          </div>
        </details>

        <details className="collapse-panel">
          <summary>🚫 Foods to Avoid / Limit</summary>
          <div className="collapse-body">
            {foodsToAvoid.length
              ? foodsToAvoid.map((f, i) => <div key={i} className="list-line">• {f}</div>)
              : <div className="small-subtext">No avoid list found.</div>}
          </div>
        </details>

        <details className="collapse-panel">
          <summary>⚖️ Nutrients to Limit</summary>
          <div className="collapse-body">
            {nutrientsToLimit.length
              ? nutrientsToLimit.map((n, i) => <div key={i} className="list-line">• {n}</div>)
              : <div className="small-subtext">No nutrient limit list found.</div>}
          </div>
        </details>
      </section>

      <section className="result-section">
        <h2 className="section-heading">🛡️ Safety Assessment</h2>
        <div className="safe-banner">✅ Diet plan passed all safety checks.</div>
        <details className="collapse-panel">
          <summary>⚠️ Safety Warnings ({warnings.length})</summary>
          <div className="collapse-body">
            {warnings.length
              ? warnings.map((w, i) => <div key={i} className="list-line">• {w}</div>)
              : <div className="small-subtext">No warnings found.</div>}
          </div>
        </details>
        <div className="safe-banner">✅ Output validated against WHO/NIH thresholds — no violations.</div>
      </section>

      <section className="result-section">
        <h2 className="section-heading">🍽️ Your Personalized Meal Plan</h2>
        <details className="collapse-panel">
          <summary>🧾 Update Diet Preferences & Reload</summary>
          <div className="collapse-body">
            <label className="sb-label">Diet Type</label>
            <select className="sb-input" value={localPrefs.diet_type} onChange={(e) => setFilter('diet_type', e.target.value)}>
              {DIET_TYPES.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>

            <label className="sb-label">Meal Frequency</label>
            <select className="sb-input" value={localPrefs.meal_frequency} onChange={(e) => setFilter('meal_frequency', e.target.value)}>
              {MEAL_FREQ.map((t) => (
                <option key={t.value} value={t.value}>{t.label}</option>
              ))}
            </select>

            <label className="sb-label">Regional Cuisine</label>
            <select className="sb-input" value={localPrefs.cuisine} onChange={(e) => setFilter('cuisine', e.target.value)}>
              {CUISINES.map((c) => (
                <option key={c} value={c}>{c || 'No preference'}</option>
              ))}
            </select>

            <label className="sb-label">Calorie Target (0 = auto)</label>
            <input
              className="sb-input"
              type="number"
              min={0}
              max={5000}
              step={100}
              value={localPrefs.calorie_target}
              onChange={(e) => setFilter('calorie_target', Number(e.target.value || 0))}
            />

            <label className="sb-label">Allergies / Exclusions</label>
            <input
              className="sb-input"
              type="text"
              placeholder="e.g. peanuts, gluten"
              value={localPrefs.allergies}
              onChange={(e) => setFilter('allergies', e.target.value)}
            />

            <label className="sb-label">Budget Level</label>
            <select className="sb-input" value={localPrefs.budget_level} onChange={(e) => setFilter('budget_level', e.target.value)}>
              {BUDGETS.map((b) => (
                <option key={b.value} value={b.value}>{b.label}</option>
              ))}
            </select>

            <div className="action-row" style={{ marginTop: 10 }}>
              <button className="btn btn-primary" onClick={applyFiltersAndReload}>Apply Filters & Reload Plan</button>
              <button className="btn btn-secondary" onClick={() => onReload && onReload()}>Reload Using Current Saved Preferences</button>
            </div>
          </div>
        </details>

        {renderDietContent(plan)}
      </section>

      {confidence && typeof confidence === 'object' && (
        <section className="result-section">
          <details className="collapse-panel">
            <summary>📊 Confidence Assessment</summary>
            {confidence.overall_confidence && (
              <p className="list-line">Overall: <strong>{confidence.overall_confidence}</strong></p>
            )}
            {qualityNotes.map((n, i) => <p key={i} className="list-line">• {n}</p>)}
            {limitations.map((l, i) => <p key={i} className="list-line">⚠ {l}</p>)}
          </details>
        </section>
      )}

      <div className="disclaimer">
        <strong>⚠️ Medical Disclaimer</strong><br />
        {disclaimer ||
          'This diet plan is generated by AI based on your medical reports and is for informational purposes only. It is NOT a substitute for professional medical advice. Always consult your doctor or a registered dietitian before making dietary changes.'}
      </div>
    </div>
  )
}
