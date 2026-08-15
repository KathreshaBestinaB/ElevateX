import { useState, useEffect } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  CartesianGrid, Legend
} from 'recharts'
import { fetchMedicationEffectiveness } from '../services/api.js'

export default function MedicationEffectiveness() {
  const [data, setData] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedDrug, setSelectedDrug] = useState('ALL')

  useEffect(() => {
    fetchMedicationEffectiveness()
      .then(res => {
        setData(res || [])
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [])

  const filtered = selectedDrug === 'ALL'
    ? data
    : data.filter(d => d.drug_class.toLowerCase().includes(selectedDrug.toLowerCase()))

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <span className="badge badge-teal">Longitudinal Comparative Analytics</span>
          <h2>Medication & Intervention Effectiveness</h2>
          <p>Cross-trial response rates, biomarker changes, adverse event rates, and completion metrics.</p>
        </div>
        <div className="filter-group">
          <select 
            value={selectedDrug} 
            onChange={e => setSelectedDrug(e.target.value)}
            className="select-input"
          >
            <option value="ALL">All Drug Classes</option>
            <option value="DPP-4">DPP-4 Inhibitors</option>
            <option value="GLP-1">GLP-1 Agonists</option>
            <option value="SGLT-2">SGLT-2 Inhibitors</option>
            <option value="Biguanides">Biguanides (Metformin)</option>
            <option value="ACE">ACE Inhibitors</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Analyzing drug response across 100,000 patient lakehouse...</div>
      ) : (
        <>
          <div className="metrics-grid">
            <div className="metric-card">
              <span className="metric-label">Highest Response Class</span>
              <span className="metric-value text-teal">GLP-1 Agonists</span>
              <span className="metric-sub">74.2% positive response rate</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Investigational Agent (Drug-X)</span>
              <span className="metric-value text-blue">68.4%</span>
              <span className="metric-sub">Avg HbA1c reduction: -1.85%</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Highest Completion Rate</span>
              <span className="metric-value text-green">ACE Inhibitors</span>
              <span className="metric-sub">94.0% trial protocol adherence</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Total Sample Size Audited</span>
              <span className="metric-value text-purple">33,000+</span>
              <span className="metric-sub">Longitudinal trial participants</span>
            </div>
          </div>

          <div className="charts-grid" style={{ marginTop: '1.5rem' }}>
            <div className="chart-card">
              <div className="card-header">
                <h3>Positive Response Rate vs Adverse Event Rate (%)</h3>
                <span className="badge badge-purple">Comparative Cohort Analysis</span>
              </div>
              <div style={{ height: 320, marginTop: '1rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={filtered} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="drug_class" stroke="#8A9BB4" angle={-15} textAnchor="end" height={60} tick={{ fontSize: 11 }} />
                    <YAxis stroke="#8A9BB4" domain={[0, 100]} />
                    <Tooltip contentStyle={{ background: '#111A2E', border: '1px solid #1E2D4A', borderRadius: 8, color: '#fff' }} />
                    <Legend wrapperStyle={{ paddingTop: 10 }} />
                    <Bar dataKey="response_rate" name="Positive Response Rate (%)" fill="#00D2BA" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="adverse_event_rate" name="Adverse Event Rate (%)" fill="#F87171" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="chart-card">
              <div className="card-header">
                <h3>Average Biomarker Change (%)</h3>
                <span className="badge badge-teal">Primary Endpoint Delta</span>
              </div>
              <div style={{ height: 320, marginTop: '1rem' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={filtered} margin={{ top: 10, right: 30, left: 0, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                    <XAxis dataKey="drug_class" stroke="#8A9BB4" angle={-15} textAnchor="end" height={60} tick={{ fontSize: 11 }} />
                    <YAxis stroke="#8A9BB4" />
                    <Tooltip contentStyle={{ background: '#111A2E', border: '1px solid #1E2D4A', borderRadius: 8, color: '#fff' }} />
                    <Bar dataKey="avg_hba1c_reduction" name="Mean HbA1c Reduction (%)" fill="#3B82F6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>
          </div>

          <div className="table-card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <h3>Medication Intelligence Catalog</h3>
              <span className="text-muted text-sm">{filtered.length} interventions documented</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Drug Class / Intervention</th>
                  <th>Primary Indication</th>
                  <th>Sample Size</th>
                  <th>Response Rate</th>
                  <th>Mean Change</th>
                  <th>Completion Rate</th>
                  <th>Common Adverse Events</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item, idx) => (
                  <tr key={idx}>
                    <td className="font-semibold text-white">{item.drug_class}</td>
                    <td><span className="badge badge-blue">{item.primary_indication}</span></td>
                    <td>{item.sample_size?.toLocaleString()}</td>
                    <td><span className="badge badge-teal">{item.response_rate}%</span></td>
                    <td className="text-blue">{item.avg_hba1c_reduction}%</td>
                    <td>{item.completion_rate}%</td>
                    <td className="text-sm text-muted">
                      {Array.isArray(item.common_adverse_events) ? item.common_adverse_events.join(', ') : 'None reported'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
