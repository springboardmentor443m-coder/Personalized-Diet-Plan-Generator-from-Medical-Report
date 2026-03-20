import { useState, useRef } from 'react'

const CATEGORIES = [
  { key: 'lab_report',        label: '🧪 Lab Reports',                    desc: 'Blood tests, urine, lipid panels, HbA1c, CBC, LFT, KFT, thyroid, etc.' },
  { key: 'diagnosis',         label: '📋 Diagnosis / Clinical Summaries', desc: "Doctor's diagnosis, clinical impressions, specialist opinions." },
  { key: 'prescription',      label: '💊 Prescriptions',                  desc: 'Medication prescriptions, drug dosages, pharmacy records.' },
  { key: 'discharge_summary', label: '🏥 Discharge Summaries & Other',    desc: 'Hospital discharge papers, admission summaries, other docs.' },
]

export default function UploadTab({ onAnalyze, onGenerateDiet, loading, error, analysisDone, onReset }) {
  const [catFiles, setCatFiles] = useState({ lab_report: [], diagnosis: [], prescription: [], discharge_summary: [] })
  const inputRefs = useRef({})

  function resetUploads() {
    setCatFiles({ lab_report: [], diagnosis: [], prescription: [], discharge_summary: [] })
    onReset()
  }

  function addFiles(key, incoming) {
    const accepted = Array.from(incoming).filter(f =>
      ['application/pdf', 'image/jpeg', 'image/png', 'image/jpg', 'image/webp'].includes(f.type) || f.name.endsWith('.pdf')
    )
    setCatFiles(prev => {
      const names = new Set(prev[key].map(f => f.name))
      return { ...prev, [key]: [...prev[key], ...accepted.filter(f => !names.has(f.name))] }
    })
  }

  function removeFile(key, idx) {
    setCatFiles(prev => ({ ...prev, [key]: prev[key].filter((_, i) => i !== idx) }))
  }

  const allFiles = Object.values(catFiles).flat()
  const totalCount = allFiles.length

  function collectFiles() {
    return Object.entries(catFiles).flatMap(([, files]) => files)
  }

  return (
    <div>
      <h2 className="tab-heading">Upload Medical Reports</h2>
      <p className="tab-sub">Upload documents by category. The AI will auto-verify your selection after processing.</p>

      <div className="cat-grid">
        {CATEGORIES.map(cat => (
          <div key={cat.key} className="cat-card">
            <div className="cat-label">{cat.label}</div>
            <div className="cat-desc">{cat.desc}</div>
            <button className="upload-btn" onClick={() => inputRefs.current[cat.key].click()} disabled={loading}>
              + Add Files
            </button>
            <input
              ref={el => inputRefs.current[cat.key] = el}
              type="file" accept=".pdf,image/*" multiple style={{ display: 'none' }}
              onChange={e => addFiles(cat.key, e.target.files)}
            />
            {catFiles[cat.key].length > 0 && (
              <ul className="cat-file-list">
                {catFiles[cat.key].map((f, i) => (
                  <li key={i}>
                    <span>{f.name.endsWith('.pdf') ? '📑' : '🖼️'} {f.name}</span>
                    <button onClick={() => removeFile(cat.key, i)}>✕</button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        ))}
      </div>

      {totalCount > 0 && (
        <div className="upload-summary">
          <strong>📊 {totalCount} file(s) ready</strong>
          {Object.entries(catFiles).map(([key, files]) => files.length > 0 && (
            <span key={key} className="summary-badge">{CATEGORIES.find(c => c.key === key)?.label.split(' ')[0]} {files.length}</span>
          ))}
        </div>
      )}

      {error && <div className="error-box">⚠ {error}</div>}

      {totalCount > 0 && (
        <div className="action-row">
          <button className="btn btn-secondary" disabled={loading} onClick={() => onAnalyze(collectFiles())}>
            🔬 Analyze Reports
          </button>
          <button className="btn btn-primary" disabled={loading} onClick={() => onGenerateDiet(collectFiles())}>
            🥗 Analyze & Generate Diet Plan
          </button>
        </div>
      )}

      {analysisDone && (
        <div className="result-section">
          <button className="btn btn-ghost" onClick={resetUploads}>🔄 Start Over</button>
        </div>
      )}
    </div>
  )
}
