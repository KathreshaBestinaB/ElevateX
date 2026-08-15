import { useState, useEffect } from 'react'
import { fetchPipelineStatus, publishStreamEvent, runPipelineDag, fetchStreamEvents } from '../services/api.js'

export default function DataPipelineMonitor() {
  const [pipeline, setPipeline] = useState(null)
  const [loading, setLoading] = useState(true)
  const [simBiomarker, setSimBiomarker] = useState('HbA1c')
  const [simValue, setSimValue] = useState(7.0)
  const [streamingLog, setStreamingLog] = useState([])
  const [publishing, setPublishing] = useState(false)
  const [runningDag, setRunningDag] = useState(null)
  const [dagRunHistory, setDagRunHistory] = useState([])
  const [streamTopic, setStreamTopic] = useState('lab.results')
  const [liveStreamEvents, setLiveStreamEvents] = useState([])

  const loadPipelineData = async () => {
    try {
      const res = await fetchPipelineStatus()
      setPipeline(res)
      if (res.airflow_orchestration?.recent_dag_runs) {
        setDagRunHistory(res.airflow_orchestration.recent_dag_runs)
      }
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  const loadStreamEvents = async (topic) => {
    try {
      const res = await fetchStreamEvents(topic, 10)
      if (res.recent_messages) {
        setLiveStreamEvents(res.recent_messages)
      }
    } catch (err) {
      console.error(err)
    }
  }

  useEffect(() => {
    loadPipelineData()
    loadStreamEvents(streamTopic)
  }, [])

  async function handleSimulateEvent() {
    setPublishing(true)
    try {
      const res = await publishStreamEvent({
        event_type: streamTopic,
        patient_id: 'P001024',
        biomarker: simBiomarker,
        value: parseFloat(simValue),
        unit: '%',
        trial_id: 'TR-02045',
        notes: 'Real-time streaming trigger event',
      })
      setStreamingLog(prev => [res, ...prev])
      loadPipelineData()
      loadStreamEvents(streamTopic)
    } catch (err) {
      console.error(err)
    } finally {
      setPublishing(false)
    }
  }

  async function handleRunDag(dagId) {
    setRunningDag(dagId)
    try {
      const res = await runPipelineDag(dagId)
      if (res.run) {
        setDagRunHistory(prev => [res.run, ...prev.filter(r => r.run_id !== res.run.run_id)])
      }
      loadPipelineData()
    } catch (err) {
      console.error(err)
    } finally {
      setRunningDag(null)
    }
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <div>
          <span className="badge badge-teal">Big Data Lakehouse & Streaming Engine</span>
          <h2>Spark, Kafka & Airflow Data Pipeline Monitor</h2>
          <p>Real-time distributed lakehouse metrics, persistent event-driven streaming broker, and live DAG execution.</p>
        </div>
        <button className="btn btn-outline" onClick={() => { loadPipelineData(); loadStreamEvents(streamTopic); }}>
          🔄 Refresh Metrics
        </button>
      </div>

      {loading ? (
        <div className="loading-state">Querying Apache Spark lakehouse & persistent stream broker metadata...</div>
      ) : pipeline ? (
        <>
          {/* Big Data Lakehouse Layer Architecture */}
          <div className="card" style={{ marginTop: '1rem' }}>
            <div className="card-header">
              <h3>Distributed Lakehouse Architecture (Apache Parquet)</h3>
              <span className="badge badge-purple">
                {pipeline.processed_metrics?.total_patients?.toLocaleString() || '1,000'} Patients Audited
              </span>
            </div>
            
            <div className="grid-3col" style={{ marginTop: '1rem', gap: '1rem' }}>
              <div style={{ padding: '1rem', background: 'rgba(217, 119, 6, 0.08)', border: '1px solid rgba(217, 119, 6, 0.3)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span className="font-bold text-amber text-sm uppercase">Bronze Layer (Raw)</span>
                  <span className="badge badge-amber text-xs">{pipeline.lakehouse?.bronze?.file_count || 5} Tables</span>
                </div>
                <p className="text-xs text-muted" style={{ marginTop: '0.4rem' }}>
                  Snappy-compressed raw clinical tables in local Parquet lakehouse storage.
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
                  <span className="badge badge-teal text-xs">Dimensional Aggs</span>
                </div>
                <p className="text-xs text-muted" style={{ marginTop: '0.4rem' }}>
                  Pre-aggregated dimensional tables powering instant research analytics and ML inference.
                </p>
                <div className="text-xs text-white" style={{ marginTop: '0.5rem' }}>
                  Tables: <code>population_kpis</code>, <code>drug_effectiveness</code>, <code>trial_kpis</code>, <code>cohort_stats</code>
                </div>
              </div>
            </div>
          </div>

          {/* Interactive Event Stream Demonstration & WAL Inspector */}
          <div className="card" style={{ marginTop: '1.5rem', border: '1px solid rgba(0, 210, 186, 0.4)' }}>
            <div className="card-header">
              <div>
                <span className="badge badge-teal">Persistent Streaming Engine</span>
                <h3 style={{ marginTop: '0.3rem' }}>Live Patient Event Publishing & Streaming Log</h3>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <span className="badge badge-green">Stream Active</span>
                <span className="badge badge-blue">{pipeline.kafka_streaming?.stream_broker_engine || 'SQLite WAL'}</span>
              </div>
            </div>

            <p className="text-sm text-muted" style={{ marginTop: '0.5rem' }}>
              Publish an event to the persistent event stream. Messages receive monotonic offsets and trigger instant response recalculation and persistent audit trail recording.
            </p>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', alignItems: 'center', flexWrap: 'wrap' }}>
              <div>
                <label className="text-xs text-muted font-bold uppercase">Topic</label>
                <select 
                  value={streamTopic} 
                  onChange={e => { setStreamTopic(e.target.value); loadStreamEvents(e.target.value); }} 
                  className="select-input" 
                  style={{ display: 'block', marginTop: '0.2rem' }}
                >
                  <option value="lab.results">lab.results</option>
                  <option value="patient.events">patient.events</option>
                  <option value="medication.events">medication.events</option>
                  <option value="outcome.events">outcome.events</option>
                </select>
              </div>
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
                  <option value="BMI">BMI (kg/m²)</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-muted font-bold uppercase">New Lab Value</label>
                <input 
                  type="number" 
                  step="0.1" 
                  value={simValue} 
                  onChange={e => setSimValue(e.target.value)} 
                  className="input-text" 
                  style={{ display: 'block', marginTop: '0.2rem', width: 130 }} 
                />
              </div>
              <div style={{ marginTop: '1.2rem' }}>
                <button 
                  className="btn btn-primary"
                  onClick={handleSimulateEvent}
                  disabled={publishing}
                >
                  {publishing ? 'Publishing to Stream...' : '⚡ Publish Event into Stream'}
                </button>
              </div>
            </div>

            {/* Stream Event Output Feed */}
            {streamingLog.length > 0 && (
              <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(0,0,0,0.3)', borderRadius: '8px' }}>
                <h4 className="text-xs text-teal font-bold uppercase">Instant Consumer Recalculation (Live)</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '0.5rem' }}>
                  {streamingLog.map((log, idx) => (
                    <div key={idx} style={{ padding: '0.75rem', background: 'rgba(0, 210, 186, 0.05)', borderLeft: '4px solid #00D2BA', borderRadius: '4px', fontSize: '0.85rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                        <span className="font-bold text-white">
                          Topic: <code>{log.kafka_metadata?.topic}</code> (Partition {log.kafka_metadata?.partition}, Offset <strong>#{log.kafka_metadata?.offset}</strong>)
                        </span>
                        <span className="text-xs text-teal">{log.kafka_metadata?.timestamp?.split('T')[1]?.slice(0, 8)} UTC</span>
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

          {/* Airflow DAG Orchestration & Execution Engine */}
          <div className="card" style={{ marginTop: '1.5rem' }}>
            <div className="card-header">
              <div>
                <span className="badge badge-blue">Pipeline Orchestration</span>
                <h3 style={{ marginTop: '0.3rem' }}>Apache Airflow / ETL Pipeline DAGs</h3>
              </div>
              <span className="badge badge-green">Engine Online</span>
            </div>

            <p className="text-sm text-muted" style={{ marginTop: '0.5rem' }}>
              Execute lakehouse transformation and ML feature pipelines on-demand. Task run durations and step states are recorded in persistent run logs.
            </p>

            <div className="table-card" style={{ marginTop: '1rem', background: 'transparent', padding: 0 }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>DAG Identifier</th>
                    <th>Schedule</th>
                    <th>Last Execution</th>
                    <th>Status</th>
                    <th>Task Flow</th>
                    <th style={{ textAlign: 'right' }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pipeline.airflow_orchestration?.dags?.map((dag, idx) => (
                    <tr key={idx}>
                      <td className="font-bold text-white font-mono">{dag.dag_id}</td>
                      <td><code>{dag.schedule}</code></td>
                      <td className="text-xs text-muted">{dag.last_run}</td>
                      <td><span className="badge badge-green">{dag.state}</span></td>
                      <td className="text-xs text-muted font-mono">{dag.tasks?.join(' → ')}</td>
                      <td style={{ textAlign: 'right' }}>
                        <button
                          className="btn btn-sm btn-outline"
                          onClick={() => handleRunDag(dag.dag_id)}
                          disabled={runningDag === dag.dag_id}
                          style={{ padding: '0.3rem 0.75rem', fontSize: '0.75rem' }}
                        >
                          {runningDag === dag.dag_id ? '⏳ Executing...' : '▶ Run DAG'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Live DAG Run History */}
            {dagRunHistory.length > 0 && (
              <div style={{ marginTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.08)', paddingTop: '1rem' }}>
                <h4 className="text-xs text-muted font-bold uppercase">Recent Pipeline Execution Runs</h4>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.75rem' }}>
                  {dagRunHistory.slice(0, 4).map((run, i) => (
                    <div key={i} style={{ padding: '0.6rem 0.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '6px', fontSize: '0.8rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <span className="font-bold text-white font-mono">{run.run_id}</span>
                        <span className="text-xs text-muted" style={{ marginLeft: '0.5rem' }}>({run.dag_id})</span>
                      </div>
                      <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                        <span className="text-xs text-teal">{run.duration_ms} ms</span>
                        <span className="badge badge-green text-xs">{run.state}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      ) : null}
    </div>
  )
}

