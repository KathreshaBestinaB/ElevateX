import { useEffect, useState } from 'react'
import { fetchHealth, fetchPopulationAnalytics, fetchSparkStatus } from '../services/api.js'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'

const PIE_COLORS = ['#34d399', '#38bdf8', '#fbbf24', '#f87171', '#ef4444', '#94a3b8']

const CUSTOM_TOOLTIP_STYLE = {
  background: 'rgba(13,22,38,0.95)',
  border: '1px solid rgba(148,163,184,0.15)',
  borderRadius: '8px',
  color: '#f0f6ff',
  fontSize: '12px',
  padding: '8px 12px',
}

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={CUSTOM_TOOLTIP_STYLE}>
      <div style={{ fontWeight: 700, marginBottom: 4 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color }}>{p.name}: {p.value?.toLocaleString()}</div>
      ))}
    </div>
  )
}

export default function Dashboard({ onNavigate }) {
  const [health,    setHealth]    = useState(null)
  const [analytics, setAnalytics] = useState(null)
  const [spark,     setSpark]     = useState(null)
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    Promise.allSettled([
      fetchHealth(),
      fetchPopulationAnalytics(),
      fetchSparkStatus(),
    ]).then(([h, a, s]) => {
      if (h.status === 'fulfilled') setHealth(h.value)
      if (a.status === 'fulfilled') setAnalytics(a.value)
      if (s.status === 'fulfilled') setSpark(s.value)
      setLoading(false)
    })
  }, [])

  const summary = analytics?.summary || {}
  const respDist = analytics?.response_distribution || {}
  const pieData  = Object.entries(respDist).map(([name, value]) => ({ name, value }))
  const topConds = analytics?.top_conditions || []
  const drugEffectiveness = analytics?.treatment_effectiveness || []

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Command Centre</h2>
          <p>Real-time clinical trial intelligence across the synthetic research cohort</p>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {health && (
            <span className={`badge ${health.status === 'ok' ? 'badge-strong' : 'badge-no-response'}`}>
              ● API {health.status === 'ok' ? 'Online' : 'Offline'}
            </span>
          )}
          <span className="badge badge-accent">⚡ Live</span>
        </div>
      </div>

      <div className="page-body">
        {loading ? (
          <div className="loading-state">
            <div className="spinner" />
            <span>Loading platform analytics…</span>
          </div>
        ) : (
          <>
            {/* KPI row */}
            <div className="kpi-grid">
              {[
                { label: 'Patients', value: (summary.total_patients || 0).toLocaleString(), sub: 'Synthetic cohort', icon: '👤' },
                { label: 'Clinical Trials', value: (summary.total_trials || 0).toLocaleString(), sub: 'Active & completed', icon: '🧪' },
                { label: 'Enrollments', value: (summary.total_enrollments || 0).toLocaleString(), sub: 'Total participations', icon: '📋' },
                { label: 'Outcomes Recorded', value: (summary.total_outcomes || 0).toLocaleString(), sub: 'With response data', icon: '📈' },
                { label: 'Positive Response Rate', value: `${summary.positive_response_rate || 0}%`, sub: 'Across all trials', icon: '✅' },
                { label: 'Medication Records', value: Number(summary.total_medications || 0).toLocaleString(), sub: 'Intervention events', icon: '💊' },
              ].map(k => (
                <div key={k.label} className="kpi-card">
                  <div className="kpi-label">{k.icon} {k.label}</div>
                  <div className="kpi-value">{k.value}</div>
                  <div className="kpi-sub">{k.sub}</div>
                </div>
              ))}
            </div>

            {/* Charts row */}
            <div className="grid-2" style={{ marginBottom: 20 }}>
              {/* Response distribution donut */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">📊 Treatment Response Distribution</div>
                    <div className="card-subtitle">Population-level outcome classification</div>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={90}
                      dataKey="value" nameKey="name" paddingAngle={3}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={CUSTOM_TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              {/* Treatment effectiveness */}
              <div className="card">
                <div className="card-header">
                  <div>
                    <div className="card-title">💊 Treatment Effectiveness by Drug Class</div>
                    <div className="card-subtitle">Positive response rate across major classes</div>
                  </div>
                </div>
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={drugEffectiveness} layout="vertical" margin={{ left: 30, right: 20 }}>
                    <XAxis type="number" domain={[0, 100]} tick={{ fill: '#475569', fontSize: 11 }}
                      tickFormatter={v => `${v}%`} />
                    <YAxis type="category" dataKey="drug_class" tick={{ fill: '#94a3b8', fontSize: 10 }}
                      width={120} />
                    <Tooltip content={<CustomTooltip />} formatter={(v) => [`${v}%`, 'Response Rate']} />
                    <Bar dataKey="response_rate" fill="url(#barGrad)" radius={[0, 4, 4, 0]} />
                    <defs>
                      <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#0ea5e9" />
                        <stop offset="100%" stopColor="#2dd4bf" />
                      </linearGradient>
                    </defs>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Top conditions table + big data status */}
            <div className="grid-2">
              <div className="card">
                <div className="card-header">
                  <div className="card-title">🏥 Top Conditions in Research</div>
                </div>
                <div className="table-wrap">
                  <table>
                    <thead>
                      <tr>
                        <th>Condition</th>
                        <th>Patients</th>
                        <th>Trials</th>
                        <th>Resp. Rate</th>
                      </tr>
                    </thead>
                    <tbody>
                      {topConds.map(c => (
                        <tr key={c.condition}>
                          <td style={{ color: '#f0f6ff', fontWeight: 500 }}>{c.condition}</td>
                          <td>{c.patients?.toLocaleString()}</td>
                          <td>{c.trials?.toLocaleString()}</td>
                          <td>
                            <span className={`badge ${c.response_rate > 60 ? 'badge-strong' : c.response_rate > 45 ? 'badge-moderate' : 'badge-minimal'}`}>
                              {c.response_rate}%
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Big data stack status */}
              <div className="card card-accent pulse-glow">
                <div className="card-header">
                  <div className="card-title">⚡ Big Data Stack</div>
                  <span className="badge badge-teal">Demo Mode</span>
                </div>
                {spark && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                    {[
                      { label: 'Apache Spark', status: spark.big_data_engine?.spark?.status, detail: spark.big_data_engine?.spark?.version },
                      { label: 'Apache Kafka', status: spark.big_data_engine?.kafka?.status, detail: `${spark.big_data_engine?.kafka?.topics?.length} topics` },
                      { label: 'Apache Airflow', status: spark.big_data_engine?.airflow?.status, detail: `${spark.big_data_engine?.airflow?.dags?.length} DAGs` },
                    ].map(item => (
                      <div key={item.label} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 8 }}>
                        <div>
                          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>{item.label}</div>
                          <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{item.detail}</div>
                        </div>
                        <span className="badge badge-neutral">{item.status}</span>
                      </div>
                    ))}
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--bg-glass)', borderRadius: 8 }}>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' }}>Data Lake</div>
                        <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>bronze / silver / gold</div>
                      </div>
                      <span className="badge badge-neutral">{spark.data_lake?.total_size_mb?.toFixed(1)} MB</span>
                    </div>
                    <div style={{ marginTop: 4 }}>
                      {[
                        { label: 'Patients Processed', value: (spark.last_processed?.patients || 0).toLocaleString() },
                        { label: 'Clinical Events',    value: (spark.last_processed?.clinical_events || 0).toLocaleString() },
                        { label: 'Medication Records', value: (spark.last_processed?.medication_records || 0).toLocaleString() },
                      ].map(r => (
                        <div key={r.label} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '4px 0', borderBottom: '1px solid var(--border)' }}>
                          <span style={{ color: 'var(--text-secondary)' }}>{r.label}</span>
                          <span style={{ color: 'var(--accent)', fontFamily: 'JetBrains Mono', fontWeight: 600 }}>{r.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div style={{ marginTop: 16, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  <button className="btn btn-primary" id="btn-dashboard-patient" onClick={() => onNavigate('patient')}>
                    👤 View Demo Patient
                  </button>
                  <button className="btn btn-ghost" id="btn-dashboard-analytics" onClick={() => onNavigate('analytics')}>
                    📊 Full Analytics
                  </button>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </>
  )
}
