import { useState } from 'react'
import Sidebar from './components/Sidebar.jsx'
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

  const Page = PAGES[page] || Dashboard

  function navigateTo(p, opts = {}) {
    if (opts.patientId) setPatientId(opts.patientId)
    setPage(p)
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  return (
    <div className="app-shell">
      <Sidebar activePage={page} onNavigate={navigateTo} />
      <main className="main-content">
        <Page patientId={patientId} onNavigate={navigateTo} />
      </main>
    </div>
  )
}
