import { useState } from 'react'
import { analyzeDocumentText, uploadDocument } from '../services/api.js'

const DEFAULT_SAMPLE_PROTOCOL = `CLINICAL TRIAL PROTOCOL — STUDY TR-02045 (PHASE 3)
A Multicenter, Randomized, Double-Blind Study Evaluating the Efficacy and Safety of Drug-X-001 in Patients with Inadequately Controlled Type 2 Diabetes Mellitus.

SECTION 4: ELIGIBILITY CRITERIA
4.1 INCLUSION CRITERIA
1. Adults aged 18 to 70 years at the time of screening.
2. Documented diagnosis of Type 2 Diabetes Mellitus for at least 12 months.
3. Inadequate glycemic control defined as baseline HbA1c between 7.5% and 12.0% inclusive.
4. Body Mass Index (BMI) >= 25.0 kg/m2.
5. Currently receiving stable Metformin 1000mg oral daily for >= 12 weeks.

4.2 EXCLUSION CRITERIA
1. Documented diagnosis of Type 1 Diabetes Mellitus or acute metabolic acidosis.
2. Severe renal impairment defined as estimated Glomerular Filtration Rate (eGFR) < 30 mL/min/1.73m2.
3. History of acute pancreatitis or severe hepatic dysfunction (ALT/AST > 3x ULN).
4. Female patients who are pregnant, nursing, or planning pregnancy during the trial.

SECTION 5: STUDY INTERVENTIONS
- Investigational Drug: Drug-X-001 (50mg oral once daily)
- Background Therapy: Metformin (1000mg oral twice daily)
- Primary Outcome Endpoint: Change in HbA1c from baseline to Week 24.`

