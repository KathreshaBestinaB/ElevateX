import { useState, useEffect } from 'react'
import { fetchPipelineStatus, publishStreamEvent } from '../services/api.js'

export default function DataPipelineMonitor() {
  const [pipeline, setPipeline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [simBiomarker, setSimBiomarker] = useState('HbA1c')
  const [simValue, setSimValue] = useState(7.0)
  const [streamingLog, setStreamingLog] = useState([])
  const [publishing, setPublishing] = useState(false)

  useEffect(() => {
    fetchPipelineStatus()
      .then(res => {
        setPipeline(res)
        setLoading(false)
      })
      .catch(err => {
        console.error(err)
        setLoading(false)
      })
  }, [])

  async function handleSimulateEvent() {
    setPublishing(true)
    try {
      const res = await publishStreamEvent({
        event_type: 'lab.results',
        patient_id: 'P001024',
        biomarker: simBiomarker,
        value: parseFloat(simValue),
        unit: '%',
        trial_id: 'TR-02045',
        notes: 'Real-time Kafka streaming trigger event',
      })
      setStreamingLog(prev => [res, ...prev])
    } catch (err) {
      console.error(err)
    } finally {
      setPublishing(false)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <span className="badge badge-teal">Big Data Lakehouse & Streaming Engine</span>
          <h2>Spark, Kafka & Airflow Data Pipeline Monitor</h2>
          <p>Real-time distributed lakehouse metrics, event-driven streaming topics, and automated DAG runs.</p>
        </div>
      </div>

      {loading ? (
        <div className="loading-state">Querying Apache Spark lakehouse & Kafka cluster metadata...</div>
      ) : pipeline ? (
        <>
          {/* Big Data Lakehouse Layer Architecture */}
          <div className="card" style={{ marginTop: '1rem' }}>
            <div className="card-header">
              <h3>Distributed Lakehouse Architecture (Apache Parquet)</h3>
              <span className="badge badge-purple">100,000 Patient Scale</span>
            </div>
            
            <div className="grid-3col" style={{ marginTop: '1rem', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'rgba(217, 119, 6, 0.08)', border: '1px solid rgba(217, 119, 6, 0.3)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="font-bold text-amber text-sm uppercase">Bronze Layer (Raw)</span>
                  <span className="badge badge-amber text-xs">5 Tables</span>
                </div>
                <p className="text-xs text-muted" style={{ marginTop: '0.4rem' }}>
                  Raw ingested CSVs converted to snappy-compressed Parquet lakehouse storage.
                </p>
                <div className="text-xs text-white" style={{ marginTop: '0.5rem' }}>
                  Tables: <code>patients</code>, <code>trials</code>, <code>enrollments</code>, <code>medications</code>, <code>outcomes</code>
                </div>
              </div>

              <div style={{ padding: '1rem', background: 'rgba(148, 163, 184, 0.08)', border: '1px solid rgba(148, 163, 184, 0.3)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="font-bold text-gray-300 text-sm uppercase">Silver Layer (Cleaned)</span>
                  <span className="badge badge-blue text-xs">Enriched Fact</span>
                </div>
                <p className="text-xs text-muted" style={{ marginTop: '0.4rem' }}>
                  Joined longitudinal clinical fact table with normalized biomarker vectors and drug classes.
                </p>
                <div className="text-xs text-white" style={{ marginTop: '0.5rem' }}>
                  Table: <code>patient_outcomes.parquet</code>
                </div>
              </div>

              <div style={{ padding: '1rem', background: 'rgba(0, 210, 186, 0.08)', border: '1px solid rgba(0, 210, 186, 0.3)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="font-bold text-teal text-sm uppercase">Gold Layer (Analytics)</span>
                  <span className="badge badge-teal text-xs">4 Aggregations</span>
                </div>
                <p className="text-xs text-muted" style={{ marginTop: '0.4rem' }}>
                  Spark aggregations powering high-speed interactive researcher dashboards and ML inference.
                </p>
                <div className="text-xs text-white" style={{ marginTop: '0.5rem' }}>
                  Tables: <code>population_kpis</code>, <code>drug_effectiveness</code>, <code>trial_kpis</code>, <code>cohort_stats</code>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Kafka Live Stream Demonstration */}
          <div className="card" style={{ marginTop: '1.5rem', border: '1px solid rgba(0, 210, 186, 0.4)' }}>
            <div className="card-header">
              <div>
                <span className="badge badge-teal">Live Demonstration for Jury</span>
                <h3 style={{ marginTop: '0.3rem' }}>Kafka Event Streaming: Live Patient Lab Simulation</h3>
              </div>
              <span className="badge badge-green">Streaming Active</span>
            </div>

            <p className="text-sm text-muted" style={{ marginTop: '0.5rem' }}>
              Emit a synthetic event into Kafka topic <code>lab.results</code>. The stream consumer will ingest the event, update the longitudinal fact lakehouse, and trigger instant trial matching and response re-evaluation.
            </p>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <label className="text-xs text-muted font-bold uppercase">Patient ID</label>
                <input type="text" value="P001024" disabled className="input-text" style={{ display: 'block', marginTop: '0.2rem', width: 120 }} />
              </div>
              <div>
                <label className="text-xs text-muted font-bold uppercase">Biomarker</label>
                <select value={simBiomarker} onChange={e => setSimBiomarker(e.target.value)} className="select-input" style={{ display: 'block', marginTop: '0.2rem' }}>
                  <option value="HbA1c">HbA1c (%)</option>
                  <option value="eGFR">eGFR (mL/min)</option>
                  <option value="Systolic_BP">Systolic BP (mmHg)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted font-bold uppercase">New Lab Measurement</label>
                <input 
                  type="number" 
                  step="0.1" 
                  value={simValue} 
                  onChange={e => setSimValue(e.target.value)} 
                  className="input-text" 
                  style={{ display: 'block', marginTop: '0.2rem', width: 140 }} 
                />
              </div>
              <div style={{ marginTop: '1.2rem' }}>
                <button 
                  className="btn btn-primary"
                  onClick={handleSimulateEvent}
                  disabled={publishing}
                >
                  {publishing ? 'Streaming Event...' : '⚡ Publish Event into Kafka Stream'}
                </button>
              </div>
            </div>

            {/* Stream Event Output Feed */}
            {streamingLog.length > 0 && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(0,0,0,0.3)', borderRadius: '8px' }}>
                <h4 className="text-xs text-teal font-bold uppercase">Stream Consumer Recalculation Output (Real-time)</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
                  {streamingLog.map((log, idx) => (
                    <div key={idx} style={{ padding: '0.75rem', background: 'rgba(0, 210, 186, 0.05)', borderLeft: '4px solid #00D2BA', borderRadius: '4px', fontSize: '0.85rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span className="font-bold text-white">Topic: {log.kafka_metadata?.topic} (Partition {log.kafka_metadata?.partition}, Offset {log.kafka_metadata?.offset})</span>
                        <span className="text-xs text-teal">{log.kafka_metadata?.timestamp}</span>
                      </div>
                      <div className="text-sm text-white" style={{ marginTop: '0.4rem' }}>
                        <strong>Delta:</strong> {log.instant_recalculation?.delta} • <strong>Updated Classification:</strong> <span className="badge badge-teal">{log.instant_recalculation?.updated_response_class}</span>
                      </div>
                      <div className="text-xs text-muted" style={{ marginTop: '0.3rem' }}>
                        {log.instant_recalculation?.message} • {log.instant_recalculation?.eligibility_re_evaluated}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Airflow DAGs status */}
          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <h3>Apache Airflow Pipeline Orchestration DAGs</h3>
              <span className="badge badge-blue">Scheduled & Event-Driven</span>
            </div>
            <div className="table-card" style={{ marginTop: '1rem', background: 'transparent', padding: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>DAG Identifier</th>
                    <th>Schedule</th>
                    <th>Last Execution</th>
                    <th>Execution State</th>
                    <th>Orchestrated Task Flow</th>
                  </tr>
                </thead>
                <tbody>
                  {pipeline.airflow_orchestration?.dags?.map((dag, idx) => (
                    <tr key={idx}>
                      <td className="font-bold text-white font-mono">{dag.dag_id}</td>
                      <td><code>{dag.schedule}</code></td>
                      <td>{dag.last_run}</td>
                      <td><span className="badge badge-green">{dag.state}</span></td>
                      <td className="text-xs text-muted font-mono">{dag.tasks?.join(' → ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </div>
  )
}
