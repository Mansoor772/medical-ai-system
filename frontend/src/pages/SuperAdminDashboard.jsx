import { useState, useEffect } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Modal from '../components/Modal'
import ConfirmDialog from '../components/ConfirmDialog'
import Spinner from '../components/Spinner'
import api from '../api/client'
import toast from 'react-hot-toast'
import {
  Users, Stethoscope, ClipboardList, Shield, Search,
  Plus, UserX, UserCheck, Download, ChevronRight, AlertCircle,
} from 'lucide-react'

// ── Doctors tab ──────────────────────────────────────────────────────────────

function DoctorsTab() {
  const [doctors, setDoctors] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [confirm, setConfirm] = useState(null)

  async function load() {
    try {
      const res = await api.get('/doctors/')
      setDoctors(res.data)
    } catch { toast.error('Failed to load doctors') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function toggleStatus(d) {
    try {
      const ep = d.is_active ? `/doctors/${d.id}/deactivate` : `/doctors/${d.id}/reactivate`
      await api.post(ep)
      toast.success(`Doctor ${d.is_active ? 'deactivated' : 'reactivated'}`)
      load()
    } catch (err) { toast.error(err.response?.data?.detail || 'Action failed') }
    setConfirm(null)
  }

  const filtered = doctors.filter(
    (d) =>
      d.name.toLowerCase().includes(search.toLowerCase()) ||
      d.specialization?.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Doctors</h2>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={15} /> Add Doctor
        </button>
      </div>

      <div className="relative mb-3">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input className="input pl-9" placeholder="Search by name or specialization..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Stethoscope size={36} className="mx-auto mb-2 text-gray-300" />
          <p className="font-medium">No doctors registered yet</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((d) => (
            <div key={d.id} className="card p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-blue-100 flex items-center justify-center font-semibold text-blue-700 text-sm flex-shrink-0">
                {d.name[0]}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{d.name}</p>
                  <span className={d.is_active ? 'badge-green' : 'badge-red'}>{d.is_active ? 'Active' : 'Inactive'}</span>
                </div>
                <p className="text-sm text-gray-500">{d.specialization || 'General'} · {d.email}</p>
              </div>
              <button
                className={d.is_active ? 'btn-secondary text-xs' : 'btn-secondary text-xs text-green-600'}
                onClick={() => setConfirm(d)}
              >
                {d.is_active ? <UserX size={13} /> : <UserCheck size={13} />}
                {d.is_active ? 'Deactivate' : 'Reactivate'}
              </button>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateDoctorModal onClose={() => setShowCreate(false)} onCreated={load} />}
      {confirm && (
        <ConfirmDialog
          title={confirm.is_active ? 'Deactivate Doctor' : 'Reactivate Doctor'}
          message={`Are you sure you want to ${confirm.is_active ? 'deactivate' : 'reactivate'} Dr. ${confirm.name}?`}
          confirmLabel={confirm.is_active ? 'Deactivate' : 'Reactivate'}
          danger={confirm.is_active}
          onConfirm={() => toggleStatus(confirm)}
          onClose={() => setConfirm(null)}
        />
      )}
    </div>
  )
}

function CreateDoctorModal({ onClose, onCreated }) {
  const [form, setForm] = useState({ name: '', email: '', password: '', phone: '', license_number: '', specialization: '', qualification: '' })
  const [loading, setLoading] = useState(false)
  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/doctors/', form)
      toast.success('Doctor registered successfully')
      onCreated(); onClose()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to register doctor') }
    finally { setLoading(false) }
  }

  return (
    <Modal title="Register Doctor" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="label">Full Name *</label><input className="input" value={form.name} onChange={f('name')} required /></div>
          <div><label className="label">Email *</label><input type="email" className="input" value={form.email} onChange={f('email')} required /></div>
          <div><label className="label">Phone</label><input className="input" value={form.phone} onChange={f('phone')} /></div>
          <div className="col-span-2"><label className="label">Password *</label><input type="password" className="input" value={form.password} onChange={f('password')} required minLength={8} /></div>
          <div><label className="label">License No. *</label><input className="input" value={form.license_number} onChange={f('license_number')} required /></div>
          <div><label className="label">Specialization</label><input className="input" value={form.specialization} onChange={f('specialization')} /></div>
          <div className="col-span-2"><label className="label">Qualification</label><input className="input" value={form.qualification} onChange={f('qualification')} /></div>
        </div>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Registering...' : 'Register Doctor'}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Patients tab ─────────────────────────────────────────────────────────────

function PatientsTab() {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  async function load() {
    try {
      const res = await api.get('/patients/')
      setPatients(res.data)
    } catch { toast.error('Failed to load patients') }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  async function exportPatient(p) {
    try {
      const res = await api.get(`/compliance/patients/${p.id}/export`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a'); a.href = url; a.download = `patient_${p.id}_export.json`; a.click()
      toast.success('Export downloaded')
    } catch { toast.error('Export failed') }
  }

  const filtered = patients.filter(
    (p) =>
      p.name?.toLowerCase().includes(search.toLowerCase()) ||
      p.cnic?.includes(search) ||
      p.phone?.includes(search),
  )

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">Patients</h2>
        <button className="btn-primary" onClick={() => setShowCreate(true)}><Plus size={15} /> Register Patient</button>
      </div>

      <div className="relative mb-3">
        <Search size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input className="input pl-9" placeholder="Search by name, CNIC or phone..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Users size={36} className="mx-auto mb-2 text-gray-300" />
          <p className="font-medium">No patients registered</p>
        </div>
      ) : (
        <div className="space-y-2">
          {filtered.map((p) => (
            <div key={p.id} className="card p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-full bg-green-100 flex items-center justify-center font-semibold text-green-700 text-sm flex-shrink-0">
                {p.name?.[0] || '?'}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{p.name}</p>
                  <span className={p.is_active ? 'badge-green' : 'badge-red'}>{p.is_active ? 'Active' : 'Anonymized'}</span>
                </div>
                <p className="text-sm text-gray-500">{p.gender} · {p.blood_group || 'Blood group unknown'} · {p.phone}</p>
              </div>
              <button className="btn-secondary text-xs" onClick={() => exportPatient(p)}>
                <Download size={13} /> Export (PDPA)
              </button>
            </div>
          ))}
        </div>
      )}

      {showCreate && <RegisterPatientModal onClose={() => setShowCreate(false)} onCreated={load} />}
    </div>
  )
}

function RegisterPatientModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '', date_of_birth: '', gender: 'Male', blood_group: '', cnic: '',
    phone: '', email: '', address: '', emergency_contact_name: '',
    emergency_contact_phone: '', emergency_contact_relation: '',
    consent_text: 'I consent to my personal and medical information being stored and processed for clinical care purposes under PDPA regulations.',
  })
  const [loading, setLoading] = useState(false)
  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/patients/', form)
      toast.success('Patient registered')
      onCreated(); onClose()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
    finally { setLoading(false) }
  }

  return (
    <Modal title="Register Patient" onClose={onClose} size="xl">
      <form onSubmit={submit} className="space-y-4">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Personal Information</p>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2"><label className="label">Full Name *</label><input className="input" value={form.name} onChange={f('name')} required /></div>
          <div><label className="label">Date of Birth *</label><input type="date" className="input" value={form.date_of_birth} onChange={f('date_of_birth')} required /></div>
          <div>
            <label className="label">Gender *</label>
            <select className="input" value={form.gender} onChange={f('gender')}>
              <option>Male</option><option>Female</option><option>Other</option>
            </select>
          </div>
          <div><label className="label">CNIC</label><input className="input" value={form.cnic} onChange={f('cnic')} placeholder="00000-0000000-0" /></div>
          <div><label className="label">Blood Group</label>
            <select className="input" value={form.blood_group} onChange={f('blood_group')}>
              <option value="">Unknown</option>
              {['A+','A-','B+','B-','AB+','AB-','O+','O-'].map(b => <option key={b}>{b}</option>)}
            </select>
          </div>
          <div><label className="label">Phone</label><input className="input" value={form.phone} onChange={f('phone')} /></div>
          <div><label className="label">Email (optional, for patient login)</label><input type="email" className="input" value={form.email} onChange={f('email')} /></div>
          <div className="col-span-2"><label className="label">Address</label><input className="input" value={form.address} onChange={f('address')} /></div>
        </div>

        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide pt-2">Emergency Contact</p>
        <div className="grid grid-cols-3 gap-3">
          <div><label className="label">Name</label><input className="input" value={form.emergency_contact_name} onChange={f('emergency_contact_name')} /></div>
          <div><label className="label">Phone</label><input className="input" value={form.emergency_contact_phone} onChange={f('emergency_contact_phone')} /></div>
          <div><label className="label">Relation</label><input className="input" value={form.emergency_contact_relation} onChange={f('emergency_contact_relation')} /></div>
        </div>

        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide pt-2">PDPA Consent *</p>
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
          <p className="text-xs text-amber-800 leading-relaxed">{form.consent_text}</p>
          <p className="text-xs text-amber-600 mt-2 font-medium">By registering this patient, you confirm they have given verbal or written consent.</p>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={loading}>{loading ? 'Registering...' : 'Register Patient'}</button>
        </div>
      </form>
    </Modal>
  )
}

