import { useState, useEffect } from 'react'

export default function Header({ 
  activePage, 
  patientId, 
  onSelectPatient, 
  theme, 
  onToggleTheme,
  onNavigate 
}) {
  const [searchQuery, setSearchQuery] = useState('')
  const [timeStr, setTimeStr] = useState('')

  useEffect(() => {
    const updateTime = () => {
      const now = new Date()
      setTimeStr(now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }))
    }
    updateTime()
    const timer = setInterval(updateTime, 1000)
    return () => clearInterval(timer)
  }, [])

  const PAGE_TITLES = {
    dashboard:   'Command Centre & Operational Overview',
    patient:     'Patient Post-Trial Intelligence (6 Questions)',
    matching:    'Clinical Trial Eligibility & Matching Engine',
    trials:      'Trial Protocol Explorer & Performance',
    similar:     'Similar Patient Cohort Search',
    analytics:   'Population-Scale Research Analytics',
    medications: 'Medication & Intervention Effectiveness',
    cohorts:     'Phenotypic Research Cohorts & Clustering',
    assistant:   'AI Clinical Research Assistant',
    documents:   'Document Intelligence & NLP Studio',
    pipeline:    'Spark Lakehouse & Kafka Streaming Monitor',
    compliance:  'Compliance, Data Quality & Audit Trail',
  }

  return (
    <header className="app-header">
      <div className="header-left">
        <div className="header-breadcrumb">
          <span className="breadcrumb-root">TrialForge</span>
          <span className="breadcrumb-sep">/</span>
          <span className="breadcrumb-current">{PAGE_TITLES[activePage] || 'Clinical Intelligence'}</span>
        </div>
      </div>

      <div className="header-center">
        <div className="patient-quick-selector">
          <span className="selector-icon">👤</span>
          <span className="selector-label">Active Patient:</span>
          <select 
            value={patientId} 
            onChange={e => onSelectPatient(e.target.value)}
            className="patient-select-input"
            aria-label="Select active patient"
          >
            <option value="P001024">P001024 (Benchmark: T2D + HTN, 46y)</option>
            <option value="P000001">P000001 (Cohort: Diabetic, 52y)</option>
            <option value="P000002">P000002 (Cohort: Hypertension, 61y)</option>
            <option value="P000003">P000003 (Cohort: Oncology, 48y)</option>
          </select>
        </div>
      </div>

      <div className="header-right">
        {/* Real-time System Status Badges */}
        <div className="system-status-pills">
          <div className="status-pill online" title="FastAPI REST API Operational">
            <span className="status-dot"></span>
            <span className="status-text">API Live</span>
          </div>
          <div className="status-pill online" title="Apache Kafka Event Stream Connected">
            <span className="status-dot"></span>
            <span className="status-text">Kafka Bus</span>
          </div>
          <div className="status-pill online" title="Apache Spark Lakehouse (Bronze/Silver/Gold)">
            <span className="status-dot"></span>
            <span className="status-text">Lakehouse Active</span>
          </div>
        </div>

        {/* Live Clock */}
        <div className="header-clock" title="System UTC/Local Time">
          <span className="clock-icon">🕒</span>
          <span className="clock-time">{timeStr}</span>
        </div>

        {/* Theme Toggle Button */}
        <div className="theme-toggle-container">
          <button 
            type="button"
            className={`theme-toggle-btn ${theme}`} 
            onClick={onToggleTheme}
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
            aria-label="Toggle theme"
          >
            <span className="toggle-track">
              <span className="toggle-icon sun">☀️</span>
              <span className="toggle-icon moon">🌙</span>
              <span className="toggle-thumb"></span>
            </span>
          </button>
        </div>

        {/* User Profile Pill */}
        <div className="user-profile-pill" onClick={() => onNavigate('compliance')}>
          <div className="user-avatar">DR</div>
          <div className="user-info">
            <span className="user-name">Dr. Investigator</span>
            <span className="user-role">Lead Clinician</span>
          </div>
        </div>
      </div>
    </header>
  )
}