export default function DocumentIntelligence() {
  const [text, setText] = useState(DEFAULT_SAMPLE_PROTOCOL)
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  async function handleAnalyze() {
    setLoading(true)
    setError(null)
    try {
      const res = await analyzeDocumentText(text, 'protocol_TR02045.txt')
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  async function handleFileUpload(e) {
    const file = e.target.files[0]
    if (!file) return
    setLoading(true)
    setError(null)
    try {
      const res = await uploadDocument(file)
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <span className="badge badge-teal">NLP & Biomedical Entity Extractor</span>
          <h2>Clinical Document Intelligence Studio</h2>
          <p>Extract structured eligibility criteria, medication regimens, biomarkers, and provenance from trial protocols.</p>
        </div>
      </div>

      <div className="grid-2col" style={{ gridTemplateColumns: '1fr 1.2fr', gap: '1.5rem', marginTop: '1rem' }}>
        {/* Left Column: Input & Upload */}
        <div className="card">
          <div className="card-header">
            <h3>Protocol Text / PDF Upload</h3>
            <span className="badge badge-blue">Input Document</span>
          </div>

          <div style={{ marginTop: '1rem' }}>
            <label className="text-xs text-muted font-semibold uppercase">Upload Protocol PDF / TXT</label>
            <input 
              type="file" 
              accept=".pdf,.txt,.docx"
              onChange={handleFileUpload}
              className="file-input"
              style={{ marginTop: '0.3rem', width: '100%' }}
            />
          </div>

          <div style={{ marginTop: '1rem' }}>
            <label className="text-xs text-muted font-semibold uppercase">Or Edit Clinical Protocol Text</label>
            <textarea
              value={text}
              onChange={e => setText(e.target.value)}
              rows={14}
              className="textarea-input"
              style={{
                width: '100%',
                marginTop: '0.4rem',
                padding: '0.75rem',
                fontFamily: 'monospace',
                fontSize: '0.82rem',
                borderRadius: '8px',
                background: 'rgba(0,0,0,0.3)',
                color: '#E2E8F0',
                border: '1px solid rgba(255,255,255,0.1)',
              }}
            />
          </div>

          <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <button 
              className="btn btn-primary"
              onClick={handleAnalyze}
              disabled={loading}
            >
              {loading ? 'Extracting Clinical Entities...' : 'Run NLP Entity Extraction'}
            </button>
            <button 
              className="btn btn-secondary text-xs"
              onClick={() => setText(DEFAULT_SAMPLE_PROTOCOL)}
            >
              Reset Sample Protocol
            </button>
          </div>

          {error && (
            <div className="alert alert-danger" style={{ marginTop: '1rem' }}>
              {error}
            </div>
          )}
        </div>

        {/* Right Column: Structured Entity Extraction Output */}
        <div>
          {result ? (
            <div className="card">
              <div className="card-header">
                <div>
                  <span className="badge badge-green">Extraction Complete</span>
                  <h3 style={{ marginTop: '0.3rem' }}>Structured Intelligence & Lineage</h3>
                </div>
                <span className="badge badge-purple">{result.document_metadata?.pipeline}</span>
              </div>

              <div className="alert alert-info" style={{ marginTop: '0.75rem', fontSize: '0.85rem' }}>
                {result.summary}
              </div>

              {/* Conditions & Medications tags */}
              <div style={{ marginTop: '1rem' }}>
                <h4 className="text-xs text-muted uppercase font-bold">Identified Conditions</h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.4rem', marginTop: '0.3rem' }}>
                  {result.extracted_entities?.conditions?.map((c, i) => (
                    <span key={i} className="badge badge-teal">{c}</span>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '1rem' }}>
                <h4 className="text-xs text-muted uppercase font-bold">Interventions & Dosages (with Provenance)</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.4rem' }}>
                  {result.extracted_entities?.medications?.map((m, i) => (
                    <div key={i} style={{ padding: '0.5rem 0.75rem', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '0.85rem', display: 'flex', justifyContent: 'space-between' }}>
                      <span className="font-semibold text-white">{m.medication} • <span className="text-teal">{m.dose}</span></span>
                      <span className="text-xs text-muted">Confidence: {(m.provenance?.confidence * 100).toFixed(0)}%</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Structured Inclusion / Exclusion */}
              <div style={{ marginTop: '1.2rem' }}>
                <h4 className="text-xs text-teal uppercase font-bold">Normalized Inclusion Criteria</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.4rem' }}>
                  {result.structured_criteria?.inclusion?.map((crit, i) => (
                    <div key={i} style={{ padding: '0.5rem 0.75rem', borderLeft: '3px solid #00D2BA', background: 'rgba(0,210,186,0.04)', borderRadius: '4px', fontSize: '0.82rem' }}>
                      <div className="font-semibold text-white">{crit.raw_text}</div>
                      <div className="text-xs text-muted" style={{ marginTop: '0.2rem' }}>
                        Type: {crit.structured?.criterion_type} • Operator: {crit.structured?.operator || 'N/A'} • Value: {crit.structured?.value || 'N/A'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '1rem' }}>
                <h4 className="text-xs text-red uppercase font-bold">Normalized Exclusion Criteria</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', marginTop: '0.4rem' }}>
                  {result.structured_criteria?.exclusion?.map((crit, i) => (
                    <div key={i} style={{ padding: '0.5rem 0.75rem', borderLeft: '3px solid #F87171', background: 'rgba(248,113,113,0.04)', borderRadius: '4px', fontSize: '0.82rem' }}>
                      <div className="font-semibold text-white">{crit.raw_text}</div>
                      <div className="text-xs text-muted" style={{ marginTop: '0.2rem' }}>
                        Exclusion Condition: {crit.structured?.name}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="disclaimer-text" style={{ marginTop: '1.2rem' }}>
                ⚠️ {result.disclaimer}
              </div>
            </div>
          ) : (
            <div className="card text-center text-muted" style={{ padding: '4rem' }}>
              Click "Run NLP Entity Extraction" on the left to extract structured criteria and biomarker parameters.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
