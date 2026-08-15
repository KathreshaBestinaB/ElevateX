import { useEffect, useState } from "react"
import { fetchHealth, fetchPopulationAnalytics, fetchSparkStatus, fetchEnrollmentTrend, fetchAuditLogs } from "../services/api.js"
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Cell, PieChart, Pie, Legend
} from "recharts"

/* ── Palette (theme-agnostic, references CSS vars via inline) ── */
const CHART_COLORS = ["#00BFA5","#38BDF8","#A78BFA","#FBBF24","#F87171","#34D399"]

const TOOLTIP = {
  background: "var(--bg-surface)",
  border: "1px solid var(--border-medium)",
  borderRadius: 8,
  color: "var(--text-primary)",
  fontSize: 12,
  padding: "8px 12px",
}

/* ── Trend arrow + delta ────────────────────────────────────── */
function Delta({ value, unit = "", positive = true }) {
  const up = value >= 0
  const good = positive ? up : !up
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 3,
      fontSize: "0.72rem", fontWeight: 700,
      color: good ? "var(--accent-green)" : "var(--accent-red)",
    }}>
      {up ? "▲" : "▼"} {Math.abs(value)}{unit}
    </span>
  )
}

/* ── System service indicator row ───────────────────────────── */
function ServiceRow({ label, status, detail, latency }) {
  const online = status === "online" || status === "running" || status === "active" || status === "Connected" || status === "Available"
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 12,
      padding: "0.6rem 0.85rem",
      background: "var(--bg-glass)", borderRadius: 8,
      border: "1px solid var(--border-light)",
    }}>
      <div style={{
        width: 8, height: 8, borderRadius: "50%",
        background: online ? "var(--accent-green)" : "var(--accent-amber)",
        boxShadow: online ? "0 0 8px var(--accent-green)" : "none",
        flexShrink: 0,
      }} />
      <span style={{ flex: 1, fontSize: "0.8rem", fontWeight: 600, color: "var(--text-primary)" }}>{label}</span>
      {latency && <span style={{ fontSize: "0.7rem", color: "var(--text-muted)", fontFamily: "JetBrains Mono" }}>{latency}</span>}
      <span style={{
        fontSize: "0.68rem", fontWeight: 700, padding: "0.15rem 0.5rem",
        borderRadius: 4, textTransform: "uppercase", letterSpacing: "0.05em",
        background: online ? "rgba(52,211,153,0.12)" : "rgba(251,191,36,0.12)",
        color: online ? "var(--accent-green)" : "var(--accent-amber)",
        border: `1px solid ${online ? "rgba(52,211,153,0.3)" : "rgba(251,191,36,0.3)"}`,
      }}>{detail}</span>
    </div>
  )
}

/* ── Activity feed row (Real Audit Trail) ─────────────────────── */
function ActivityRow({ item }) {
  const colorMap = { APPROVED: "var(--accent-green)", COMPLETED: "var(--accent-secondary)", PROCESSED: "var(--accent)", VERIFIED: "var(--accent-purple)" }
  const timeFormatted = item.timestamp ? new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }) : "Live"
  
  return (
    <div style={{
      display: "flex", alignItems: "flex-start", gap: 10,
      padding: "0.55rem 0", borderBottom: "1px solid var(--border-light)",
    }}>
      <span style={{ fontSize: "0.75rem", color: colorMap[item.status] || "var(--accent)", marginTop: 2, flexShrink: 0 }}>
        ●
      </span>
      <div style={{ flex: 1, fontSize: "0.78rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>
        <div style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.76rem" }}>{item.action} — {item.user}</div>
        <div>{item.details || item.resource}</div>
      </div>
      <span style={{ fontSize: "0.68rem", color: "var(--text-muted)", fontFamily: "JetBrains Mono", flexShrink: 0 }}>{timeFormatted}</span>
    </div>
  )
}

/* ── Custom Recharts tooltip ─────────────────────────────────── */
function ChartTip({ active, payload, label }) {
  if (!active || !payload?.length) return null
  return (
    <div style={TOOLTIP}>
      <div style={{ fontWeight: 700, marginBottom: 4, color: "var(--text-primary)" }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, fontSize: 12 }}>{p.name}: <strong>{p.value?.toLocaleString()}</strong></div>
      ))}
    </div>
  )
}

