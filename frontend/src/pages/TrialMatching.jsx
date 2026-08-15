import { useState, useEffect } from 'react'
import { runMatching } from '../services/api.js'

function ScoreMeter({ score }) {
  const color = score >= 70 ? 'var(--green)' : score >= 40 ? 'var(--amber)' : 'var(--red)'
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ position: 'relative', width: 52, height: 52 }}>
        <svg width="52" height="52" viewBox="0 0 52 52">
          <circle cx="26" cy="26" r="20" fill="none" stroke="var(--bg-glass)" strokeWidth="5" />
          <circle cx="26" cy="26" r="20" fill="none" stroke={color} strokeWidth="5"
            strokeDasharray={`${(score / 100) * 125.6} 125.6`}
            strokeLinecap="round" transform="rotate(-90 26 26)" />
        </svg>
        <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 11, fontWeight: 800, color, fontFamily: 'JetBrains Mono' }}>
          {score}
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }) {
  const map = {
    Eligible:            'badge-strong',
    'Potentially Eligible': 'badge-moderate',
    Ineligible:          'badge-no-response',
  }
  return <span className={`badge ${map[status] || 'badge-neutral'}`}>{status}</span>
}

export default function TrialMatching({ patientId: initialId, onNavigate }) {
  const [patientId, setPatientId] = useState(initialId || 'P001024')
  const [inputId,   setInputId]   = useState(initialId || 'P001024')
  const [results,   setResults]   = useState(null)
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState(null)
  const [minScore,  setMinScore]  = useState(0)
  const [expanded,  setExpanded]  = useState(null)

  useEffect(() => {
    const target = initialId || patientId || 'P001024'
    setPatientId(target)
    setInputId(target)
    setLoading(true)
    setError(null)
    runMatching(target, minScore, 30)
      .then(setResults)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [initialId])

  function handleRun() {
    setLoading(true)
    setError(null)
    setResults(null)
    setPatientId(inputId)
    runMatching(inputId, minScore, 30)
      .then(setResults)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  const eligible    = results?.filter(r => r.status === 'Eligible') || []
  const potential   = results?.filter(r => r.status === 'Potentially Eligible') || []
  const ineligible  = results?.filter(r => r.status === 'Ineligible') || []

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Trial Matching Engine</h2>
          <p>Hybrid eligibility scoring — explainable criteria matching with 0–100 score</p>
        </div>
      </div>

      <div className="page-body">
        {/* Controls */}
        <div className="card" style={{ marginBottom: 20 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 200px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Patient ID</label>
              <input id="matching-patient-id" className="input" value={inputId}
                onChange={e => setInputId(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleRun()}
                placeholder="e.g. P001024" />
            </div>
            <div style={{ flex: '0 0 160px' }}>
              <label style={{ fontSize: 11, color: 'var(--text-muted)', display: 'block', marginBottom: 6, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.07em' }}>Min Score</label>
              <input id="matching-min-score" className="input" type="number" min={0} max={100} value={minScore}
                onChange={e => setMinScore(Number(e.target.value))} />
            </div>
            <button id="btn-run-matching" className="btn btn-primary" onClick={handleRun} disabled={loading}>
              {loading ? '⏳ Matching…' : '🎯 Run Matching'}
            </button>
            <button className="btn btn-ghost" onClick={() => onNavigate('patient', { patientId })}>
              👤 View Outcomes
            </button>
          </div>
        </div>

        {loading && (
          <div className="loading-state">
            <div className="spinner" />
            <span>Running eligibility matching engine…</span>
          </div>
        )}

        {error && !loading && <div className="error-state">❌ {error}</div>}

        {results && !loading && (
          <>
            {/* Summary */}
            <div className="kpi-grid" style={{ marginBottom: 20 }}>
              <div className="kpi-card">
                <div className="kpi-label">Total Trials Evaluated</div>
                <div className="kpi-value">{results.length}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">✅ Eligible</div>
                <div className="kpi-value" style={{ color: 'var(--green)' }}>{eligible.length}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">🔶 Potentially Eligible</div>
                <div className="kpi-value" style={{ color: 'var(--amber)' }}>{potential.length}</div>
              </div>
              <div className="kpi-card">
                <div className="kpi-label">❌ Ineligible</div>
                <div className="kpi-value" style={{ color: 'var(--red)' }}>{ineligible.length}</div>
              </div>
            </div>

            {/* Results list */}
            {[
              { label: '✅ Eligible Trials', items: eligible,   color: 'var(--green)' },
              { label: '🔶 Potentially Eligible', items: potential, color: 'var(--amber)' },
              { label: '❌ Ineligible', items: ineligible.slice(0, 5), color: 'var(--red)' },
            ].map(group => group.items.length > 0 && (
              <div key={group.label} style={{ marginBottom: 20 }}>
                <div style={{ fontSize: 13, fontWeight: 700, color: group.color, marginBottom: 10 }}>
                  {group.label} ({group.items.length})
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {group.items.map(r => (
                    <div key={r.trial_id} className="card" style={{ padding: 16 }}>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 14 }}>
                        <ScoreMeter score={r.eligibility_score} />
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap', marginBottom: 6 }}>
                            <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)' }}>{r.trial_id}</span>
                            <StatusBadge status={r.status} />
                            {r.phase && <span className="badge badge-neutral">{r.phase}</span>}
                          </div>
                          <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 8 }}>{r.trial_title || r.title}</div>
                          {/* Criteria preview */}
                          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                            {r.matched_criteria?.slice(0, 3).map((c, i) => (
                              <span key={i} className="chip chip-green">✓ {typeof c === 'string' ? c : c.criterion_name || c.criterion}</span>
                            ))}
                            {r.failed_criteria?.slice(0, 2).map((c, i) => (
                              <span key={i} className="chip chip-red">✗ {typeof c === 'string' ? c : c.criterion_name || c.criterion}</span>
                            ))}
                          </div>
                        </div>
                        <button className="btn btn-ghost" style={{ fontSize: 11, padding: '5px 10px' }}
                          onClick={() => setExpanded(expanded === r.trial_id ? null : r.trial_id)}>
                          {expanded === r.trial_id ? '▲ Less' : '▼ Details'}
                        </button>
                      </div>

                      {/* Expanded detail */}
                      {expanded === r.trial_id && (
                        <div style={{ marginTop: 14, paddingTop: 14, borderTop: '1px solid var(--border)' }}>
                          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
                            <div>
                              <div style={{ fontSize: 11, color: 'var(--green)', fontWeight: 700, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                                ✓ Matched Criteria
                              </div>
                              {r.matched_criteria?.map((c, i) => (
                                <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '3px 0' }}>✓ {typeof c === 'string' ? c : c.criterion_name || c.criterion}</div>
                              ))}
                            </div>
                            <div>
                              <div style={{ fontSize: 11, color: 'var(--red)', fontWeight: 700, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                                ✗ Failed Criteria
                              </div>
                              {r.failed_criteria?.map((c, i) => (
                                <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '3px 0' }}>✗ {typeof c === 'string' ? c : c.criterion_name || c.criterion}</div>
                              ))}
                              {r.missing_data?.length > 0 && (
                                <>
                                  <div style={{ fontSize: 11, color: 'var(--amber)', fontWeight: 700, marginTop: 8, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                                    ⚠ Missing Data
                                  </div>
                                  {r.missing_data.map((m, i) => (
                                    <div key={i} style={{ fontSize: 12, color: 'var(--text-secondary)', padding: '3px 0' }}>⚠ {typeof m === 'string' ? m : m.criterion_name || m.criterion}</div>
                                  ))}
                                </>
                              )}
                            </div>
                          </div>
                          {r.explanation && (
                            <div style={{ marginTop: 12, padding: 12, background: 'var(--bg-glass)', borderRadius: 8, fontSize: 12.5, color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                              💡 {r.explanation}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </>
        )}

        {!results && !loading && !error && (
          <div className="loading-state" style={{ flexDirection: 'column', gap: 12 }}>
            <div style={{ fontSize: 48 }}>🎯</div>
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--text-secondary)' }}>
              Enter a patient ID and run the matching engine
            </div>
            <div style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              Try demo patient <strong style={{ color: 'var(--accent)' }}>P001024</strong>
            </div>
            <button className="btn btn-primary" id="btn-demo-match" onClick={() => { setInputId('P001024'); handleRun() }}>
              🎯 Run Demo Match
            </button>
          </div>
        )}
      </div>
    </>
  )
}
