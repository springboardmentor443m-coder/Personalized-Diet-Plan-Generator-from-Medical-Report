import { useState, useEffect, useRef } from 'react'
import { submitDietTask, submitProcessReportsTask, submitRegenerateDietTask, pollTask } from './api.js'
import Sidebar from './components/Sidebar.jsx'
import UploadTab from './components/UploadTab.jsx'
import LabTab from './components/LabTab.jsx'
import DietTab from './components/DietTab.jsx'
import ChatTab from './components/ChatTab.jsx'

const TABS = [
  { id: 'upload', label: '📄 Upload Reports' },
  { id: 'lab', label: '🧪 Lab Results' },
  { id: 'diet', label: '🥗 Diet Plan' },
  { id: 'chat', label: '💬 Chat Assistant' },
]

function isPlainObject(value) {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return false
  const proto = Object.getPrototypeOf(value)
  return proto === Object.prototype || proto === null
}

function StepIndicator({ analysisDone, dietDone, chatReady }) {
  const steps = [
    { label: '📄 Upload', done: true },
    { label: '🧪 Analyze', done: analysisDone },
    { label: '🥗 Diet Plan', done: dietDone },
    { label: '💬 Chat', done: chatReady },
  ]
  return (
    <div className="step-indicator">
      {steps.map(s => (
        <span key={s.label} className={`step-badge${s.done ? ' done' : ''}`}>
          {s.done ? '✅' : '⏳'} {s.label}
        </span>
      ))}
    </div>
  )
}

