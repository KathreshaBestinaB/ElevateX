import { useEffect, useState } from 'react'
import { fetchPopulationAnalytics, fetchSparkStatus, fetchEnrollmentTrend } from '../services/api.js'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  PieChart, Pie, Cell, Legend, AreaChart, Area,
} from 'recharts'

const TOOLTIP_STYLE = {
  background: 'rgba(13,22,38,0.95)',
  border: '1px solid rgba(148,163,184,0.15)',
  borderRadius: 8,
  color: '#f0f6ff',
  fontSize: 12,
  padding: '8px 12px',
}

const PIE_COLORS = ['#34d399', '#38bdf8', '#fbbf24', '#f87171', '#ef4444', '#94a3b8']

const PHASE_DATA = [
  { phase: 'Phase 1', pct: 8.2,  count: 820 },
  { phase: 'Phase 2', pct: 22.5, count: 2250 },
  { phase: 'Phase 3', pct: 51.3, count: 5130 },
  { phase: 'Phase 4', pct: 18.0, count: 1800 },
]

export default function PopulationAnalytics({ onNavigate }) {
  const [analytics, setAnalytics] = useState(null)
  const [spark,     setSpark]     = useState(null)
  const [trendData, setTrendData] = useState([])
  const [tab,       setTab]       = useState('overview')
  const [loading,   setLoading]   = useState(true)

  useEffect(() => {
    Promise.allSettled([fetchPopulationAnalytics(), fetchSparkStatus(), fetchEnrollmentTrend()])
      .then(([a, s, t]) => {
        if (a.status === 'fulfilled') setAnalytics(a.value)
        if (s.status === 'fulfilled') setSpark(s.value)
        if (t.status === 'fulfilled') setTrendData(t.value?.trend || [])
        setLoading(false)
      })
  }, [])

  const summary   = analytics?.summary || {}
  const respDist  = analytics?.response_distribution || {}
  const topConds  = analytics?.top_conditions || []
  const drugEff   = analytics?.treatment_effectiveness || []

  const pieData = Object.entries(respDist).map(([name, value]) => ({ name, value }))

  return (
    <>
      <div className="page-header">
        <div className="page-header-left">
          <h2>Population Analytics</h2>
          <p>Aggregate clinical research patterns across {(summary.total_patients || 0).toLocaleString()} patients — powered by synthetic Spark pipeline</p>
        </div>
        <div className="tab-bar">
          {['overview', 'spark', 'conditions'].map(t => (
            <button key={t} className={`tab-btn${tab === t ? ' active' : ''}`} onClick={() => setTab(t)}>
              {t.charAt(0).toUpperCase() + t.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="page-body">
        {loading && <div className="loading-state"><div className="spinner" /><span>Loading population data…</span></div>}

        {!loading && tab === 'overview' && (
          <>
            {/* KPIs */}
            <div className="kpi-grid" style={{ marginBottom: 24 }}>
              {[
                { label: 'Total Patients',    value: (summary.total_patients || 0).toLocaleString(),    icon: '👤' },
                { label: 'Active Trials',     value: (summary.total_trials || 0).toLocaleString(),      icon: '🧪' },
                { label: 'Total Enrollments', value: (summary.total_enrollments || 0).toLocaleString(), icon: '📋' },
                { label: 'Outcomes Recorded', value: (summary.total_outcomes || 0).toLocaleString(),    icon: '📈' },
                { label: 'Positive Response', value: `${summary.positive_response_rate || 0}%`,         icon: '✅' },
              ].map(k => (
                <div key={k.label} className="kpi-card">
                  <div className="kpi-label">{k.icon} {k.label}</div>
                  <div className="kpi-value">{k.value}</div>
                </div>
              ))}
            </div>

            {/* Response distribution + trial phase */}
            <div className="grid-2" style={{ marginBottom: 24 }}>
              <div className="card">
                <div className="card-header">
                  <div className="card-title">📊 Response Distribution</div>
                </div>
                <ResponsiveContainer width="100%" height={240}>
                  <PieChart>
                    <Pie data={pieData} cx="50%" cy="50%" innerRadius={65} outerRadius={95}
                      dataKey="value" nameKey="name" paddingAngle={3}>
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Legend wrapperStyle={{ fontSize: 11, color: '#94a3b8' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">🔬 Enrollment by Phase</div>
                </div>
                <ResponsiveContainer width="100%" height={240}>
                  <BarChart data={PHASE_DATA}>
                    <CartesianGrid stroke="rgba(148,163,184,0.07)" vertical={false} />
                    <XAxis dataKey="phase" tick={{ fill: '#94a3b8', fontSize: 11 }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fill: '#475569', fontSize: 11 }} axisLine={false} tickLine={false} tickFormatter={v => `${v}%`} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => [`${v}%`, 'Share']} />
                    <Bar dataKey="pct" fill="url(#phaseGrad)" radius={[6, 6, 0, 0]} />
                    <defs>
                      <linearGradient id="phaseGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#a78bfa" />
                        <stop offset="100%" stopColor="#6366f1" />
                      </linearGradient>
                    </defs>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Enrollment trend + drug class */}
            <div className="grid-2" style={{ marginBottom: 24 }}>
              <div className="card">
                <div className="card-header">
                  <div className="card-title">📈 Enrollment Trend (24 months)</div>
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <AreaChart data={trendData}>
                    <defs>
                      <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#38bdf8" stopOpacity={0.3} />
                        <stop offset="100%" stopColor="#38bdf8" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid stroke="rgba(148,163,184,0.07)" vertical={false} />
                    <XAxis dataKey="month" tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} interval={3} />
                    <YAxis tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <Area type="monotone" dataKey="enrollments" stroke="#38bdf8" strokeWidth={2} fill="url(#areaGrad)" />
                    <Area type="monotone" dataKey="outcomes" stroke="#34d399" strokeWidth={2} fill="none" strokeDasharray="4 2" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>

              <div className="card">
                <div className="card-header">
                  <div className="card-title">💊 Drug Class Effectiveness</div>
                </div>
                <ResponsiveContainer width="100%" height={200}>
                  <BarChart data={drugEff} layout="vertical" margin={{ left: 20 }}>
                    <XAxis type="number" domain={[0, 100]} tick={{ fill: '#475569', fontSize: 10 }} tickFormatter={v => `${v}%`} />
                    <YAxis type="category" dataKey="drug_class" tick={{ fill: '#94a3b8', fontSize: 10 }} width={130} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} formatter={v => [`${v}%`, 'Response Rate']} />
                    <Bar dataKey="response_rate" fill="url(#drugGrad)" radius={[0, 4, 4, 0]} />
                    <defs>
                      <linearGradient id="drugGrad" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#0ea5e9" />
                        <stop offset="100%" stopColor="#2dd4bf" />
                      </linearGradient>
                    </defs>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </>
        )}

        {!loading && tab === 'spark' && spark && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card card-accent">
              <div className="card-title" style={{ marginBottom: 16 }}>⚡ Apache Spark Processing Status</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(200px,1fr))', gap: 12 }}>
                {Object.entries(spark.last_processed || {}).map(([k, v]) => (
                  <div key={k} style={{ background: 'var(--bg-glass)', borderRadius: 10, padding: 14 }}>
                    <div style={{ fontSize: 11, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: 6 }}>
                      {k.replace(/_/g, ' ')}
                    </div>
                    <div style={{ fontSize: 22, fontWeight: 800, color: 'var(--accent)', fontFamily: 'JetBrains Mono' }}>
                      {Number(v).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid-2">
              <div className="card">
                <div className="card-title" style={{ marginBottom: 14 }}>🗄 Data Lake Layers</div>
                {Object.entries(spark.data_lake?.layers || {}).map(([layer, info]) => (
                  <div key={layer} style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border)' }}>
                    <span style={{ fontWeight: 600, color: 'var(--text-primary)', textTransform: 'capitalize' }}>{layer}</span>
                    <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>{info.files} files · {info.size_mb} MB</span>
                  </div>
                ))}
              </div>

              <div className="card">
                <div className="card-title" style={{ marginBottom: 14 }}>📡 Kafka Topics</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                  {(spark.big_data_engine?.kafka?.topics || []).map(t => (
                    <div key={t} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px',
                      background: 'var(--bg-glass)', borderRadius: 6, fontSize: 12, fontFamily: 'JetBrains Mono' }}>
                      <span style={{ color: 'var(--teal)' }}>▶</span>
                      <span style={{ color: 'var(--text-secondary)' }}>{t}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="card">
              <div className="card-title" style={{ marginBottom: 14 }}>🔄 Airflow DAGs</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(240px,1fr))', gap: 8 }}>
                {(spark.big_data_engine?.airflow?.dags || []).map(dag => (
                  <div key={dag} style={{ background: 'var(--bg-glass)', borderRadius: 8, padding: '10px 14px',
                    display: 'flex', alignItems: 'center', gap: 10 }}>
                    <span style={{ color: 'var(--amber)', fontSize: 14 }}>🔄</span>
                    <span style={{ fontSize: 12, fontFamily: 'JetBrains Mono', color: 'var(--text-secondary)' }}>{dag}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {!loading && tab === 'conditions' && (
          <div className="card">
            <div className="card-title" style={{ marginBottom: 16 }}>🏥 Conditions Research Overview</div>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Condition</th>
                    <th>Patients</th>
                    <th>Trials</th>
                    <th>Response Rate</th>
                    <th>Success Rate Bar</th>
                  </tr>
                </thead>
                <tbody>
                  {topConds.map(c => (
                    <tr key={c.condition}>
                      <td style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{c.condition}</td>
                      <td>{c.patients?.toLocaleString()}</td>
                      <td>{c.trials?.toLocaleString()}</td>
                      <td>
                        <span className={`badge ${c.response_rate > 65 ? 'badge-strong' : c.response_rate > 50 ? 'badge-moderate' : 'badge-minimal'}`}>
                          {c.response_rate}%
                        </span>
                      </td>
                      <td style={{ width: 160 }}>
                        <div className="progress-bar-wrap">
                          <div className="progress-bar-fill" style={{
                            width: `${c.response_rate}%`,
                            background: `linear-gradient(90deg, #0ea5e9, #2dd4bf)`,
                          }} />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
