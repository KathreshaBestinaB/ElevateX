const NAV = [
  {
    section: 'Clinical Intelligence',
    items: [
      { id: 'dashboard',    icon: '⬡', label: 'Command Centre' },
      { id: 'patient',      icon: '👤', label: 'Patient Intelligence', badge: '6 Questions' },
      { id: 'matching',     icon: '🎯', label: 'Trial Matching Engine' },
      { id: 'trials',       icon: '📋', label: 'Trial Protocol Explorer' },
      { id: 'similar',      icon: '👥', label: 'Similar Patient Search' },
    ],
  },
  {
    section: 'Analytics & Research',
    items: [
      { id: 'analytics',    icon: '📊', label: 'Population Analytics' },
      { id: 'medications',  icon: '💊', label: 'Drug Effectiveness' },
      { id: 'cohorts',      icon: '🧬', label: 'Research Cohorts' },
      { id: 'assistant',    icon: '🤖', label: 'AI Research Assistant' },
      { id: 'documents',    icon: '📄', label: 'Document NLP Studio' },
    ],
  },
  {
    section: 'Big Data & Governance',
    items: [
      { id: 'pipeline',     icon: '⚡', label: 'Spark & Kafka Streaming', badge: 'Live' },
      { id: 'compliance',   icon: '🛡️', label: 'Data Quality & Audit' },
    ],
  },
]

export default function Sidebar({ activePage, onNavigate }) {
  return (
    <aside className="sidebar" role="navigation" aria-label="Main navigation">
      <div className="sidebar-logo">
        <div className="logo-mark">
          <div className="logo-icon">🧪</div>
          <div className="logo-text">
            <h1>TrialForge AI</h1>
            <p>Clinical Trial & Outcome Intelligence</p>
          </div>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV.map(group => (
          <div key={group.section} className="nav-group">
            <div className="nav-section-label">{group.section}</div>
            {group.items.map(item => (
              <button
                key={item.id}
                id={`nav-${item.id}`}
                className={`nav-item${activePage === item.id ? ' active' : ''}`}
                onClick={() => onNavigate(item.id)}
                aria-current={activePage === item.id ? 'page' : undefined}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
                {item.badge && <span className="nav-badge">{item.badge}</span>}
              </button>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="disclaimer-pill">
          <span className="pill-dot"></span>
          <span>Decision-Support Prototype • Synthetic Data (100k)</span>
        </div>
      </div>
    </aside>
  )
}
