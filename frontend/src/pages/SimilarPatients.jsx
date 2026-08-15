import { useState, useEffect } from 'react'
import { fetchSimilarPatients, fetchPatients } from '../services/api.js'

export default function SimilarPatients({ patientId = 'P001024', onNavigate }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [currentId, setCurrentId] = useState(patientId)
  const [patientList, setPatientList] = useState([])

  useEffect(() => {
    fetchPatients(10).then(res => setPatientList(res || [])).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchSimilarPatients(currentId)
      .then(res => {
        setData(res)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [currentId])

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <span className="badge badge-purple">High-Dimensional Vector Search</span>
          <h2>Similar Patient Cohort Search Engine</h2>
          <p>Scans patient records across the clinical lakehouse using multi-parametric distance vectors.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <label className="text-sm text-muted">Target Patient:</label>
          <select 
            value={currentId} 
            onChange={e => setCurrentId(e.target.value)}
            className="select-input"
          >
            <option value="P001024">P001024 (Demo Benchmark)</option>
            {patientList.filter(p => p.patient_id !== 'P001024').map(p => (
              <option key={p.patient_id} value={p.patient_id}>{p.patient_id} ({p.gender}, {p.age}y)</option>
            ))}
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Querying clinical feature matrix across analytical cluster...</div>
      ) : data ? (
        <>
          {/* Query Patient Snapshot */}
          <div className="card" style={{ marginTop: '1rem', background: 'linear-gradient(135deg, rgba(20,28,48,0.8), rgba(10,16,30,0.9))' }}>
            <div className="card-header">
              <h3>Target Patient Vector Profile: {data.query_patient.patient_id}</h3>
              <span className="badge badge-teal">Benchmark Input</span>
            </div>
            <div className="metrics-grid" style={{ gridTemplateColumns: 'repeat(4, 1fr)', marginTop: '0.75rem' }}>
              <div>
                <span className="text-muted text-xs">Demographics</span>
                <div className="font-bold text-white text-md">{data.query_patient.gender}, {data.query_patient.age} years</div>
              </div>
              <div>
                <span className="text-muted text-xs">Baseline Biomarker</span>
                <div className="font-bold text-teal text-md">HbA1c: {data.query_patient.baseline_hba1c}</div>
              </div>
              <div>
                <span className="text-muted text-xs">Diagnoses</span>
                <div className="font-semibold text-white text-sm">{data.query_patient.conditions.join(', ')}</div>
              </div>
              <div>
                <span className="text-muted text-xs">Search Space</span>
                <div className="font-bold text-purple text-md">{data.search_space?.patients_analyzed?.toLocaleString() || '1,000'} Patients Audited</div>
              </div>
            </div>
          </div>

          {/* Similar Cohort Summary */}
          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <div>
                <span className="badge badge-green">Nearest Cluster Match</span>
                <h3 style={{ marginTop: '0.25rem' }}>
                  Identified Similar Cohort ({data.most_similar_cohort_summary.cohort_size} Patients)
                </h3>
              </div>
              <span className="badge badge-purple">{data.most_similar_cohort_summary.primary_condition}</span>
            </div>

            <p className="text-muted text-sm" style={{ marginTop: '0.5rem' }}>
              Historical treatment outcomes across patients sharing identical baseline biomarkers (HbA1c &gt; 9.0%), age distribution, and comorbidity index:
            </p>

            <div className="table-card" style={{ marginTop: '1rem', background: 'transparent', padding: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Administered Treatment Regimen</th>
                    <th>Patients in Cohort</th>
                    <th>Observed Positive Response Rate</th>
                    <th>Median Biomarker Delta</th>
                  </tr>
                </thead>
                <tbody>
                  {data.most_similar_cohort_summary.historical_treatment_outcomes.map((item, idx) => (
                    <tr key={idx}>
                      <td className="font-semibold text-white">{item.treatment}</td>
                      <td>{item.patients_count} patients</td>
                      <td>
                        <span className={`badge ${parseFloat(item.positive_response_rate) >= 70 ? 'badge-teal' : 'badge-blue'}`}>
                          {item.positive_response_rate}
                        </span>
                      </td>
                      <td className="font-bold text-blue">{item.median_biomarker_change}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Non-response insight */}
            <div style={{ marginTop: '1.2rem', padding: '1rem', background: 'rgba(239, 68, 68, 0.08)', border: '1px solid rgba(239, 68, 68, 0.2)', borderRadius: '8px' }}>
              <h4 className="text-red font-bold text-xs uppercase" style={{ letterSpacing: '0.05em' }}>
                Observed Non-Response Factors in this Cohort
              </h4>
              <p className="text-sm text-white" style={{ marginTop: '0.3rem' }}>
                <span className="text-muted">Non-Response Frequency:</span> <strong className="text-red">{data.most_similar_cohort_summary.non_response_frequency}</strong> • 
                <span className="text-muted"> Top Associated Factor:</span> <strong>{data.most_similar_cohort_summary.top_correlated_non_response_factor}</strong>
              </p>
            </div>

            <div className="disclaimer-text" style={{ marginTop: '1rem' }}>
              ⚠️ {data.disclaimer}
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