// ── Audit Log tab ─────────────────────────────────────────────────────────────

function AuditLogTab() {
  const [logs, setLogs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.get('/admin/audit-log')
      .then((r) => setLogs(r.data))
      .catch(() => toast.error('Failed to load audit logs'))
      .finally(() => setLoading(false))
  }, [])

  const actionColor = (action) => {
    if (action.includes('delete') || action.includes('anonymize')) return 'badge-red'
    if (action.includes('add') || action.includes('create') || action.includes('register')) return 'badge-green'
    if (action.includes('login')) return 'badge-blue'
    return 'badge-gray'
  }

  return (
    <div>
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Audit Log</h2>
      {loading ? (
        <div className="flex justify-center py-16"><Spinner size="lg" /></div>
      ) : (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 border-b border-gray-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Time</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Actor</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Action</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Resource</th>
                <th className="text-left px-4 py-3 font-medium text-gray-600">Details</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {logs.map((log) => (
                <tr key={log.id} className="hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-500 whitespace-nowrap">
                    {new Date(log.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3">
                    <span className="font-medium">{log.actor_id}</span>
                    <span className="text-gray-400 ml-1">({log.actor_role})</span>
                  </td>
                  <td className="px-4 py-3">
                    <span className={actionColor(log.action)}>{log.action}</span>
                  </td>
                  <td className="px-4 py-3 text-gray-600">{log.resource_type} #{log.resource_id}</td>
                  <td className="px-4 py-3 text-gray-500 max-w-xs truncate">{log.details}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {logs.length === 0 && (
            <p className="text-center py-10 text-gray-500">No audit events recorded yet</p>
          )}
        </div>
      )}
    </div>
  )
}

// ── Overview ──────────────────────────────────────────────────────────────────

function OverviewPage() {
  const [stats, setStats] = useState(null)
  const [tab, setTab] = useState('doctors')

  const tabs = [
    { key: 'doctors', label: 'Doctors', icon: <Stethoscope size={16} /> },
    { key: 'patients', label: 'Patients', icon: <Users size={16} /> },
    { key: 'audit', label: 'Audit Log', icon: <ClipboardList size={16} /> },
  ]

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">Hospital Dashboard</h1>
        <p className="text-sm text-gray-500 mt-0.5">Manage your clinic's staff and patients</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-6 bg-gray-100 rounded-xl p-1 w-fit">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
              tab === t.key ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {tab === 'doctors' && <DoctorsTab />}
      {tab === 'patients' && <PatientsTab />}
      {tab === 'audit' && <AuditLogTab />}
    </div>
  )
}

const navItems = [
  { to: '/admin', label: 'Dashboard', icon: <Users size={18} /> },
]

export default function SuperAdminDashboard() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar items={navItems} title="MedAI Admin" subtitle="Hospital Administrator" />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route index element={<OverviewPage />} />
          <Route path="*" element={<Navigate to="/admin" replace />} />
        </Routes>
      </main>
    </div>
  )
}
