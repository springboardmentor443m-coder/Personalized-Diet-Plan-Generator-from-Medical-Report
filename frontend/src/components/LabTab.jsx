function fmt(v) {
  if (v === null || v === undefined || v === '') return '--'
  return String(v)
}

function pickPatientFields(info = {}) {
  const name = info.name || info.patient_name || info.full_name || info.patient || '--'
  const age = info.age || info.age_years || '--'
  const gender = info.gender || info.sex || '--'
  const reportDate = info.report_date || info.date || info.collection_date || '--'
  return [
    { label: 'Name', value: name },
    { label: 'Age', value: age },
    { label: 'Gender', value: gender },
    { label: 'Report Date', value: reportDate },
  ]
}

function normalizeTests(tests) {
  if (!tests || typeof tests !== 'object') return []
  return Object.entries(tests).map(([key, raw]) => {
    const t = raw && typeof raw === 'object' ? raw : { current_value: raw }
    const statusRaw = t.current_interpretation ?? t.interpretation ?? t.status ?? t.flag ?? '--'
    return {
      id: key,
      name: t.test_name || key.replace(/_/g, ' '),
      value: fmt(t.current_value ?? t.value ?? t.result),
      units: fmt(t.units ?? t.unit),
      reference: fmt(t.reference_range ?? t.normal_range),
      status: String(statusRaw || '--').toLowerCase(),
    }
  })
}

function normalizeFindings(findings) {
  if (Array.isArray(findings)) {
    return findings.map((f, idx) => {
      if (!f || typeof f !== 'object') {
        return { id: `f-${idx}`, test: String(f), value: '--', severity: 'flag' }
      }
      return {
        id: f.canonical_test_key || f.test_key || f.test_name || f.name || `f-${idx}`,
        test: f.test_name || f.name || f.canonical_test_key || f.test_key || `Finding ${idx + 1}`,
        value: fmt(f.observed_value ?? f.value ?? f.current_value),
        unit: f.units || f.unit || '',
        severity: String(f.severity || f.status || f.flag || f.current_interpretation || 'flag').toLowerCase(),
      }
    })
  }

  if (findings && typeof findings === 'object') {
    return Object.entries(findings).map(([key, value], idx) => ({
      id: key || `f-${idx}`,
      test: key,
      value: fmt(value),
      unit: '',
      severity: 'flag',
    }))
  }

  return []
}

function PatientInfo({ info }) {
  if (!info || !Object.keys(info).length) return null
  const fields = pickPatientFields(info)
  return (
    <section className="result-section">
      <h2 className="section-heading">👤 Patient Information</h2>
      <div className="patient-row">
        {fields.map((item) => (
          <div key={item.label} className="patient-item">
            <div className="patient-label">{item.label}</div>
            <div className="patient-value">{fmt(item.value)}</div>
          </div>
        ))}
      </div>
    </section>
  )
}

function TestsTable({ tests }) {
  const rows = normalizeTests(tests)
  if (!rows.length) return null
  return (
    <section className="result-section">
      <h2 className="section-heading">🧪 Lab Test Results</h2>
      <div className="small-subtext">{rows.length} test(s) extracted</div>
      <div className="test-table-wrap">
        <table className="test-table">
          <thead>
            <tr>
              <th>Test</th>
              <th>Value</th>
              <th>Units</th>
              <th>Reference Range</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              const statusClass = row.status.includes('high')
                ? 'status-high'
                : row.status.includes('low')
                  ? 'status-low'
                  : ''
              return (
                <tr key={row.id}>
                  <td>{row.name}</td>
                  <td>{row.value}</td>
                  <td>{row.units}</td>
                  <td>{row.reference}</td>
                  <td><span className={`status-badge ${statusClass}`}>{row.status || '--'}</span></td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function AbnormalFindings({ findings }) {
  const rows = normalizeFindings(findings)
  if (!rows.length) {
    return (
      <section className="result-section">
        <h2 className="section-heading">⚠️ Abnormal Findings</h2>
        <div className="small-subtext">No abnormal findings detected.</div>
      </section>
    )
  }
  return (
    <section className="result-section">
      <h2 className="section-heading">⚠️ Abnormal Findings</h2>
      <div className="finding-list">
        {rows.map((f) => {
          const cls = f.severity.includes('high')
            ? 'finding-high'
            : f.severity.includes('low')
              ? 'finding-low'
              : 'finding-flag'
          return (
            <div key={f.id} className={`finding-item ${cls}`}>
              <strong>{f.test}:</strong>
              <span>{` ${f.value}${f.unit ? ` ${f.unit}` : ''} — ${f.severity}`}</span>
            </div>
          )
        })}
      </div>
    </section>
  )
}

function DocumentDetails({ docs }) {
  if (!docs?.length) return null
  return (
    <details className="collapse-panel result-section">
      <summary>📋 Per-Document Details</summary>
      <div className="collapse-body">
        {docs.map((doc, idx) => (
          <div key={idx} className="doc-row">
            <div><strong>{doc.original_filename || `document-${idx + 1}`}</strong></div>
            <div className="small-subtext">
              Declared: {fmt(doc.user_declared_type)} | Detected: {fmt(doc.doc_type)} | Status: {fmt(doc.status)}
            </div>
          </div>
        ))}
      </div>
    </details>
  )
}

export default function LabTab({ data, loading, loadingMsg, onGenerateDiet, dietDone, dietGenerating }) {
  if (!data && !loading) {
    return (
      <div className="empty-state">
        <h3>🧪 No Lab Results Yet</h3>
        <p>Upload your medical reports in Upload Reports and click Analyze.</p>
      </div>
    )
  }

  const tests = data?.aggregated_tests || data?.tests_index || {}
  const abnormal = data?.aggregated_abnormal_findings || data?.abnormal_findings || []
  const docs = data?.per_document_results || []
  const procTime = data?.processing_time_seconds

  return (
    <div>
      {data && (
        <div className="success-banner">
          ✅ {data.documents_processed != null
            ? `Processed ${data.documents_processed} document(s)`
            : 'Report analyzed'}
          {procTime > 0 && ` in ${Number(procTime).toFixed(2)}s`}
        </div>
      )}

      {data && (
        <>
          <PatientInfo info={data.patient_information} />
          <TestsTable tests={tests} />
          <AbnormalFindings findings={abnormal} />
          <DocumentDetails docs={docs} />
        </>
      )}

      {!dietDone && data && (
        <div className="result-section">
          <button className="btn btn-danger" onClick={() => onGenerateDiet()} disabled={loading}>
            🍲 Generate Diet Plan from These Results
          </button>
        </div>
      )}

      {dietGenerating && (
        <div className="result-section">
          <div className="small-subtext">AI generating diet plan...</div>
          <div className="progress-track"><div className="progress-fill" /></div>
          <div className="small-subtext">🍲 {loadingMsg || 'Generating personalized diet plan (this may take 30-60 seconds)...'}</div>
        </div>
      )}
    </div>
  )
}
