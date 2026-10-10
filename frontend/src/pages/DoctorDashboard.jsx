import { useState, useEffect, useRef } from 'react'
import { Routes, Route, Navigate, useNavigate, useParams, Link } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Modal from '../components/Modal'
import Spinner from '../components/Spinner'
import api from '../api/client'
import toast from 'react-hot-toast'
import {
  Users, BookOpen, Search, ChevronRight, Brain, FlaskConical,
  AlertTriangle, CheckCircle, Clock, Send, Plus, ArrowLeft,
  Pill, FileText, Activity,
} from 'lucide-react'

// ── Patient List ──────────────────────────────────────────────────────────────

function PatientListPage() {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    api.get('/patients/')
      .then((r) => setPatients(r.data))
      .catch(() => toast.error('Failed to load patients'))
      .finally(() => setLoading(false))
  }, [])

  const filtered = patients.filter(
    (p) =>
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.phone?.includes(search),
  )

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">My Patients</h1>
        <p className="text-sm text-gray-500 mt-0.5">Select a patient to view records or run an AI diagnosis</p>
      </div>

      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input className="input pl-9" placeholder="Search by name or phone..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <Users size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">No patients found</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((p) => (
            <button
              key={p.id}
              onClick={() => navigate(`/doctor/patients/${p.id}`)}
              className="card p-4 flex items-center gap-4 w-full text-left hover:border-primary-300 hover:shadow-md transition-all"
            >
              <div className="w-11 h-11 rounded-full bg-primary-100 flex items-center justify-center font-semibold text-primary-700 text-base flex-shrink-0">
                {p.name?.[0] || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900">{p.name}</p>
                <p className="text-sm text-gray-500">{p.gender} · {p.blood_group || '—'} · {p.phone || '—'}</p>
              </div>
              <span className={p.is_active ? 'badge-green' : 'badge-red'}>{p.is_active ? 'Active' : 'Inactive'}</span>
              <ChevronRight size={18} className="text-gray-400 flex-shrink-0" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Patient Detail ────────────────────────────────────────────────────────────

function PatientDetailPage() {
  const { patientId } = useParams()
  const [patient, setPatient] = useState(null)
  const [medications, setMedications] = useState([])
  const [labs, setLabs] = useState([])
  const [diagnoses, setDiagnoses] = useState([])
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState('overview')
  const navigate = useNavigate()

  async function load() {
    try {
      const [pRes, mRes, lRes, dRes] = await Promise.all([
        api.get(`/patients/${patientId}`),
        api.get(`/patients/${patientId}/medications`),
        api.get(`/patients/${patientId}/labs`),
        api.get(`/diagnosis/patient/${patientId}`),
      ])
      setPatient(pRes.data)
      setMedications(mRes.data)
      setLabs(lRes.data)
      setDiagnoses(dRes.data)
    } catch { toast.error('Failed to load patient data') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [patientId])

  if (loading) return <div className="flex justify-center py-24"><Spinner size="lg" /></div>
  if (!patient) return <div className="p-6 text-gray-500">Patient not found</div>

  const tabs = [
    { key: 'overview', label: 'Overview', icon: <FileText size={15} /> },
    { key: 'labs', label: `Labs (${labs.length})`, icon: <FlaskConical size={15} /> },
    { key: 'diagnoses', label: `Diagnoses (${diagnoses.length})`, icon: <Brain size={15} /> },
    { key: 'ai', label: 'AI Diagnosis', icon: <Activity size={15} /> },
  ]

  const age = patient.date_of_birth
    ? Math.floor((Date.now() - new Date(patient.date_of_birth)) / (365.25 * 24 * 3600 * 1000))
    : null

  return (
    <div className="p-6 max-w-5xl mx-auto">
      {/* Back + Header */}
      <button onClick={() => navigate('/doctor/patients')} className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 mb-4 transition-colors">
        <ArrowLeft size={15} /> Back to patients
      </button>

      <div className="card p-5 mb-6">
        <div className="flex items-start gap-4">
          <div className="w-14 h-14 rounded-2xl bg-primary-100 flex items-center justify-center font-bold text-primary-700 text-xl flex-shrink-0">
            {patient.name?.[0] || '?'}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-xl font-bold text-gray-900">{patient.name}</h1>
              <span className={patient.is_active ? 'badge-green' : 'badge-red'}>{patient.is_active ? 'Active' : 'Inactive'}</span>
            </div>
            <div className="flex flex-wrap gap-4 mt-1 text-sm text-gray-600">
              {age && <span>{age} years old</span>}
              <span>{patient.gender}</span>
              {patient.blood_group && <span className="font-medium text-red-600">Blood: {patient.blood_group}</span>}
              {patient.phone && <span>{patient.phone}</span>}
            </div>
            {patient.allergies?.length > 0 && (
              <div className="flex items-center gap-2 mt-2 p-2 bg-red-50 rounded-lg">
                <AlertTriangle size={14} className="text-red-500 flex-shrink-0" />
                <span className="text-sm text-red-700 font-medium">Allergies: {patient.allergies.join(', ')}</span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 bg-gray-100 rounded-xl p-1 w-fit overflow-x-auto">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors ${
              tab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === 'overview' && <OverviewTab patient={patient} medications={medications} onReload={load} />}
      {tab === 'labs' && <LabsTab patientId={patientId} labs={labs} onReload={load} />}
      {tab === 'diagnoses' && <DiagnosesTab diagnoses={diagnoses} onReload={load} />}
      {tab === 'ai' && <AIDiagnosisTab patient={patient} medications={medications} patientId={patientId} onReload={() => { load(); setTab('diagnoses') }} />}
    </div>
  )
}

function OverviewTab({ patient, medications, onReload }) {
  const current = medications.filter((m) => m.is_current)
  const past = medications.filter((m) => !m.is_current)
  const [showAddMed, setShowAddMed] = useState(false)

  return (
    <div className="space-y-4">
      {/* Medical History */}
      <div className="card p-5">
        <h3 className="font-semibold text-gray-900 mb-3">Medical History</h3>
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-gray-500 mb-1">Past Diseases</p>
            <p className="text-gray-800">{patient.past_diseases?.join(', ') || 'None reported'}</p>
          </div>
          <div>
            <p className="text-gray-500 mb-1">Past Surgeries</p>
            <p className="text-gray-800">{patient.past_surgeries?.join(', ') || 'None reported'}</p>
          </div>
          <div>
            <p className="text-gray-500 mb-1">Allergies</p>
            <p className="text-gray-800">{patient.allergies?.join(', ') || 'None reported'}</p>
          </div>
          <div>
            <p className="text-gray-500 mb-1">Family History</p>
            <p className="text-gray-800">{patient.family_history || 'Not provided'}</p>
          </div>
        </div>
      </div>

      {/* Current Medications */}
      <div className="card p-5">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold text-gray-900">Current Medications</h3>
          <button className="btn-secondary text-xs" onClick={() => setShowAddMed(true)}><Plus size={13} /> Add</button>
        </div>
        {current.length === 0 ? (
          <p className="text-sm text-gray-500">No current medications</p>
        ) : (
          <div className="space-y-2">
            {current.map((m) => (
              <div key={m.id} className="flex items-center gap-3 p-3 bg-green-50 rounded-lg">
                <Pill size={16} className="text-green-600 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-900">{m.medicine_name}</p>
                  <p className="text-xs text-gray-500">{m.dosage} · {m.frequency} · {m.route}</p>
                </div>
                {m.start_date && <span className="text-xs text-gray-400">Since {m.start_date}</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {showAddMed && (
        <AddMedicationModal
          patientId={patient.id}
          onClose={() => setShowAddMed(false)}
          onAdded={() => { setShowAddMed(false); onReload() }}
        />
      )}
    </div>
  )
}

function AddMedicationModal({ patientId, onClose, onAdded }) {
  const [form, setForm] = useState({ medicine_name: '', dosage: '', frequency: '', route: 'Oral', start_date: '', is_current: true, notes: '' })
  const [loading, setLoading] = useState(false)
  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault(); setLoading(true)
    try {
      await api.post(`/patients/${patientId}/medications`, form)
      toast.success('Medication added'); onAdded()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
    finally { setLoading(false) }
  }

  return (
    <Modal title="Add Medication" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div><label className="label">Medicine Name *</label><input className="input" value={form.medicine_name} onChange={f('medicine_name')} required /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Dosage *</label><input className="input" placeholder="e.g. 500mg" value={form.dosage} onChange={f('dosage')} required /></div>
          <div><label className="label">Frequency *</label><input className="input" placeholder="e.g. Twice daily" value={form.frequency} onChange={f('frequency')} required /></div>
          <div>
            <label className="label">Route</label>
            <select className="input" value={form.route} onChange={f('route')}>
              {['Oral', 'IV', 'IM', 'Topical', 'Inhaled', 'Subcutaneous', 'Other'].map(r => <option key={r}>{r}</option>)}
            </select>
          </div>
          <div><label className="label">Start Date</label><input type="date" className="input" value={form.start_date} onChange={f('start_date')} /></div>
        </div>
        <div><label className="label">Notes</label><textarea className="input" rows={2} value={form.notes} onChange={f('notes')} /></div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Saving...' : 'Add Medication'}</button>
        </div>
      </form>
    </Modal>
  )
}

function LabsTab({ patientId, labs, onReload }) {
  const [showAdd, setShowAdd] = useState(false)
  const [flagging, setFlagging] = useState(null)
  const [approving, setApproving] = useState(null)

  async function flagAlert(lab) {
    setFlagging(lab.id)
    try {
      await api.post(`/patients/${patientId}/labs/${lab.id}/flag-alert`)
      toast.success('Alert flagged for approval'); onReload()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
    finally { setFlagging(null) }
  }

  async function approveAlert(lab) {
    setApproving(lab.id)
    try {
      await api.post(`/patients/${patientId}/labs/${lab.id}/approve-alert`)
      toast.success('Alert approved and sent'); onReload()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
    finally { setApproving(null) }
  }

  const alertBadge = (status) => {
    const map = { none: null, pending: <span className="badge-amber">Alert Pending</span>, approved: <span className="badge-blue">Alert Approved</span>, sent: <span className="badge-green">Alert Sent</span> }
    return map[status] || null
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-semibold text-gray-900">Lab Results</h3>
        <button className="btn-primary text-xs" onClick={() => setShowAdd(true)}><Plus size={13} /> Add Result</button>
      </div>

      {labs.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          <FlaskConical size={32} className="mx-auto mb-2 text-gray-300" />
          <p className="font-medium">No lab results yet</p>
        </div>
      ) : (
        <div className="space-y-3">
          {labs.map((lab) => (
            <div key={lab.id} className={`card p-4 ${lab.is_abnormal ? 'border-red-200 bg-red-50/30' : ''}`}>
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="font-medium text-gray-900">{lab.test_name}</p>
                    {lab.is_abnormal && <span className="badge-red">Abnormal</span>}
                    {alertBadge(lab.alert_status)}
                  </div>
                  <p className="text-lg font-semibold text-gray-800 mt-1">
                    {lab.result_value} <span className="text-sm font-normal text-gray-500">{lab.unit}</span>
                  </p>
                  {lab.reference_range && <p className="text-xs text-gray-500">Reference: {lab.reference_range}</p>}
                  {lab.notes && <p className="text-sm text-gray-600 mt-1">{lab.notes}</p>}
                  <p className="text-xs text-gray-400 mt-1">{lab.test_date}</p>
                </div>
                <div className="flex flex-col gap-2 flex-shrink-0">
                  {lab.is_abnormal && lab.alert_status === 'none' && (
                    <button className="btn-secondary text-xs" onClick={() => flagAlert(lab)} disabled={flagging === lab.id}>
                      <AlertTriangle size={12} className="text-amber-500" />
                      {flagging === lab.id ? 'Flagging...' : 'Flag Alert'}
                    </button>
                  )}
                  {lab.alert_status === 'pending' && (
                    <button className="btn-primary text-xs" onClick={() => approveAlert(lab)} disabled={approving === lab.id}>
                      <Send size={12} />
                      {approving === lab.id ? 'Sending...' : 'Approve & Send'}
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <AddLabModal patientId={patientId} onClose={() => setShowAdd(false)} onAdded={() => { setShowAdd(false); onReload() }} />
      )}
    </div>
  )
}

function AddLabModal({ patientId, onClose, onAdded }) {
  const [form, setForm] = useState({ test_name: '', test_date: new Date().toISOString().slice(0, 10), result_value: '', unit: '', reference_range: '', is_abnormal: false, notes: '' })
  const [loading, setLoading] = useState(false)
  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault(); setLoading(true)
    try {
      await api.post(`/patients/${patientId}/labs`, form)
      toast.success('Lab result added'); onAdded()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
    finally { setLoading(false) }
  }

  return (
    <Modal title="Add Lab Result" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div><label className="label">Test Name *</label><input className="input" value={form.test_name} onChange={f('test_name')} required /></div>
        <div className="grid grid-cols-2 gap-3">
          <div><label className="label">Result Value *</label><input className="input" value={form.result_value} onChange={f('result_value')} required /></div>
          <div><label className="label">Unit</label><input className="input" placeholder="e.g. mg/dL" value={form.unit} onChange={f('unit')} /></div>
          <div><label className="label">Reference Range</label><input className="input" placeholder="e.g. 70-110" value={form.reference_range} onChange={f('reference_range')} /></div>
          <div><label className="label">Test Date *</label><input type="date" className="input" value={form.test_date} onChange={f('test_date')} required /></div>
        </div>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" className="w-4 h-4 rounded accent-red-500" checked={form.is_abnormal} onChange={(e) => setForm({ ...form, is_abnormal: e.target.checked })} />
          <span className="text-sm text-gray-700 font-medium">Mark as Abnormal</span>
        </label>
        <div><label className="label">Notes</label><textarea className="input" rows={2} value={form.notes} onChange={f('notes')} /></div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Adding...' : 'Add Result'}</button>
        </div>
      </form>
    </Modal>
  )
}

function DiagnosesTab({ diagnoses, onReload }) {
  const [deciding, setDeciding] = useState(null)

  async function decide(diag, decision, finalDiagnosis, note) {
    try {
      await api.post(`/diagnosis/${diag.id}/decide`, { decision, final_diagnosis: finalDiagnosis, modification_note: note })
      toast.success('Decision recorded'); onReload(); setDeciding(null)
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
  }

  const statusBadge = (d) => {
    const m = { pending: <span className="badge-amber flex items-center gap-1"><Clock size={11} /> Pending</span>, accepted: <span className="badge-green flex items-center gap-1"><CheckCircle size={11} /> Accepted</span>, modified: <span className="badge-blue flex items-center gap-1"><CheckCircle size={11} /> Modified</span> }
    return m[d] || null
  }

  return (
    <div>
      <h3 className="font-semibold text-gray-900 mb-4">Diagnosis History</h3>
      {diagnoses.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          <Brain size={32} className="mx-auto mb-2 text-gray-300" />
          <p className="font-medium">No diagnoses yet</p>
          <p className="text-sm mt-1">Use the AI Diagnosis tab to get a suggestion</p>
        </div>
      ) : (
        <div className="space-y-4">
          {diagnoses.map((d) => (
            <div key={d.id} className="card p-5">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <div className="flex items-center gap-2 mb-1">{statusBadge(d.decision)}</div>
                  <p className="font-medium text-gray-900">{d.query}</p>
                  <p className="text-xs text-gray-400 mt-0.5">{new Date(d.suggested_at).toLocaleString()}</p>
                </div>
                {d.decision === 'pending' && (
                  <button className="btn-primary text-xs flex-shrink-0" onClick={() => setDeciding(d)}>
                    <CheckCircle size={13} /> Record Decision
                  </button>
                )}
              </div>

              {d.final_diagnosis && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-3 mb-3">
                  <p className="text-xs font-semibold text-green-700 mb-1">FINAL DIAGNOSIS</p>
                  <p className="text-sm text-gray-800">{d.final_diagnosis}</p>
                  {d.modification_note && <p className="text-xs text-gray-500 mt-1 italic">{d.modification_note}</p>}
                </div>
              )}

              <details className="group">
                <summary className="text-xs text-primary-600 cursor-pointer hover:text-primary-700 font-medium">
                  Show AI suggestion
                </summary>
                <div className="mt-3 p-3 bg-blue-50 rounded-lg text-sm text-gray-700 leading-relaxed whitespace-pre-wrap">
                  {d.ai_suggestion}
                </div>
                {d.citations?.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-gray-500 mb-1">Citations (frozen at time of suggestion)</p>
                    {d.citations.map((c, i) => (
                      <p key={i} className="text-xs text-gray-500">
                        [{i + 1}] {c.book_title}, p.{c.page_number}{c.author ? ` — ${c.author}` : ''}
                      </p>
                    ))}
                  </div>
                )}
              </details>
            </div>
          ))}
        </div>
      )}

      {deciding && <DecisionModal diag={deciding} onDecide={decide} onClose={() => setDeciding(null)} />}
    </div>
  )
}

function DecisionModal({ diag, onDecide, onClose }) {
  const [decision, setDecision] = useState('accepted')
  const [finalDiagnosis, setFinalDiagnosis] = useState('')
  const [note, setNote] = useState('')
  const [loading, setLoading] = useState(false)

  async function submit(e) {
    e.preventDefault(); setLoading(true)
    await onDecide(diag, decision, finalDiagnosis, note)
    setLoading(false)
  }

  return (
    <Modal title="Record Clinical Decision" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-sm text-amber-800">
          <strong>AI Query:</strong> {diag.query}
        </div>
        <div>
          <label className="label">Decision</label>
          <div className="flex gap-3">
            {[['accepted', 'Accept AI suggestion'], ['modified', 'Modify / Override']].map(([v, l]) => (
              <label key={v} className={`flex-1 flex items-center gap-2 p-3 border rounded-lg cursor-pointer transition-colors ${decision === v ? 'border-primary-400 bg-primary-50' : 'border-gray-200'}`}>
                <input type="radio" className="accent-primary-600" value={v} checked={decision === v} onChange={() => setDecision(v)} />
                <span className="text-sm font-medium">{l}</span>
              </label>
            ))}
          </div>
        </div>
        <div>
          <label className="label">Final Diagnosis *</label>
          <textarea className="input" rows={3} value={finalDiagnosis} onChange={(e) => setFinalDiagnosis(e.target.value)} placeholder="Enter the doctor's final clinical diagnosis..." required />
        </div>
        {decision === 'modified' && (
          <div>
            <label className="label">Modification Note</label>
            <textarea className="input" rows={2} value={note} onChange={(e) => setNote(e.target.value)} placeholder="Explain why you modified the AI suggestion..." />
          </div>
        )}
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Saving...' : 'Record Decision'}</button>
        </div>
      </form>
    </Modal>
  )
}

function AIDiagnosisTab({ patient, medications, patientId, onReload }) {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState(null)

  async function runDiagnosis() {
    if (!query.trim()) return
    setLoading(true); setResult(null)
    try {
      const res = await api.post('/diagnosis/query', { patient_id: patientId, query })
      setResult(res.data)
      toast.success('AI analysis complete — review and record your decision in the Diagnoses tab')
    } catch (err) { toast.error(err.response?.data?.detail || 'AI query failed') }
    finally { setLoading(false) }
  }

  return (
    <div className="space-y-4">
      {/* Disclaimer */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex gap-3">
        <AlertTriangle size={18} className="text-amber-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-amber-800">AI Advisory Only</p>
          <p className="text-sm text-amber-700 mt-0.5">
            This is an AI-generated suggestion based on the patient's records and the medical knowledge base.
            The treating physician must make all clinical decisions.
          </p>
        </div>
      </div>

      {/* Query input */}
      <div className="card p-5">
        <label className="label">Clinical Query</label>
        <textarea
          className="input mb-3"
          rows={3}
          placeholder="Describe symptoms, concerns, or ask a clinical question about this patient..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button
          className="btn-primary"
          onClick={runDiagnosis}
          disabled={loading || !query.trim()}
        >
          {loading ? (
            <><Spinner size="sm" /> Analyzing patient data...</>
          ) : (
            <><Brain size={16} /> Run AI Analysis</>
          )}
        </button>
      </div>

      {/* Result */}
      {result && (
        <div className="card p-5">
          <div className="flex items-center gap-2 mb-3">
            <Brain size={18} className="text-primary-600" />
            <h3 className="font-semibold text-gray-900">AI Analysis</h3>
            <span className="badge-blue ml-auto">Advisory</span>
          </div>
          <div className="text-sm text-gray-700 leading-relaxed whitespace-pre-wrap bg-blue-50 rounded-lg p-4">
            {result.ai_suggestion}
          </div>

          {result.citations?.length > 0 && (
            <div className="mt-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Evidence Sources</p>
              <div className="space-y-1.5">
                {result.citations.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs text-gray-600 bg-gray-50 rounded p-2">
                    <span className="font-semibold text-primary-600">[{i + 1}]</span>
                    <span>{c.book_title}{c.author ? `, ${c.author}` : ''} — Page {c.page_number}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="mt-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <p className="text-xs text-green-700">
              Go to the <strong>Diagnoses</strong> tab to record your clinical decision on this AI suggestion.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}

// ── Knowledge Base ────────────────────────────────────────────────────────────

function KnowledgeBasePage() {
  const [books, setBooks] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef()

  async function load() {
    try {
      const res = await api.get('/knowledge/books')
      setBooks(res.data)
    } catch { toast.error('Failed to load knowledge base') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function upload(e) {
    const file = e.target.files[0]
    if (!file) return
    if (!file.name.endsWith('.pdf')) { toast.error('Only PDF files are supported'); return }
    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)
    formData.append('title', file.name.replace('.pdf', ''))
    try {
      await api.post('/knowledge/books', formData, { headers: { 'Content-Type': 'multipart/form-data' } })
      toast.success('PDF uploaded — processing in background')
      load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Upload failed') }
    finally { setUploading(false); e.target.value = '' }
  }

  async function deleteBook(book) {
    try {
      await api.delete(`/knowledge/books/${book.id}`)
      toast.success('Book removed'); load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
  }

  const statusBadge = (s) => {
    const m = { pending: <span className="badge-gray">Pending</span>, processing: <span className="badge-amber">Processing...</span>, processed: <span className="badge-green">Ready</span>, failed: <span className="badge-red">Failed</span> }
    return m[s] || null
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Knowledge Base</h1>
          <p className="text-sm text-gray-500 mt-0.5">Upload medical books and references used for AI diagnosis</p>
        </div>
        <div>
          <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={upload} />
          <button className="btn-primary" onClick={() => fileRef.current.click()} disabled={uploading}>
            <Plus size={16} /> {uploading ? 'Uploading...' : 'Upload PDF'}
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : books.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <BookOpen size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">No books in knowledge base</p>
          <p className="text-sm mt-1">Upload a medical PDF to enable AI-assisted diagnoses</p>
        </div>
      ) : (
        <div className="space-y-3">
          {books.map((b) => (
            <div key={b.id} className="card p-4 flex items-center gap-4">
              <BookOpen size={24} className="text-primary-600 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-medium text-gray-900">{b.title}</p>
                  {statusBadge(b.upload_status)}
                </div>
                {b.author && <p className="text-sm text-gray-500">{b.author}</p>}
                {b.chunk_count > 0 && <p className="text-xs text-gray-400">{b.chunk_count} chunks indexed</p>}
                {b.error_message && <p className="text-xs text-red-500 mt-0.5">{b.error_message}</p>}
              </div>
              <button
                className="text-xs text-red-600 hover:text-red-700 font-medium px-2 py-1 rounded hover:bg-red-50 transition-colors"
                onClick={() => deleteBook(b)}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Layout ────────────────────────────────────────────────────────────────────

const navItems = [
  { to: '/doctor/patients', label: 'Patients', icon: <Users size={18} /> },
  { to: '/doctor/knowledge', label: 'Knowledge Base', icon: <BookOpen size={18} /> },
]

export default function DoctorDashboard() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar items={navItems} title="MedAI Doctor" subtitle="Clinical Dashboard" />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route index element={<Navigate to="/doctor/patients" replace />} />
          <Route path="patients" element={<PatientListPage />} />
          <Route path="patients/:patientId" element={<PatientDetailPage />} />
          <Route path="knowledge" element={<KnowledgeBasePage />} />
          <Route path="*" element={<Navigate to="/doctor/patients" replace />} />
        </Routes>
      </main>
    </div>
  )
}