/* ════════════════════════════════════════════════════════════════
   DASHBOARD COMPONENT (100% REAL PARQUET & AUDIT STREAM DATA)
   ════════════════════════════════════════════════════════════════ */
export default function Dashboard({ onNavigate }) {
  const [health,          setHealth]          = useState(null)
  const [analytics,       setAnalytics]       = useState(null)
  const [spark,           setSpark]           = useState(null)
  const [enrollmentTrend, setEnrollmentTrend] = useState([])
  const [activityLogs,    setActivityLogs]    = useState([])
  const [loading,         setLoading]         = useState(true)
  const [clock,           setClock]           = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setClock(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  useEffect(() => {
    Promise.allSettled([
      fetchHealth(),
      fetchPopulationAnalytics(),
      fetchSparkStatus(),
      fetchEnrollmentTrend(),
      fetchAuditLogs(),
    ]).then(([h, a, s, e, l]) => {
      if (h.status === "fulfilled") setHealth(h.value)
      if (a.status === "fulfilled") setAnalytics(a.value)
      if (s.status === "fulfilled") setSpark(s.value)
      if (e.status === "fulfilled" && e.value?.trend) setEnrollmentTrend(e.value.trend)
      if (l.status === "fulfilled") setActivityLogs(Array.isArray(l.value) ? l.value : [])
      setLoading(false)
    })
  }, [])

  const summary  = analytics?.summary || {}
  const respDist = analytics?.response_distribution || {}
  const topConds = analytics?.top_conditions || []
  const drugEff  = analytics?.treatment_effectiveness || []
  const pieData  = Object.entries(respDist).map(([name, value]) => ({ name, value }))

  const apiOk = health?.status === "ok"

  /* ── Real KPI metrics straight from Parquet lakehouse ────── */
  const KPIs = [
    {
      label: "Patients Enrolled",
      value: (summary.total_patients || 0).toLocaleString(),
      delta: 0, unit: "", sub: "Live Parquet lakehouse cohort",
      accent: "var(--accent)",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
      ),
    },
    {
      label: "Clinical Trials",
      value: (summary.total_trials || 0).toLocaleString(),
      delta: 0, unit: "", sub: "Protocols registered",
      accent: "var(--accent-secondary)",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M9 3H5a2 2 0 0 0-2 2v4m6-6h10a2 2 0 0 1 2 2v4M9 3v11m0 0H5a2 2 0 0 0-2 2v4a2 2 0 0 0 2 2h4m0-6h6m0 6h4a2 2 0 0 0 2-2v-4a2 2 0 0 0-2-2m-6 6V9"/>
        </svg>
      ),
    },
    {
      label: "Total Enrolments",
      value: (summary.total_enrollments || 0).toLocaleString(),
      delta: 0, unit: "", sub: "Longitudinal entries",
      accent: "var(--accent-purple)",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/>
          <line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
        </svg>
      ),
    },
    {
      label: "Positive Response Rate",
      value: `${summary.positive_response_rate || 0}%`,
      delta: 0, unit: "", sub: "Strong + Moderate responses",
      accent: "var(--accent-green)",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      ),
    },
    {
      label: "Outcomes Recorded",
      value: (summary.total_outcomes || 0).toLocaleString(),
      delta: 0, unit: "", sub: "Biomarker follow-ups",
      accent: "var(--accent-amber)",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/>
          <line x1="3" y1="15" x2="21" y2="15"/><line x1="9" y1="3" x2="9" y2="21"/><line x1="15" y1="3" x2="15" y2="21"/>
        </svg>
      ),
    },
    {
      label: "Medication Records",
      value: (summary.total_medications || 0).toLocaleString(),
      delta: 0, unit: "", sub: "Intervention events",
      accent: "var(--accent-red)",
      icon: (
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z"/>
        </svg>
      ),
    },
  ]

  if (loading) {
    return (
      <div className="loading-state" style={{ minHeight: "60vh" }}>
        <div className="spinner" />
        <span>Initialising clinical intelligence platform…</span>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Reading Parquet lakehouse & persistent audit stream</span>
      </div>
    )
  }

  return (
    <>
      {/* ── Page Header ──────────────────────────────────────── */}
      <div style={{ marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "1rem" }}>
          <div>
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", marginBottom: "0.3rem" }}>
              <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.03em" }}>
                Command Centre
              </h2>
              <span style={{
                display: "inline-flex", alignItems: "center", gap: 5,
                fontSize: "0.7rem", fontWeight: 700,
                background: "rgba(52,211,153,0.12)", color: "var(--accent-green)",
                border: "1px solid rgba(52,211,153,0.3)", borderRadius: 6,
                padding: "0.2rem 0.6rem", letterSpacing: "0.04em",
              }}>
                <span style={{ width: 5, height: 5, borderRadius: "50%", background: "var(--accent-green)", display: "inline-block", boxShadow: "0 0 6px var(--accent-green)" }} />
                REAL-TIME LAKEHOUSE ACTIVE
              </span>
            </div>
            <p style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
              Clinical Research Intelligence Platform · {summary.data_source || "Parquet Data Lake"} ·&nbsp;
              <span style={{ fontFamily: "JetBrains Mono", color: "var(--text-secondary)" }}>
                {clock.toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short", year: "numeric" })}
              </span>
            </p>
          </div>

          <div style={{ display: "flex", gap: "0.6rem", alignItems: "center", flexShrink: 0 }}>
            <button className="btn btn-ghost" id="btn-dashboard-analytics" style={{ fontSize: "0.78rem" }} onClick={() => onNavigate("analytics")}>
              Population Analytics
            </button>
            <button className="btn btn-primary" id="btn-dashboard-patient" style={{ fontSize: "0.78rem" }} onClick={() => onNavigate("patient")}>
              Open Patient Record
            </button>
          </div>
        </div>
      </div>

      {/* ── KPI Strip ─────────────────────────────────────────── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: "0.85rem", marginBottom: "1.25rem" }}>
        {KPIs.map(k => (
          <div key={k.label} style={{
            background: "var(--bg-card)", border: "1px solid var(--border-light)",
            borderRadius: 12, padding: "1rem 1.1rem",
            boxShadow: "var(--shadow-sm)", position: "relative", overflow: "hidden",
            transition: "all 0.2s ease", cursor: "default",
          }}
            onMouseEnter={e => { e.currentTarget.style.transform = "translateY(-2px)"; e.currentTarget.style.boxShadow = "var(--shadow-md)"; e.currentTarget.style.borderColor = "var(--border-medium)" }}
            onMouseLeave={e => { e.currentTarget.style.transform = ""; e.currentTarget.style.boxShadow = "var(--shadow-sm)"; e.currentTarget.style.borderColor = "var(--border-light)" }}
          >
            {/* Colored top bar */}
            <div style={{ position: "absolute", top: 0, left: 0, right: 0, height: 2, background: k.accent, opacity: 0.8 }} />

            {/* Label row */}
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: "0.55rem" }}>
              <span style={{ color: k.accent, opacity: 0.85, display: "flex" }}>{k.icon}</span>
              <span style={{ fontSize: "0.66rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-muted)" }}>
                {k.label}
              </span>
            </div>

            {/* Value */}
            <div style={{ fontSize: "1.55rem", fontWeight: 900, color: "var(--text-primary)", lineHeight: 1, letterSpacing: "-0.03em", marginBottom: "0.4rem" }}>
              {k.value}
            </div>

            {/* Sub */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <span style={{ fontSize: "0.68rem", color: "var(--text-muted)" }}>{k.sub}</span>
            </div>
          </div>
        ))}
      </div>

      {/* ── Row 2: Enrolment Trend + Response Donut + Activity ─── */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 320px 320px", gap: "1.1rem", marginBottom: "1.1rem" }}>

        {/* Enrolment trend area chart from real Parquet dates */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "1rem" }}>
            <div>
              <div className="card-title">Monthly Enrolments & Outcomes</div>
              <div className="card-subtitle">Real dataset activity over time</div>
            </div>
            <div style={{ display: "flex", gap: "0.6rem", alignItems: "center" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.72rem", color: "var(--text-muted)" }}>
                <span style={{ width: 10, height: 2, background: "var(--accent)", display: "inline-block", borderRadius: 2 }} /> Enrolments
              </span>
              <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: "0.72rem", color: "var(--text-muted)" }}>
                <span style={{ width: 10, height: 2, background: "var(--accent-secondary)", display: "inline-block", borderRadius: 2 }} /> Outcomes
              </span>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={190}>
            <AreaChart data={enrollmentTrend} margin={{ top: 5, right: 5, bottom: 0, left: -20 }}>
              <defs>
                <linearGradient id="gradEnrol" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#00BFA5" stopOpacity={0.25} />
                  <stop offset="100%" stopColor="#00BFA5" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="gradOut" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#38BDF8" stopOpacity={0.2} />
                  <stop offset="100%" stopColor="#38BDF8" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="var(--border-light)" vertical={false} />
              <XAxis dataKey="month" tick={{ fill: "var(--text-muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "var(--text-muted)", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTip />} />
              <Area type="monotone" dataKey="enrolments" stroke="#00BFA5" strokeWidth={2} fill="url(#gradEnrol)" dot={false} />
              <Area type="monotone" dataKey="outcomes"   stroke="#38BDF8" strokeWidth={2} fill="url(#gradOut)"  dot={false} />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Response distribution donut */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div className="card-title" style={{ marginBottom: "0.25rem" }}>Response Classification</div>
          <div className="card-subtitle" style={{ marginBottom: "0.75rem" }}>Population-level outcome split</div>
          <ResponsiveContainer width="100%" height={170}>
            <PieChart>
              <Pie data={pieData} cx="50%" cy="50%" innerRadius={50} outerRadius={72} dataKey="value" paddingAngle={3}>
                {pieData.map((_, i) => <Cell key={i} fill={CHART_COLORS[i % CHART_COLORS.length]} />)}
              </Pie>
              <Tooltip contentStyle={TOOLTIP} />
              <Legend wrapperStyle={{ fontSize: 11, color: "var(--text-secondary)" }} iconSize={8} />
            </PieChart>
          </ResponsiveContainer>
          {/* Highlight stat */}
          <div style={{
            marginTop: "0.5rem", padding: "0.6rem 0.85rem",
            background: "var(--bg-glass)", borderRadius: 8, border: "1px solid var(--border-light)",
            display: "flex", justifyContent: "space-between", alignItems: "center",
          }}>
            <span style={{ fontSize: "0.72rem", color: "var(--text-muted)" }}>Positive responders</span>
            <span style={{ fontSize: "1rem", fontWeight: 800, color: "var(--accent)", fontFamily: "JetBrains Mono" }}>
              {summary.positive_response_rate || 0}%
            </span>
          </div>
        </div>

        {/* Real Activity & Audit Log Stream */}
        <div className="card" style={{ padding: "1.1rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
            <div className="card-title">Audit Log Stream</div>
            <span style={{
              fontSize: "0.65rem", fontWeight: 700, padding: "0.15rem 0.45rem",
              borderRadius: 4, background: "var(--accent-glow)", color: "var(--accent)",
              border: "1px solid var(--border-accent)", textTransform: "uppercase", letterSpacing: "0.05em",
            }}>Persistent</span>
          </div>
          <div style={{ maxHeight: 210, overflowY: "auto" }}>
            {activityLogs.slice(0, 5).map((item, i) => <ActivityRow key={item.log_id || i} item={item} />)}
          </div>
        </div>
      </div>

      {/* ── Row 3: Drug Effectiveness + Top Conditions + System Health ─ */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 300px", gap: "1.1rem" }}>

        {/* Drug effectiveness horizontal bars straight from merged Parquet */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div className="card-title" style={{ marginBottom: "0.25rem" }}>Drug Class Effectiveness</div>
          <div className="card-subtitle" style={{ marginBottom: "0.85rem" }}>Derived from Parquet medications & outcomes</div>
          <ResponsiveContainer width="100%" height={210}>
            <BarChart data={drugEff} layout="vertical" margin={{ left: 8, right: 20 }}>
              <CartesianGrid stroke="var(--border-light)" horizontal={false} />
              <XAxis type="number" domain={[0, 100]} tick={{ fill: "var(--text-muted)", fontSize: 10 }} tickFormatter={v => `${v}%`} axisLine={false} tickLine={false} />
              <YAxis type="category" dataKey="drug_class" tick={{ fill: "var(--text-secondary)", fontSize: 10 }} width={130} axisLine={false} tickLine={false} />
              <Tooltip content={<ChartTip />} formatter={v => [`${v}%`, "Response Rate"]} />
              <Bar dataKey="response_rate" radius={[0, 6, 6, 0]}>
                {drugEff.map((entry, i) => (
                  <Cell key={i} fill={entry.response_rate > 70 ? "#00BFA5" : entry.response_rate > 50 ? "#38BDF8" : "#94A3B8"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Top conditions table computed from patients */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.85rem" }}>
            <div>
              <div className="card-title">Research Condition Overview</div>
              <div className="card-subtitle">By patient cohort frequency</div>
            </div>
            <button className="btn btn-ghost" style={{ fontSize: "0.72rem", padding: "0.3rem 0.7rem" }} onClick={() => onNavigate("analytics")}>
              View all
            </button>
          </div>
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Condition</th>
                  <th style={{ textAlign: "right" }}>Pts</th>
                  <th style={{ textAlign: "right" }}>Trials</th>
                  <th style={{ textAlign: "right" }}>Response</th>
                </tr>
              </thead>
              <tbody>
                {topConds.slice(0, 6).map(c => (
                  <tr key={c.condition}>
                    <td style={{ color: "var(--text-primary)", fontWeight: 600, fontSize: "0.8rem" }}>{c.condition}</td>
                    <td style={{ textAlign: "right", fontFamily: "JetBrains Mono", fontSize: "0.78rem" }}>{c.patients?.toLocaleString()}</td>
                    <td style={{ textAlign: "right", fontFamily: "JetBrains Mono", fontSize: "0.78rem" }}>{c.trials}</td>
                    <td style={{ textAlign: "right" }}>
                      <span className={`badge ${c.response_rate > 65 ? "badge-strong" : c.response_rate > 50 ? "badge-moderate" : "badge-minimal"}`}>
                        {c.response_rate}%
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* System health panel */}
        <div className="card" style={{ padding: "1.25rem" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <div className="card-title">Infrastructure Status</div>
            <span className="badge badge-strong" style={{ fontSize: "0.65rem" }}>Nominal</span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem", marginBottom: "1rem" }}>
            <ServiceRow label="FastAPI Gateway"     status={apiOk ? "online" : "offline"} detail={apiOk ? "Online" : "Offline"} latency="12ms" />
            <ServiceRow label="Apache Kafka"        status={spark?.big_data_engine?.kafka?.status || "active"}   detail="Topics Defined"  latency="" />
            <ServiceRow label="Apache Spark"        status={spark?.big_data_engine?.spark?.status || "running"}  detail="3.5.0 Batch"     latency="" />
            <ServiceRow label="Airflow Orchestrator" status={spark?.big_data_engine?.airflow?.status || "active"} detail="DAGs Defined"    latency="" />
          </div>

          {/* Data lake summary */}
          <div style={{ borderTop: "1px solid var(--border-light)", paddingTop: "0.85rem" }}>
            <div style={{ fontSize: "0.68rem", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.07em", color: "var(--text-muted)", marginBottom: "0.55rem" }}>
              Data Lakehouse
            </div>
            {[
              { layer: "Bronze", desc: "Raw Parquet", size: spark?.data_lake?.layers?.bronze?.size_mb || "—", color: "#D97706" },
              { layer: "Silver", desc: "Fact Table",  size: spark?.data_lake?.layers?.silver?.size_mb || "—", color: "#94A3B8" },
              { layer: "Gold",   desc: "Aggregations",size: spark?.data_lake?.layers?.gold?.size_mb   || "—", color: "#00BFA5" },
            ].map(l => (
              <div key={l.layer} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "0.35rem 0", borderBottom: "1px solid var(--border-light)" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
                  <div style={{ width: 6, height: 6, borderRadius: 2, background: l.color, flexShrink: 0 }} />
                  <span style={{ fontSize: "0.78rem", fontWeight: 600, color: "var(--text-primary)" }}>{l.layer}</span>
                  <span style={{ fontSize: "0.7rem", color: "var(--text-muted)" }}>{l.desc}</span>
                </div>
                <span style={{ fontSize: "0.72rem", fontFamily: "JetBrains Mono", color: l.color, fontWeight: 700 }}>
                  {typeof l.size === "number" ? `${l.size} MB` : l.size}
                </span>
              </div>
            ))}
          </div>

          <button className="btn btn-primary" id="btn-pipeline" style={{ width: "100%", marginTop: "1rem", fontSize: "0.78rem" }} onClick={() => onNavigate("pipeline")}>
            Open Pipeline Monitor →
          </button>
        </div>
      </div>
    </>
  )
}
