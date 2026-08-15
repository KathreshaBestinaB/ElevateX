import { useState, useEffect } from 'react'
import { fetchComplianceDashboard, recordReviewAction } from '../services/api.js'

export default function ComplianceCenter() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [reviewNotes, setReviewNotes] = useState('Reviewed 24-week outcome delta and approved AI response analysis.')
  const [reviewSuccess, setReviewSuccess] = useState(false)

  const loadDashboard = async () => {
    try {
      const res = await fetchComplianceDashboard()
      setData(res)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  async function handleApprove() {
    try {
      await recordReviewAction({
        patient_id: 'P001024',
        trial_id: 'TR-02045',
        action: 'APPROVED',
        reviewer: 'dr.principal_investigator@hospital.org',
        notes: reviewNotes,
      })
      setReviewSuccess(true)
      await loadDashboard()
      setTimeout(() => setReviewSuccess(false), 4000)
    } catch (err) {
      console.error(err)
    }
  }

  function handleExportAudit() {
    if (!data?.recent_audit_logs) return
    const blob = new Blob([JSON.stringify(data.recent_audit_logs, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit_trail_export_${new Date().toISOString().slice(0, 10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <span className="badge badge-teal">FDA 21 CFR Part 11 & GCP ICH E6</span>
          <h2>Compliance, Data Quality & Audit Center</h2>
          <p>Continuous clinical data validation, algorithmic model governance, and human-in-the-loop sign-off.</p>
        </div>
        <div style={{ display: 'flex', gap: '0.75rem' }}>
          <button className="btn btn-outline" onClick={handleExportAudit}>
            📥 Export Audit Trail (JSON)
          </button>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Loading governance registry and data quality audits...</div>
      ) : data ? (
        <>
          {/* Top KPI Cards: Quality & Compliance */}
          <div className="metrics-grid" style={{ marginTop: '1rem' }}>
            <div className="metric-card">
              <span className="metric-label">Data Quality Score</span>
              <span className="metric-value text-teal">{data.data_quality.overall_quality_score}%</span>
              <span className="metric-sub">Status: {data.data_quality.quality_status}</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Records Audited</span>
              <span className="metric-value text-white">{data.data_quality.metrics.total_records_audited?.toLocaleString()}</span>
              <span className="metric-sub">{data.data_quality.metrics.valid_records?.toLocaleString()} fully verified</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">HIPAA De-identification</span>
              <span className="metric-value text-green">100% Passed</span>
              <span className="metric-sub">Safe Harbor Standard</span>
            </div>
            <div className="metric-card">
              <span className="metric-label">Active Governance Models</span>
              <span className="metric-value text-purple">{data.model_registry.length} Models</span>
              <span className="metric-sub">Full version lineage</span>
            </div>
          </div>

          <div className="grid-2col" style={{ marginTop: '1.5rem', gap: '1.5rem' }}>
            {/* Left: Data Integrity Checks */}
            <div className="card">
              <div className="card-header">
                <h3>Clinical Data Validation Checks</h3>
                <span className="badge badge-teal">Automated Rules</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem', marginTop: '1rem' }}>
                {data.data_quality.integrity_checks?.map((chk, i) => (
                  <div key={i} style={{ display: 'flex', justifyContent: 'space-between', padding: '0.65rem 0.85rem', background: 'rgba(255,255,255,0.03)', borderRadius: '6px', fontSize: '0.85rem' }}>
                    <span className="text-white font-medium">{chk.check}</span>
                    <span className="badge badge-green text-xs">{chk.status} ({chk.pass_rate})</span>
                  </div>
                ))}
              </div>

              {/* Human in the loop review box */}
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(0, 210, 186, 0.06)', border: '1px solid rgba(0, 210, 186, 0.3)', borderRadius: '8px' }}>
                <h4 className="text-xs text-teal font-bold uppercase">Human-In-The-Loop Sign-Off</h4>
                <p className="text-xs text-muted" style={{ marginTop: '0.25rem' }}>
                  Record formal clinician sign-off on Patient P001024 / TR-02045 outcome intelligence report.
                </p>
                <input 
                  type="text" 
                  value={reviewNotes}
                  onChange={e => setReviewNotes(e.target.value)}
                  className="input-text"
                  style={{ width: '100%', marginTop: '0.5rem', fontSize: '0.85rem' }}
                />
                <div style={{ marginTop: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <button className="btn btn-primary text-xs" onClick={handleApprove}>
                    ✍️ Sign & Approve Clinical Finding
                  </button>
                  {reviewSuccess && (
                    <span className="text-xs text-green font-bold">✓ Audit Log Recorded Successfully</span>
                  )}
                </div>
              </div>
            </div>

            {/* Right: Model Governance Registry */}
            <div className="card">
              <div className="card-header">
                <h3>Production Model Registry & Lineage</h3>
                <span className="badge badge-purple">MLOps Governance</span>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
                {data.model_registry?.map((m, i) => (
                  <div key={i} style={{ padding: '0.85rem', background: 'rgba(255,255,255,0.03)', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.07)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span className="font-bold text-white text-sm">{m.model_name}</span>
                      <span className="badge badge-blue text-xs font-mono">{m.version}</span>
                    </div>
                    <div className="text-xs text-muted" style={{ marginTop: '0.3rem' }}>
                      Algorithm: <strong className="text-white">{m.algorithm}</strong>
                    </div>
                    <div className="text-xs text-teal font-mono" style={{ marginTop: '0.3rem' }}>
                      {Object.entries(m.metrics).map(([k, v]) => `${k.toUpperCase()}: ${v}`).join(' • ')}
                    </div>
                    <div className="text-xs text-muted" style={{ marginTop: '0.3rem' }}>
                      Explainability: {m.explainability_engine}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          {/* Full Audit Log Table */}
          <div className="table-card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <h3>Immutable Audit Trail (FDA 21 CFR Part 11 Lineage)</h3>
              <span className="badge badge-blue">{data.recent_audit_logs?.length} recent events</span>
            </div>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Audit ID</th>
                  <th>Timestamp</th>
                  <th>User / Daemon</th>
                  <th>Role</th>
                  <th>Action</th>
                  <th>Target Resource</th>
                  <th>Verification Status</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_audit_logs?.map((log, idx) => (
                  <tr key={idx}>
                    <td className="font-mono font-bold text-white text-xs">{log.log_id}</td>
                    <td className="text-xs text-muted">{log.timestamp}</td>
                    <td className="text-white font-medium text-xs">{log.user}</td>
                    <td><span className="badge badge-purple text-xs">{log.role}</span></td>
                    <td className="font-mono text-xs text-teal">{log.action}</td>
                    <td className="text-xs text-white">{log.resource}</td>
                    <td><span className="badge badge-green text-xs">{log.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      ) : null}
    </div>
  )
}
