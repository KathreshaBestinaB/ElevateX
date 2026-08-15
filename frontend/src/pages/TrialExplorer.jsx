import { useState, useEffect } from 'react'
import { fetchTrials, fetchTrialAnalytics } from '../services/api.js'

export default function TrialExplorer({ onNavigate }) {
  const [trials, setTrials] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedTrial, setSelectedTrial] = useState(null)
  const [trialAnalytics, setTrialAnalytics] = useState(null)
  const [phaseFilter, setPhaseFilter] = useState('ALL')
  const [search, setSearch] = useState('')

  useEffect(() => {
    fetchTrials(100)
      .then(res => {
        setTrials(res || [])
        if (res && res.length > 0) {
          const defaultTrial = res.find(t => t.trial_id === 'TR-02045') || res[0]
          handleSelectTrial(defaultTrial)
        }
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [])

  function handleSelectTrial(trial) {
    setSelectedTrial(trial)
    fetchTrialAnalytics(trial.trial_id)
      .then(res => setTrialAnalytics(res))
      .catch(() => setTrialAnalytics(null))
  }

  const filteredTrials = trials.filter(t => {
    const matchesPhase = phaseFilter === 'ALL' || t.phase === phaseFilter
    const matchesSearch = !search || 
      t.title?.toLowerCase().includes(search.toLowerCase()) ||
      t.trial_id?.toLowerCase().includes(search.toLowerCase()) ||
      t.conditions?.some(c => c.toLowerCase().includes(search.toLowerCase()))
    return matchesPhase && matchesSearch
  })

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <span className="badge badge-blue">Clinical Protocol Catalog</span>
          <h2>Trial Protocol Explorer & Performance</h2>
          <p>Index of 10,000 interventional & observational clinical studies with structured eligibility criteria.</p>
        </div>
      </div>

      <div className="grid-2col" style={{ gridTemplateColumns: '1fr 1.3fr', gap: '1.5rem', marginTop: '1rem' }}>
        {/* Left column: Trial List with Search & Phase Filters */}
        <div className="card">
          <div className="card-header">
            <h3>Indexed Trials</h3>
            <span className="badge badge-purple">{filteredTrials.length} trials</span>
          </div>

          <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', marginBottom: '1rem' }}>
            <input 
              type="text" 
              placeholder="Search title, condition, NCT ID..."
              value={search}
              onChange={e => setSearch(e.target.value)}
              className="search-input"
              style={{ flex: 1 }}
            />
            <select 
              value={phaseFilter} 
              onChange={e => setPhaseFilter(e.target.value)}
              className="select-input"
            >
              <option value="ALL">All Phases</option>
              <option value="Phase 1">Phase 1</option>
              <option value="Phase 2">Phase 2</option>
              <option value="Phase 3">Phase 3</option>
              <option value="Phase 4">Phase 4</option>
            </select>
          </div>

          <div style={{ maxHeight: '600px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
            {filteredTrials.map(t => (
              <div 
                key={t.trial_id}
                onClick={() => handleSelectTrial(t)}
                className={`trial-list-item ${selectedTrial?.trial_id === t.trial_id ? 'active' : ''}`}
                style={{
                  padding: '0.85rem',
                  borderRadius: '8px',
                  background: selectedTrial?.trial_id === t.trial_id ? 'rgba(0, 210, 186, 0.12)' : 'rgba(255, 255, 255, 0.03)',
                  border: selectedTrial?.trial_id === t.trial_id ? '1px solid #00D2BA' : '1px solid rgba(255, 255, 255, 0.07)',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="font-bold text-white text-sm">{t.trial_id}</span>
                  <span className={`badge ${t.status === 'COMPLETED' ? 'badge-green' : 'badge-blue'}`}>{t.status}</span>
                </div>
                <div className="text-sm font-semibold text-white" style={{ marginTop: '0.25rem' }}>{t.title}</div>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.4rem' }}>
                  <span className="badge badge-purple text-xs">{t.phase || 'Interventional'}</span>
                  {t.conditions?.map((c, i) => (
                    <span key={i} className="badge badge-teal text-xs">{c}</span>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right column: Selected Trial Detail & Analytics */}
        <div>
          {selectedTrial ? (
            <div className="card">
              <div className="card-header">
                <div>
                  <span className="badge badge-teal">{selectedTrial.trial_id}</span>
                  <h3 style={{ marginTop: '0.3rem' }}>{selectedTrial.title}</h3>
                </div>
                <span className="badge badge-blue">{selectedTrial.phase}</span>
              </div>

              <p className="text-muted text-sm" style={{ marginTop: '0.75rem', lineHeight: '1.6' }}>
                {selectedTrial.brief_summary || 'Clinical trial protocol exploring therapeutic intervention.'}
              </p>

              {/* Performance Metrics if available */}
              {trialAnalytics && (
                <div style={{ marginTop: '1.2rem', padding: '1rem', background: 'rgba(0,0,0,0.25)', borderRadius: '8px' }}>
                  <h4 className="text-xs uppercase text-teal font-bold" style={{ letterSpacing: '0.05em' }}>
                    Lakehouse Trial Performance Metrics
                  </h4>
                  <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginTop: '0.75rem' }}>
                    <div>
                      <span className="text-muted text-xs">Total Enrolled</span>
                      <div className="font-bold text-white text-lg">{trialAnalytics.total_enrolled?.toLocaleString()}</div>
                    </div>
                    <div>
                      <span className="text-muted text-xs">Positive Response</span>
                      <div className="font-bold text-teal text-lg">{trialAnalytics.response_rate}%</div>
                    </div>
                    <div>
                      <span className="text-muted text-xs">Completed</span>
                      <div className="font-bold text-green text-lg">{trialAnalytics.total_completed?.toLocaleString()}</div>
                    </div>
                  </div>
                </div>
              )}

              {/* Structured Eligibility Rules */}
              <div style={{ marginTop: '1.5rem' }}>
                <h4>Normalized Eligibility Criteria</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
                  {selectedTrial.eligibility_criteria?.map((crit, idx) => (
                    <div 
                      key={idx}
                      style={{
                        padding: '0.65rem 0.85rem',
                        background: 'rgba(255,255,255,0.02)',
                        borderLeft: crit.required ? '3px solid #00D2BA' : '3px solid #F87171',
                        borderRadius: '4px',
                        fontSize: '0.85rem',
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span className="font-semibold text-white">{crit.name || crit.criterion_type}</span>
                        <span className="badge badge-purple text-xs">{crit.required ? 'Inclusion' : 'Exclusion'}</span>
                      </div>
                      <div className="text-muted text-xs" style={{ marginTop: '0.2rem' }}>
                        {crit.source_text}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.75rem' }}>
                <button 
                  className="btn btn-primary"
                  onClick={() => onNavigate('matching', { trialId: selectedTrial.trial_id })}
                >
                  Run Patient Matching
                </button>
                <button 
                  className="btn btn-secondary"
                  onClick={() => onNavigate('assistant')}
                >
                  Analyze with Research AI
                </button>
              </div>
            </div>
          ) : (
            <div className="card text-center text-muted" style={{ padding: '3rem' }}>
              Select a clinical trial from the left to view protocol and lakehouse outcomes.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
