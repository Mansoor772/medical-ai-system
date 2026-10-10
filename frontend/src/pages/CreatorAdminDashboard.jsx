import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import Modal from '../components/Modal'
import ConfirmDialog from '../components/ConfirmDialog'
import Spinner from '../components/Spinner'
import api from '../api/client'
import toast from 'react-hot-toast'
import { Building2, Plus, CheckCircle, XCircle, Download, LayoutDashboard, Search } from 'lucide-react'

function HospitalList() {
  const [hospitals, setHospitals] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [confirm, setConfirm] = useState(null)

  async function load() {
    try {
      const res = await api.get('/hospitals/')
      setHospitals(res.data)
    } catch {
      toast.error('Failed to load hospitals')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function toggleStatus(h) {
    try {
      const endpoint = h.is_active ? `/hospitals/${h.id}/deactivate` : `/hospitals/${h.id}/reactivate`
      await api.post(endpoint)
      toast.success(`Hospital ${h.is_active ? 'deactivated' : 'reactivated'}`)
      load()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Action failed')
    }
    setConfirm(null)
  }

  async function exportData(h) {
    try {
      const res = await api.get(`/compliance/hospitals/${h.id}/export`, { responseType: 'blob' })
      const url = URL.createObjectURL(res.data)
      const a = document.createElement('a')
      a.href = url
      a.download = `${h.name.replace(/\s+/g, '_')}_export.json`
      a.click()
      toast.success('Export downloaded')
    } catch {
      toast.error('Export failed')
    }
  }

  const filtered = hospitals.filter(
    (h) =>
      h.name.toLowerCase().includes(search.toLowerCase()) ||
      h.city?.toLowerCase().includes(search.toLowerCase()),
  )

  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Hospitals</h1>
          <p className="text-sm text-gray-500 mt-0.5">Manage all registered clinics and hospitals</p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreate(true)}>
          <Plus size={16} /> New Hospital
        </button>
      </div>

      {/* Search */}
      <div className="relative mb-4">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
        <input
          className="input pl-9"
          placeholder="Search by name or city..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {loading ? (
        <div className="flex justify-center py-20"><Spinner size="lg" /></div>
      ) : filtered.length === 0 ? (
        <div className="card p-12 text-center text-gray-500">
          <Building2 size={40} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">No hospitals found</p>
          <p className="text-sm mt-1">Create the first hospital to get started</p>
        </div>
      ) : (
        <div className="space-y-3">
          {filtered.map((h) => (
            <div key={h.id} className="card p-4 flex items-center gap-4">
              <div className="w-10 h-10 rounded-lg bg-primary-50 flex items-center justify-center flex-shrink-0">
                <Building2 size={20} className="text-primary-600" />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-gray-900">{h.name}</p>
                  <span className={h.is_active ? 'badge-green' : 'badge-red'}>
                    {h.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="text-sm text-gray-500">{h.city} · {h.contact_email}</p>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                <button
                  className="btn-secondary text-xs"
                  onClick={() => exportData(h)}
                  title="Export hospital data (JSON)"
                >
                  <Download size={14} /> Export
                </button>
                <button
                  className={h.is_active ? 'btn-danger text-xs' : 'btn-secondary text-xs'}
                  onClick={() =>
                    setConfirm({
                      h,
                      action: h.is_active ? 'deactivate' : 'reactivate',
                    })
                  }
                >
                  {h.is_active ? <XCircle size={14} /> : <CheckCircle size={14} />}
                  {h.is_active ? 'Deactivate' : 'Reactivate'}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {showCreate && <CreateHospitalModal onClose={() => setShowCreate(false)} onCreated={load} />}

      {confirm && (
        <ConfirmDialog
          title={`${confirm.action === 'deactivate' ? 'Deactivate' : 'Reactivate'} Hospital`}
          message={`Are you sure you want to ${confirm.action} "${confirm.h.name}"? ${
            confirm.action === 'deactivate'
              ? 'Staff will not be able to log in while the hospital is inactive.'
              : ''
          }`}
          confirmLabel={confirm.action === 'deactivate' ? 'Deactivate' : 'Reactivate'}
          danger={confirm.action === 'deactivate'}
          onConfirm={() => toggleStatus(confirm.h)}
          onClose={() => setConfirm(null)}
        />
      )}
    </div>
  )
}

function CreateHospitalModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '', city: '', address: '', contact_email: '', contact_phone: '',
    admin_name: '', admin_email: '', admin_password: '', admin_phone: '',
  })
  const [loading, setLoading] = useState(false)

  const f = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function submit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/hospitals/', {
        name: form.name,
        city: form.city,
        address: form.address,
        contact_email: form.contact_email,
        contact_phone: form.contact_phone,
        super_admin: {
          name: form.admin_name,
          email: form.admin_email,
          password: form.admin_password,
          phone: form.admin_phone,
        },
      })
      toast.success(`Hospital "${form.name}" created`)
      onCreated()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create hospital')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Modal title="Register New Hospital" onClose={onClose} size="lg">
      <form onSubmit={submit} className="space-y-4">
        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Hospital Information</p>
        <div className="grid grid-cols-2 gap-3">
          <div className="col-span-2">
            <label className="label">Hospital Name *</label>
            <input className="input" value={form.name} onChange={f('name')} required />
          </div>
          <div>
            <label className="label">City *</label>
            <input className="input" value={form.city} onChange={f('city')} required />
          </div>
          <div>
            <label className="label">Contact Phone *</label>
            <input className="input" value={form.contact_phone} onChange={f('contact_phone')} required />
          </div>
          <div className="col-span-2">
            <label className="label">Address</label>
            <input className="input" value={form.address} onChange={f('address')} />
          </div>
          <div className="col-span-2">
            <label className="label">Contact Email *</label>
            <input type="email" className="input" value={form.contact_email} onChange={f('contact_email')} required />
          </div>
        </div>

        <p className="text-xs font-semibold text-gray-400 uppercase tracking-wide pt-2">Super Admin Account</p>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="label">Admin Name *</label>
            <input className="input" value={form.admin_name} onChange={f('admin_name')} required />
          </div>
          <div>
            <label className="label">Admin Phone</label>
            <input className="input" value={form.admin_phone} onChange={f('admin_phone')} />
          </div>
          <div className="col-span-2">
            <label className="label">Admin Email *</label>
            <input type="email" className="input" value={form.admin_email} onChange={f('admin_email')} required />
          </div>
          <div className="col-span-2">
            <label className="label">Admin Password *</label>
            <input type="password" className="input" value={form.admin_password} onChange={f('admin_password')} required minLength={8} />
          </div>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button type="button" className="btn-secondary" onClick={onClose}>Cancel</button>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Creating...' : 'Create Hospital'}
          </button>
        </div>
      </form>
    </Modal>
  )
}

const navItems = [
  { to: '/creator', label: 'Hospitals', icon: <Building2 size={18} /> },
]

export default function CreatorAdminDashboard() {
  return (
    <div className="flex h-screen bg-gray-50">
      <Sidebar items={navItems} title="MedAI Creator" subtitle="System Administrator" />
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route index element={<HospitalList />} />
          <Route path="*" element={<Navigate to="/creator" replace />} />
        </Routes>
      </main>
    </div>
  )
}