export default function App() {
  const [activeTab, setActiveTab] = useState('upload')
  const [loading, setLoading] = useState(false)
  const [loadingMsg, setLoadingMsg] = useState('')
  const [error, setError] = useState(null)
  const [results, setResults] = useState(null)
  const [dietData, setDietData] = useState(null)
  const [prefs, setPrefs] = useState({})
  const [bmi, setBmi] = useState(null)
  const [uploadedFiles, setUploadedFiles] = useState([])
  const pollRef = useRef(null)

  useEffect(() => {
    return () => clearInterval(pollRef.current)
  }, [])

  function poll(taskId, onDone) {
    clearInterval(pollRef.current)
    pollRef.current = setInterval(async () => {
      try {
        const data = await pollTask(taskId)
        setLoadingMsg(data.progress || 'Working...')
        if (data.status === 'complete') {
          clearInterval(pollRef.current)
          onDone(data.result || data)
        } else if (data.status === 'failed') {
          clearInterval(pollRef.current)
          setError(data.error || 'Task failed')
          setLoading(false)
        }
      } catch (err) {
        clearInterval(pollRef.current)
        setError(err.message)
        setLoading(false)
      }
    }, 2500)
  }

  async function handleAnalyze(files) {
    if (!files?.length) return
    setError(null)
    setLoading(true)
    setLoadingMsg('Analyzing reports...')
    setUploadedFiles(files)
    try {
      const { task_id } = await submitProcessReportsTask(files)
      poll(task_id, (data) => {
        setResults(data)
        setDietData(null)
        setLoading(false)
        setActiveTab('lab')
      })
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  async function handleGenerateDiet(files, prefsOverride = null) {
    const sourceFiles = files?.length ? files : uploadedFiles
    if (!sourceFiles?.length) {
      if (results?.diet_plan) {
        setDietData(results)
        setActiveTab('diet')
        return
      }
      setError('Please upload reports first, then generate a diet plan.')
      return
    }

    setError(null)
    setLoading(true)
    setLoadingMsg('Generating personalized diet plan...')
    setUploadedFiles(sourceFiles)

    const basePrefs = isPlainObject(prefsOverride) ? prefsOverride : prefs
    const requestPrefs = { ...basePrefs }
    if (bmi && typeof bmi === 'object') {
      requestPrefs.bmi = bmi
    }

    try {
      const { task_id } = await submitDietTask(sourceFiles, requestPrefs)
      poll(task_id, (data) => {
        setResults(data)
        setDietData(data)
        if (!data?.diet_plan && data?.diet_generation_metadata?.error) {
          setError(`Unable to generate diet plan: ${data.diet_generation_metadata.error}`)
        }
        setLoading(false)
        setActiveTab('diet')
      })
    } catch (err) {
      setError(err.message)
      setLoading(false)
    }
  }

  async function handleGenerateDietFromResults(prefsOverride = null) {
    const hasPrefsOverride = isPlainObject(prefsOverride)
    const baseResult = dietData || results
    const nextPrefs = hasPrefsOverride ? prefsOverride : (isPlainObject(prefs) ? prefs : {})

    if (hasPrefsOverride) {
      setPrefs(prefsOverride)
    }

    if (baseResult && isPlainObject(baseResult)) {
      const requestPrefs = { ...nextPrefs }
      if (bmi && typeof bmi === 'object') {
        requestPrefs.bmi = bmi
      }

      setError(null)
      setLoading(true)
      setLoadingMsg(hasPrefsOverride
        ? 'Applying filters and regenerating diet plan...'
        : 'Regenerating diet plan with current preferences...')
      try {
        const { task_id } = await submitRegenerateDietTask(baseResult, requestPrefs)
        poll(task_id, (data) => {
          setResults(data)
          setDietData(data)
          if (!data?.diet_plan && data?.diet_generation_metadata?.error) {
            setError(`Unable to generate diet plan: ${data.diet_generation_metadata.error}`)
          }
          setLoading(false)
          setActiveTab('diet')
        })
      } catch (err) {
        setError(err.message)
        setLoading(false)
      }
      return
    }

    if (uploadedFiles.length) {
      await handleGenerateDiet(uploadedFiles, hasPrefsOverride ? prefsOverride : nextPrefs)
      return
    }

    if (hasPrefsOverride) {
      setError('Cannot regenerate with new filters because original uploaded files are unavailable. Please upload reports again.')
      return
    }

    if (results?.diet_plan) {
      setDietData(results)
      setActiveTab('diet')
      return
    }
    setError('No uploaded files available. Please upload again and generate diet plan.')
  }

  function handleReset() {
    clearInterval(pollRef.current)
    setActiveTab('upload')
    setResults(null)
    setDietData(null)
    setUploadedFiles([])
    setError(null)
    setLoading(false)
    setLoadingMsg('')
  }

  const sessionId = dietData?.session_id || results?.session_id || ''

  return (
    <div className="app-shell">
      <Sidebar prefs={prefs} onPrefsChange={setPrefs} onBmiChange={setBmi} />

      <div className="main-area">
        <div className="main-header">
          <h1 className="app-title">🏥 AI-Powered Diet Plan Generator</h1>
          <p className="main-subtitle">Upload reports → Analyze lab data → Generate diet plan</p>
        </div>

        <StepIndicator analysisDone={!!results} dietDone={!!dietData} chatReady={!!sessionId} />

        <div className="tab-nav">
          {TABS.map(t => (
            <button
              key={t.id}
              className={`tab-btn${activeTab === t.id ? ' active' : ''}`}
              onClick={() => setActiveTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="tab-content">
          {error && <div className="error-box">⚠ {error}</div>}

          {loading && (
            <div className="overlay-loading">
              <div className="status-line">⏳ {loadingMsg}</div>
              <div className="progress-track"><div className="progress-fill" /></div>
              <p>This may take 30-60 seconds...</p>
            </div>
          )}

          {activeTab === 'upload' && (
            <UploadTab
              onAnalyze={handleAnalyze}
              onGenerateDiet={handleGenerateDiet}
              loading={loading}
              error={error}
              analysisDone={!!results}
              onReset={handleReset}
            />
          )}
          {activeTab === 'lab' && (
            <LabTab
              data={results}
              loading={loading}
              loadingMsg={loadingMsg}
              dietGenerating={loading && loadingMsg.toLowerCase().includes('diet')}
              onGenerateDiet={handleGenerateDietFromResults}
              dietDone={!!dietData}
            />
          )}
          {activeTab === 'diet' && (
            <DietTab data={dietData} prefs={prefs} onReload={handleGenerateDietFromResults} />
          )}
          {activeTab === 'chat' && (
            <ChatTab sessionId={sessionId} />
          )}
        </div>
      </div>
    </div>
  )
}
