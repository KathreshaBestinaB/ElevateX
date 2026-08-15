// API service layer — all calls to FastAPI backend

const BASE = import.meta.env.VITE_API_URL || ''

async function get(path) {
  const res = await fetch(`${BASE}${path}`)
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

async function post(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// ── Health ─────────────────────────────────────────────────
export const fetchHealth = () => get('/health')

// ── Patients ───────────────────────────────────────────────
export const fetchPatients = (limit = 50) => get(`/api/patients?limit=${limit}`)
export const fetchPatient  = (id) => get(`/api/patients/${id}`)

// ── Trials ─────────────────────────────────────────────────
export const fetchTrials = (limit = 50) => get(`/api/trials?limit=${limit}`)
export const fetchTrial  = (id) => get(`/api/trials/${id}`)

// ── Outcome Intelligence (6 questions) ─────────────────────
export const fetchOutcomeSummary   = (patientId) => get(`/api/patients/${patientId}/outcome-summary`)
export const fetchTimeline         = (patientId) => get(`/api/patients/${patientId}/timeline`)
export const fetchMedications      = (patientId) => get(`/api/patients/${patientId}/medications`)
export const fetchOutcomes         = (patientId) => get(`/api/patients/${patientId}/outcomes`)
export const fetchResponseAnalysis = (patientId) => get(`/api/patients/${patientId}/response-analysis`)
export const fetchAlternatives     = (patientId) => get(`/api/patients/${patientId}/alternative-pathways`)
export const fetchCohortResemblance= (patientId) => get(`/api/patients/${patientId}/cohort-resemblance`)
export const fetchSimilarPatients  = (patientId) => get(`/api/patients/${patientId}/similar`)

// ── Matching ───────────────────────────────────────────────
export const runMatching = (patientId, minScore = 0, limit = 20) =>
  post(`/api/matching/run?patient_id=${patientId}&min_score=${minScore}&limit=${limit}`, {})

// ── Analytics ──────────────────────────────────────────────
export const fetchPopulationAnalytics = () => get('/api/analytics/population')
export const fetchEnrollmentTrend     = () => get('/api/analytics/enrollment-trend')
export const fetchSparkStatus         = () => get('/api/analytics/spark-status')
export const fetchCohortAnalytics     = () => get('/api/analytics/cohorts')
export const fetchTrialAnalytics      = (trialId) => get(`/api/trials/${trialId}/analytics`)
export const fetchMedicationEffectiveness = (drugClass) => 
  get(`/api/medications/effectiveness${drugClass ? `?drug_class=${encodeURIComponent(drugClass)}` : ''}`)

// ── Research Q&A ───────────────────────────────────────────
export const askResearchQuestion = (question, context = {}) => 
  post('/api/research/question', { question, context })

// ── Document Intelligence ──────────────────────────────────
export const analyzeDocumentText = (text, documentName = 'clinical_protocol.txt') =>
  post('/api/documents/analyze', { text, document_name: documentName })

export const uploadDocument = async (file) => {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${BASE}/api/documents/upload`, {
    method: 'POST',
    body: formData,
  })
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`)
  return res.json()
}

// ── Compliance & Data Quality ───────────────────────────────
export const fetchComplianceDashboard = () => get('/api/compliance/dashboard')
export const fetchAuditLogs           = () => get('/api/compliance/audit-logs')
export const recordReviewAction       = (payload) => post('/api/compliance/review', payload)

// ── Pipeline & Kafka Streaming ─────────────────────────────
export const fetchPipelineStatus = () => get('/api/pipeline/status')
export const publishStreamEvent  = (eventPayload) => post('/api/pipeline/publish-event', eventPayload)
