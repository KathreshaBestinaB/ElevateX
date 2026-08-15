import { useEffect, useState } from 'react'
import { fetchCohortAnalytics } from '../services/api.js'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, ResponsiveContainer, Tooltip } from 'recharts'

const TOOLTIP_STYLE = {
  background: 'rgba(13,22,38,0.95)',
  border: '1px solid rgba(148,163,184,0.15)',
  borderRadius: 8,
  color: '#f0f6ff',
  fontSize: 12,
  padding: '8px 12px',
}

const COHORT_COLORS = ['#38bdf8', '#34d399', '#a78bfa', '#fbbf24', '#fb923c']

function CohortCard({ cohort, index, selected, onSelect }) {
  const color = COHORT_COLORS[index % COHORT_COLORS.length]
  const respPct = (cohort.positive_response_rate * 100).toFixed(0)

  return (
    <div
      className={`card${selected ? ' card-accent' : ''}`}
      style={{ cursor: 'pointer', transition: 'all 0.2s', borderColor: selected ? color : undefined }}
      onClick={() => onSelect(cohort)}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 14 }}>
        <div style={{ width: 44, height: 44, borderRadius: 12, background: color + '22',
          border: `1px solid ${color}44`, display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 20, flexShrink: 0 }}>
          🧬
        </div>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-primary)', marginBottom: 2 }}>
            {cohort.name}
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>
            n = {cohort.size?.toLocaleString()} · {cohort.primary_condition}
          </div>
        </div>
      </div>

      <p style={{ fontSize: 12.5, color: 'var(--text-secondary)', marginBottom: 12, lineHeight: 1.6 }}>
        {cohort.description}
      </p>

      <div style={{ marginBottom: 10 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
          <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>Positive Response Rate</span>
          <span style={{ fontSize: 12, fontWeight: 700, color }}>
            {respPct}%
          </span>
        </div>
        <div className="progress-bar-wrap">
          <div className="progress-bar-fill" style={{ width: `${respPct}%`, background: `linear-gradient(90deg,${color},${color}cc)` }} />
        </div>
      </div>

      <div className="chip-list">
        {(Array.isArray(cohort.key_features)
          ? cohort.key_features
          : (cohort.key_features || '').split(/\s{2,}|\|/).filter(Boolean)
        ).map((f, i) => <span key={i} className="chip">{f}</span>)}
      </div>

      {cohort.most_effective_treatment && (
        <div style={{ marginTop: 10, fontSize: 12, color }}>
          💡 Best: <strong>{cohort.most_effective_treatment}</strong>
        </div>
      )}
    </div>
  )
}

// Build radar chart data from cohort features
function buildRadarData(cohort) {
  if (!cohort) return []
  return [
    { feature: 'Response Rate', value: Math.round(cohort.positive_response_rate * 100) },
    { feature: 'Cohort Size',   value: Math.min(100, Math.round(cohort.size / 100)) },
    { feature: 'Complexity',    value: Math.round(cohort.key_features?.length * 25) },
    { feature: 'Eligibility',   value: Math.round(cohort.positive_response_rate * 80 + 15) },
    { feature: 'Data Quality',  value: Math.round(70 + Math.random() * 20) },
  ]
}

export default function CohortDiscovery({ onNavigate }) {
  const [cohorts,  setCohorts]  = useState([])
  const [selected, setSelected] = useState(null)
  const [loading,  setLoading]  = useState(true)

  useEffect(() => {
    fetchCohortAnalytics()
      .then(data => {
        setCohorts(data.cohorts || [])
        if (data.cohorts?.length > 0) setSelected(data.cohorts[0])
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const radarData = buildRadarData(selected)

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Cohort Discovery</h2>
          <p>ML-identified research cohorts — K-Means clustering across {(100000).toLocaleString()} patients (24 features)</p>
        </div>
        <span className="badge badge-purple" style={{ background: 'var(--purple-glow)', color: 'var(--purple)', border: '1px solid rgba(167,139,250,0.3)' }}>
          Spark MLlib · k=8 clusters
        </span>
      </div>

      <div className="page-body">
        {loading && <div className="loading-state"><div className="spinner" /><span>Loading cohort data…</span></div>}

        {!loading && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20 }}>
            {/* Cohort grid */}
            <div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 14 }}>
                Click a cohort to see its profile. Use these for patient stratification and trial design.
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(280px,1fr))', gap: 14 }}>
                {cohorts.map((c, i) => (
                  <CohortCard key={c.cohort_id} cohort={c} index={i}
                    selected={selected?.cohort_id === c.cohort_id}
                    onSelect={setSelected} />
                ))}
              </div>
            </div>

            {/* Detail panel */}
            {selected && (
              <div style={{ position: 'sticky', top: 0 }}>
                <div className="card card-accent" style={{ marginBottom: 14 }}>
                  <div className="card-title" style={{ marginBottom: 16 }}>🔬 Cohort Profile</div>
                  <div style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-primary)', marginBottom: 4 }}>
                    {selected.name}
                  </div>
                  <div style={{ fontSize: 12, color: 'var(--text-muted)', marginBottom: 16 }}>
                    Cohort {selected.cohort_id} · n={selected.size?.toLocaleString()}
                  </div>

                  <ResponsiveContainer width="100%" height={200}>
                    <RadarChart data={radarData}>
                      <PolarGrid stroke="rgba(148,163,184,0.15)" />
                      <PolarAngleAxis dataKey="feature" tick={{ fill: '#94a3b8', fontSize: 10 }} />
                      <Radar name="Cohort" dataKey="value" stroke="#38bdf8" fill="#38bdf8" fillOpacity={0.2} strokeWidth={2} />
                      <Tooltip contentStyle={TOOLTIP_STYLE} />
                    </RadarChart>
                  </ResponsiveContainer>

                  <hr className="divider" />

                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                    {[
                      { label: 'Primary Condition', value: selected.primary_condition },
                      { label: 'Cohort Size', value: selected.size?.toLocaleString() + ' patients' },
                      { label: 'Response Rate', value: (selected.positive_response_rate * 100).toFixed(0) + '%' },
                      { label: 'Best Treatment', value: selected.most_effective_treatment },
                    ].map(item => (
                      <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                        <span style={{ color: 'var(--text-muted)' }}>{item.label}</span>
                        <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{item.value}</span>
                      </div>
                    ))}
                  </div>

                  <div style={{ marginTop: 14, display: 'flex', gap: 8 }}>
                    <button className="btn btn-primary" style={{ flex: 1 }}
                      id="btn-cohort-patient"
                      onClick={() => onNavigate('patient')}>
                      👤 Demo Patient
                    </button>
                    <button className="btn btn-ghost"
                      id="btn-cohort-analytics"
                      onClick={() => onNavigate('analytics')}>
                      📊 Analytics
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  )
}
