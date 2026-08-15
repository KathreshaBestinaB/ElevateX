import { useEffect, useState } from 'react'
import { fetchOutcomeSummary, fetchTimeline } from '../services/api.js'
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid,
} from 'recharts'

const CHART_TOOLTIP = {
  background: 'rgba(13,22,38,0.95)',
  border: '1px solid rgba(148,163,184,0.15)',
  borderRadius: 8,
  color: '#f0f6ff',
  fontSize: 12,
  padding: '8px 12px',
}

function ResponseBadge({ status }) {
  if (!status) return null
  const map = {
    'Strong Response':   'badge-strong',
    'Moderate Response': 'badge-moderate',
    'Minimal Response':  'badge-minimal',
    'No Response':       'badge-no-response',
    'Worsened':          'badge-worsened',
  }
  return <span className={`badge ${map[status] || 'badge-neutral'}`}>{status}</span>
}

function QPanel({ number, label, color, children, defaultOpen = false }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="q-panel">
      <div className="q-header" onClick={() => setOpen(o => !o)} role="button" aria-expanded={open}>
        <div className="q-number" style={{ background: color + '22', color }}>Q{number}</div>
        <div className="q-label">{label}</div>
        <span className={`q-chevron${open ? ' open' : ''}`}>▶</span>
      </div>
      {open && <div className="q-body">{children}</div>}
    </div>
  )
}

