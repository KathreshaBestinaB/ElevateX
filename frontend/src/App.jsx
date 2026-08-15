import { useState, useEffect } from 'react'
import Sidebar from './components/Sidebar.jsx'
import Header from './components/Header.jsx'
import Dashboard from './pages/Dashboard.jsx'
import PatientProfile from './pages/PatientProfile.jsx'
import TrialMatching from './pages/TrialMatching.jsx'
import TrialExplorer from './pages/TrialExplorer.jsx'
import PopulationAnalytics from './pages/PopulationAnalytics.jsx'
import MedicationEffectiveness from './pages/MedicationEffectiveness.jsx'
import CohortDiscovery from './pages/CohortDiscovery.jsx'
import SimilarPatients from './pages/SimilarPatients.jsx'
import DocumentIntelligence from './pages/DocumentIntelligence.jsx'
import DataPipelineMonitor from './pages/DataPipelineMonitor.jsx'
import ResearchAssistant from './pages/ResearchAssistant.jsx'
import ComplianceCenter from './pages/ComplianceCenter.jsx'

const PAGES = {
  dashboard:   Dashboard,
  patient:     PatientProfile,
  matching:    TrialMatching,
  trials:      TrialExplorer,
  similar:     SimilarPatients,
  analytics:   PopulationAnalytics,
  medications: MedicationEffectiveness,
  cohorts:     CohortDiscovery,
  assistant:   ResearchAssistant,
  documents:   DocumentIntelligence,
  pipeline:    DataPipelineMonitor,
  compliance:  ComplianceCenter,
}

export default function App() {
  const [page, setPage] = useState('dashboard')
  const [patientId, setPatientId] = useState('P001024')
  
  // Theme state: dark (default) or light, with localStorage persistence
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('trialforge_theme') || 'dark'
  })

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem('trialforge_theme', theme)
  }, [theme])

  function toggleTheme() {
    setTheme(prev => (prev === 'dark' ? 'light' : 'dark'))
  }

  function navigateTo(p, opts = {}) {
    if (opts.patientId) setPatientId(opts.patientId)
    setPage(p)
    const content = document.querySelector('.main-content')
    if (content) content.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const PageComponent = PAGES[page] || Dashboard

  return (
    <div className="app-shell">
      <Sidebar activePage={page} onNavigate={navigateTo} />
      <div className="main-wrapper">
        <Header 
          activePage={page}
          patientId={patientId}
          onSelectPatient={setPatientId}
          theme={theme}
          onToggleTheme={toggleTheme}
          onNavigate={navigateTo}
        />
        <main className="main-content">
          <PageComponent patientId={patientId} onNavigate={navigateTo} />
        </main>
      </div>
    </div>
  )
}
