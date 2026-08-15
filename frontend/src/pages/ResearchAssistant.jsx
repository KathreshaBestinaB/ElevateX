import { useState } from 'react'
import { askResearchQuestion } from '../services/api.js'

const SUGGESTIONS = [
  'Why did patients in the treatment-resistant cohort have a low response rate?',
  'Which medication classes had the highest response rate across all trials?',
  'Which trials had the highest completion and lowest dropout rates?',
  'What clinical factors were most correlated with adverse events in Phase 3 trials?',
]

export default function ResearchAssistant() {
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      text: 'Welcome to the TrialForge AI Research Assistant. I provide evidence-based analytical summaries from the 100,000 patient lakehouse. Ask any question regarding treatment response, non-response factor associations, drug effectiveness, or cohort characteristics.',
      findings: null,
      disclaimer: 'Observational research decision-support only. Not autonomous medical diagnosis or prescriptive directives.',
      timestamp: new Date().toLocaleTimeString(),
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSend(queryText) {
    const textToSend = queryText || input
    if (!textToSend.trim() || loading) return

    const userMsg = {
      role: 'user',
      text: textToSend,
      timestamp: new Date().toLocaleTimeString(),
    }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await askResearchQuestion(textToSend)
      const assistantMsg = {
        role: 'assistant',
        text: res.answer,
        findings: res.findings,
        disclaimer: res.disclaimer,
        cohortSize: res.cohort_size,
        evidenceLevel: res.evidence_level,
        timestamp: new Date().toLocaleTimeString(),
      }
      setMessages(prev => [...prev, assistantMsg])
    } catch (err) {
      setMessages(prev => [
        ...prev,
        {
          role: 'assistant',
          text: 'Encountered an error while querying analytical dataset. Please try again.',
          timestamp: new Date().toLocaleTimeString(),
        }
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 40px)' }}>
      <div className="page-header" style={{ marginBottom: '1rem' }}>
        <div>
          <span className="badge badge-purple">Safe Analytical Query Engine</span>
          <h2>AI Clinical Research Assistant</h2>
          <p>Natural language research inquiry backed by 100,000 synthetic patient longitudinal lakehouse records.</p>
        </div>
      </div>

      {/* Suggested Inquiries */}
      <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
        {SUGGESTIONS.map((s, idx) => (
          <button
            key={idx}
            onClick={() => handleSend(s)}
            className="btn btn-secondary text-xs"
            style={{ borderRadius: '20px', padding: '0.4rem 0.8rem' }}
          >
            💡 {s}
          </button>
        ))}
      </div>

      {/* Chat conversation area */}
      <div 
        className="card" 
        style={{ 
          flex: 1, 
          overflowY: 'auto', 
          display: 'flex', 
          flexDirection: 'column', 
          gap: '1.2rem',
          padding: '1.5rem',
          marginBottom: '1rem',
          background: 'rgba(10, 16, 30, 0.7)'
        }}
      >
        {messages.map((m, idx) => (
          <div 
            key={idx} 
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: m.role === 'user' ? '75%' : '88%',
            }}
          >
            <div 
              style={{
                padding: '1rem 1.25rem',
                borderRadius: '12px',
                background: m.role === 'user' ? '#00D2BA' : 'rgba(255,255,255,0.05)',
                color: m.role === 'user' ? '#050D1E' : '#E2E8F0',
                border: m.role === 'user' ? 'none' : '1px solid rgba(255,255,255,0.1)',
                boxShadow: '0 4px 12px rgba(0,0,0,0.2)',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem', fontSize: '0.75rem', opacity: 0.8 }}>
                <span className="font-bold">{m.role === 'user' ? 'Clinical Researcher' : 'TrialForge Intelligence Engine'}</span>
                <span>{m.timestamp}</span>
              </div>
              
              <p style={{ fontSize: '0.92rem', lineHeight: '1.6', fontWeight: m.role === 'user' ? 600 : 400 }}>
                {m.text}
              </p>

              {/* Evidence findings table if present */}
              {m.findings && (
                <div style={{ marginTop: '1rem', padding: '0.75rem', background: 'rgba(0,0,0,0.3)', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                    <span className="text-xs font-bold text-teal uppercase">Supporting Dataset Evidence ({m.cohortSize?.toLocaleString()} Records Analyzed)</span>
                    <span className="badge badge-purple text-xs">Evidence: {m.evidenceLevel}</span>
                  </div>
                  <table className="data-table" style={{ fontSize: '0.82rem' }}>
                    <tbody>
                      {m.findings.map((f, fIdx) => (
                        <tr key={fIdx}>
                          <td className="font-semibold text-white">{f.factor || f.medication || f.trial_type}</td>
                          <td><span className="badge badge-teal">{f.association || f.response_rate || f.completion_rate}</span></td>
                          <td className="text-muted text-xs">{f.note || (f.sample_size ? `${f.sample_size} patients` : '')}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {m.disclaimer && (
                <div style={{ marginTop: '0.75rem', fontSize: '0.72rem', color: '#94A3B8', borderTop: '1px solid rgba(255,255,255,0.1)', paddingTop: '0.4rem' }}>
                  ⚠️ {m.disclaimer}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div style={{ alignSelf: 'flex-start', padding: '0.75rem 1rem', background: 'rgba(255,255,255,0.05)', borderRadius: '12px', fontSize: '0.85rem', color: '#00D2BA' }}>
            ⚡ Synthesizing longitudinal trial evidence and calculating statistical associations...
          </div>
        )}
      </div>

      {/* Input bar */}
      <div style={{ display: 'flex', gap: '0.75rem' }}>
        <input 
          type="text" 
          placeholder="Ask a clinical research question regarding outcomes, non-response, or cohorts..."
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSend()}
          className="search-input"
          style={{ flex: 1, padding: '0.85rem 1.2rem', fontSize: '0.95rem' }}
        />
        <button 
          className="btn btn-primary"
          onClick={() => handleSend()}
          disabled={loading || !input.trim()}
          style={{ padding: '0 1.8rem' }}
        >
          Send Query
        </button>
      </div>
    </div>
  )
}