function MiniTimeline({ events }) {
  if (!events?.length) return <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No timeline data</div>

  const COLOR_MAP = {
    diagnosis:        '#ef4444',
    medication:       '#6366f1',
    lab_test:         '#8b5cf6',
    trial_enrollment: '#10b981',
    trial_completion: '#f59e0b',
    adverse_event:    '#fb923c',
    outcome:          '#06b6d4',
  }

  return (
    <div className="timeline">
      {events.map(ev => (
        <div key={ev.event_id} className="timeline-item">
          <div className="timeline-dot" style={{ color: COLOR_MAP[ev.event_type] || '#94a3b8' }} />
          <div className="timeline-content">
            <div className="timeline-date">{ev.date}</div>
            <div className="timeline-title">{ev.title}</div>
            <div className="timeline-desc">{ev.description}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function PatientProfile({ patientId: initialId, onNavigate }) {
  const [patientId, setPatientId] = useState(initialId || 'P001024')
  const [inputId,   setInputId]   = useState(initialId || 'P001024')
  const [summary,   setSummary]   = useState(null)
  const [timeline,  setTimeline]  = useState(null)
  const [loading,   setLoading]   = useState(true)
  const [error,     setError]     = useState(null)

  function loadPatient(id) {
    setLoading(true)
    setError(null)
    setSummary(null)
    setTimeline(null)
    Promise.allSettled([fetchOutcomeSummary(id), fetchTimeline(id)])
      .then(([s, t]) => {
        if (s.status === 'fulfilled') setSummary(s.value)
        else setError(s.reason?.message || 'Failed to load outcome summary')
        if (t.status === 'fulfilled') setTimeline(t.value)
        setLoading(false)
      })
  }

  useEffect(() => { loadPatient(patientId) }, [patientId])

  const outcome = summary?.primary_outcome
  const meds    = summary?.interventions || []
  const nonResp = summary?.non_response_analysis
  const alts    = summary?.alternative_pathways || []
  const cohortObj = summary?.cohort_resemblance
  const cohorts = Array.isArray(cohortObj)
    ? cohortObj
    : (cohortObj?.resembled_cohorts || [])
  const patient = summary?.patient

  // Build HbA1c sparkline data
  const sparkData = outcome ? [
    { t: 'Baseline',  value: outcome.baseline_value },
    { t: '12-week',   value: outcome.baseline_value && outcome.followup_value
        ? +(outcome.baseline_value + (outcome.followup_value - outcome.baseline_value) / 2).toFixed(1)
        : null },
    { t: 'Final',     value: outcome.followup_value },
  ].filter(d => d.value !== null) : []

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Patient Intelligence</h2>
          <p>Post-trial outcome analysis — 6 research questions answered for every patient</p>
        </div>
        {/* Patient search */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input
            id="input-patient-id"
            className="input"
            style={{ width: 160 }}
            value={inputId}
            onChange={e => setInputId(e.target.value)}
            placeholder="Patient ID"
            onKeyDown={e => e.key === 'Enter' && setPatientId(inputId)}
          />
          <button
            id="btn-load-patient"
            className="btn btn-primary"
            onClick={() => setPatientId(inputId)}
          >🔍 Load</button>
          <button
            id="btn-run-matching"
            className="btn btn-ghost"
            onClick={() => onNavigate('matching', { patientId })}
          >🎯 Match Trials</button>
        </div>
      </div>

      <div className="page-body">
        {loading && (
          <div className="loading-state">
            <div className="spinner" />
            <span>Analysing patient outcome data…</span>
          </div>
        )}

        {error && !loading && (
          <div className="error-state">❌ {error}</div>
        )}

        {summary && !loading && (
          <>
            {/* Patient overview */}
            <div className="card card-accent" style={{ marginBottom: 20 }}>
              <div style={{ display: 'flex', gap: 24, alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div style={{ flex: '0 0 auto' }}>
                  <div style={{ width: 64, height: 64, borderRadius: 16, background: 'linear-gradient(135deg,#0ea5e9,#2dd4bf)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 28 }}>
                    👤
                  </div>
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap', marginBottom: 8 }}>
                    <span style={{ fontSize: 20, fontWeight: 800, fontFamily: 'JetBrains Mono' }}>{summary.patient_id}</span>
                    <span className="badge badge-neutral">{patient?.gender}</span>
                    <span className="badge badge-neutral">Age {patient?.age}</span>
                    {outcome?.response_status && <ResponseBadge status={outcome.response_status} />}
                  </div>
                  <div className="chip-list" style={{ marginBottom: 10 }}>
                    {(patient?.conditions || []).map(c => <span key={c} className="chip chip-blue">{c}</span>)}
                  </div>
                  <div className="chip-list">
                    {(patient?.medications || []).map(m => <span key={m} className="chip">{m}</span>)}
                  </div>
                </div>
                {/* Outcome mini-card */}
                {outcome && (
                  <div style={{ background: 'var(--bg-glass)', borderRadius: 12, padding: '14px 20px', textAlign: 'center', border: '1px solid var(--border)' }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                      {outcome.outcome_type} Change
                    </div>
                    <div style={{ fontSize: 32, fontWeight: 900, color: (outcome.change || 0) < 0 ? 'var(--green)' : 'var(--red)', fontFamily: 'JetBrains Mono' }}>
                      {outcome.change > 0 ? '+' : ''}{outcome.change}
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
                      {outcome.baseline_value} → {outcome.followup_value} {outcome.unit}
                    </div>
                    <div style={{ marginTop: 8 }}>
                      <ResponseBadge status={outcome.response_status} />
                    </div>
                  </div>
                )}
              </div>

              {/* Biomarker sparkline */}
              {sparkData.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 8 }}>
                    {outcome.outcome_type} Trajectory ({outcome.unit})
                  </div>
                  <ResponsiveContainer width="100%" height={80}>
                    <LineChart data={sparkData}>
                      <CartesianGrid stroke="rgba(148,163,184,0.07)" vertical={false} />
                      <XAxis dataKey="t" tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} />
                      <YAxis domain={['dataMin - 0.5', 'dataMax + 0.5']} hide />
                      <Tooltip contentStyle={CHART_TOOLTIP} />
                      <ReferenceLine y={7.0} stroke="rgba(52,211,153,0.4)" strokeDasharray="4 4" label={{ value: 'Target 7.0', fill: '#34d399', fontSize: 10 }} />
                      <Line type="monotone" dataKey="value" stroke="#38bdf8" strokeWidth={2.5}
                        dot={{ fill: '#38bdf8', r: 4, strokeWidth: 0 }} />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>

            {/* 6 Questions */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginBottom: 24 }}>

              {/* Q1 — What was given? */}
              <QPanel number={1} label="What was given? — Interventions administered" color="#38bdf8" defaultOpen>
                {meds.length > 0 ? meds.map(m => (
                  <div key={m.medication_id} style={{ background: 'var(--bg-glass)', borderRadius: 10, padding: 16, marginBottom: 8 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                      <span style={{ fontSize: 22 }}>💊</span>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{m.medication_name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{m.drug_class}</div>
                      </div>
                      <span className="badge badge-accent" style={{ marginLeft: 'auto' }}>
                        {m.is_investigational ? 'Investigational' : 'Standard'}
                      </span>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(120px,1fr))', gap: 8 }}>
                      {[
                        ['Dose', m.dose], ['Route', m.route], ['Frequency', m.frequency],
                        ['Duration', `${m.duration_weeks}w`], ['Start', m.start_date], ['End', m.end_date],
                        ['Combination', m.combination_with?.join?.(',') || m.combination_with || 'None'],
                      ].map(([k, v]) => v && (
                        <div key={k} style={{ fontSize: 11.5 }}>
                          <div style={{ color: 'var(--text-muted)', marginBottom: 2 }}>{k}</div>
                          <div style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{v}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )) : <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No intervention records</div>}
              </QPanel>

              {/* Q2 — Did it work? */}
              <QPanel number={2} label="Did it work? — Primary endpoint result" color="#34d399" defaultOpen>
                {outcome ? (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(140px,1fr))', gap: 12 }}>
                    {[
                      { label: 'Baseline', value: `${outcome.baseline_value} ${outcome.unit}`, accent: false },
                      { label: 'Follow-up', value: `${outcome.followup_value} ${outcome.unit}`, accent: false },
                      { label: 'Absolute Change', value: `${outcome.change > 0 ? '+' : ''}${outcome.change} ${outcome.unit}`,
                        accent: true, color: (outcome.change||0) < 0 ? 'var(--green)' : 'var(--red)' },
                      { label: 'Relative Change', value: `${outcome.change_pct}%`, accent: true,
                        color: (outcome.change||0) < 0 ? 'var(--green)' : 'var(--red)' },
                      { label: 'Treatment', value: outcome.treatment_completed ? '✅ Completed' : '⚠ Incomplete', accent: false },
                      { label: 'Adverse Events', value: (outcome.adverse_events || []).join(', ') || 'None', accent: false },
                    ].map(item => (
                      <div key={item.label} style={{ background: 'var(--bg-glass)', borderRadius: 8, padding: 12 }}>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 4 }}>{item.label}</div>
                        <div style={{ fontSize: 15, fontWeight: 700, color: item.color || 'var(--text-primary)' }}>{item.value}</div>
                      </div>
                    ))}
                  </div>
                ) : <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No outcome data</div>}
              </QPanel>

              {/* Q3 — How did patient respond? */}
              <QPanel number={3} label="How did the patient respond? — Response classification" color="#a78bfa">
                <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <ResponseBadge status={outcome?.response_status} />
                    <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
                      {summary.response_narrative}
                    </span>
                  </div>
                  {/* Response scale visual */}
                  <div style={{ marginTop: 8 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', marginBottom: 6 }}>Response Scale</div>
                    {[
                      { label: 'Strong Response', width: 90, color: 'var(--strong-resp)' },
                      { label: 'Moderate Response', width: 60, color: 'var(--moderate-resp)' },
                      { label: 'Minimal Response', width: 35, color: 'var(--amber)' },
                      { label: 'No Response', width: 12, color: 'var(--no-resp)' },
                    ].map(r => (
                      <div key={r.label} style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                        <div style={{ width: 120, fontSize: 11, color: 'var(--text-muted)' }}>{r.label}</div>
                        <div style={{ flex: 1 }}>
                          <div className="progress-bar-wrap">
                            <div className="progress-bar-fill" style={{
                              width: `${r.width}%`,
                              background: r.label === outcome?.response_status
                                ? `linear-gradient(90deg,${r.color},${r.color}dd)`
                                : 'var(--bg-glass-hover)',
                            }} />
                          </div>
                        </div>
                        {r.label === outcome?.response_status && (
                          <span style={{ fontSize: 11, color: r.color, fontWeight: 700 }}>← This patient</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              </QPanel>

              {/* Q4 — Why didn't they respond? */}
              <QPanel number={4} label="Why might the patient have failed to fully respond?" color="#fb923c">
                {nonResp ? (
                  <div>
                    <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginBottom: 12 }}>
                      {nonResp.summary}
                    </p>
                    {nonResp.contributing_factors?.length > 0 && (
                      <div style={{ marginBottom: 12 }}>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 8 }}>
                          Contributing Factors
                        </div>
                        {nonResp.contributing_factors.map((f, i) => (
                          <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 8,
                            background: 'var(--bg-glass)', borderRadius: 8, padding: 12 }}>
                            <span style={{ color: 'var(--amber)', fontSize: 16, flexShrink: 0 }}>⚠</span>
                            <div>
                              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{f.factor}</div>
                              <div style={{ fontSize: 12, color: 'var(--text-secondary)' }}>{f.explanation}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    {nonResp.biomarker_flags?.length > 0 && (
                      <div>
                        <div style={{ fontSize: 11, fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: 6 }}>
                          Biomarker Flags
                        </div>
                        <div className="chip-list">
                          {nonResp.biomarker_flags.map((f, i) => <span key={i} className="chip chip-red">{f}</span>)}
                        </div>
                      </div>
                    )}
                  </div>
                ) : <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>Not applicable — patient responded positively.</div>}
              </QPanel>

              {/* Q5 — Alternative pathways */}
              <QPanel number={5} label="What alternative research pathways exist?" color="#2dd4bf">
                {alts.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {alts.map((alt, i) => (
                      <div key={i} style={{ background: 'var(--bg-glass)', borderRadius: 10, padding: 14, display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                        <div style={{ width: 32, height: 32, borderRadius: 8, background: 'rgba(45,212,191,0.15)', border: '1px solid rgba(45,212,191,0.3)',
                          display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, flexShrink: 0 }}>
                          {i + 1}
                        </div>
                        <div style={{ flex: 1 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4, flexWrap: 'wrap' }}>
                            <span style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>{alt.pathway_name}</span>
                            <span className={`badge ${alt.priority === 'High' ? 'badge-strong' : alt.priority === 'Medium' ? 'badge-moderate' : 'badge-neutral'}`}>
                              {alt.priority}
                            </span>
                            <span className="badge badge-neutral">{alt.trial_type}</span>
                          </div>
                          <div style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 6 }}>{alt.rationale}</div>
                          {alt.relevant_trials?.length > 0 && (
                            <div className="chip-list">
                              {alt.relevant_trials.map((t, j) => <span key={j} className="chip chip-blue">{t}</span>)}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No alternative pathways identified</div>}
              </QPanel>

              {/* Q6 — Cohort resemblance */}
              <QPanel number={6} label="What research cohort does this patient resemble?" color="#f59e0b">
                {cohorts.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {cohorts.map((c, i) => (
                      <div key={i} style={{ background: 'var(--bg-glass)', borderRadius: 10, padding: 14 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
                          <div style={{ flex: 1 }}>
                            <div style={{ fontSize: 13.5, fontWeight: 700, color: 'var(--text-primary)' }}>{c.cohort_name}</div>
                            <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>n = {c.cohort_size?.toLocaleString()} patients</div>
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: 22, fontWeight: 900, color: 'var(--amber)', fontFamily: 'JetBrains Mono' }}>
                              {(c.similarity_score * 100).toFixed(0)}%
                            </div>
                            <div style={{ fontSize: 10, color: 'var(--text-muted)' }}>match</div>
                          </div>
                        </div>
                        <div style={{ marginBottom: 8 }}>
                          <div className="progress-bar-wrap">
                            <div className="progress-bar-fill" style={{ width: `${c.similarity_score * 100}%`, background: 'linear-gradient(90deg,#f59e0b,#fbbf24)' }} />
                          </div>
                        </div>
                        <p style={{ fontSize: 12, color: 'var(--text-secondary)', marginBottom: 8 }}>{c.description}</p>
                        {c.key_features?.length > 0 && (
                          <div className="chip-list">
                          {(Array.isArray(c.key_features)
                          ? c.key_features
                          : (c.key_features || c.key_shared_features || '').split(/\s{2,}|\|/).filter(Boolean)
                        ).map((f, j) => <span key={j} className="chip">{f}</span>)}
                          </div>
                        )}
                        {c.most_effective_treatment && (
                          <div style={{ marginTop: 8, fontSize: 12, color: 'var(--teal)' }}>
                            💡 Best response: <strong>{c.most_effective_treatment}</strong>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                ) : <div style={{ color: 'var(--text-muted)', fontSize: 12 }}>No cohort data</div>}
              </QPanel>
            </div>

            {/* Timeline */}
            {timeline?.events && (
              <div className="card">
                <div className="card-header">
                  <div className="card-title">📅 Clinical Timeline</div>
                  <span className="badge badge-neutral">{timeline.event_count} events</span>
                </div>
                <MiniTimeline events={timeline.events} />
              </div>
            )}
          </>
        )}
      </div>
    </>
  )
}
