import { useState, useEffect, useRef } from 'react'
import { useAuth } from '../context/AuthContext'
import api from '../api/client'
import toast from 'react-hot-toast'
import { Send, Bot, User, Pill, FlaskConical, FileText, Activity, AlertTriangle } from 'lucide-react'
import Spinner from '../components/Spinner'

function ChatBubble({ msg }) {
  const isBot = msg.role === 'bot'
  return (
    <div className={`flex gap-3 ${isBot ? '' : 'flex-row-reverse'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isBot ? 'bg-primary-100 text-primary-600' : 'bg-gray-200 text-gray-600'}`}>
        {isBot ? <Bot size={16} /> : <User size={16} />}
      </div>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          isBot
            ? 'bg-white border border-gray-200 text-gray-800 rounded-tl-sm'
            : 'bg-primary-600 text-white rounded-tr-sm'
        }`}
      >
        {msg.text}
      </div>
    </div>
  )
}

function ChatTab({ patientId }) {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: 'Hello! I can help you view information from your medical records — such as your medications, lab results, and doctor diagnoses. What would you like to know?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function send() {
    const question = input.trim()
    if (!question || loading) return
    setInput('')
    setMessages((m) => [...m, { role: 'user', text: question }])
    setLoading(true)
    try {
      const res = await api.post('/chatbot/ask', { question })
      setMessages((m) => [...m, { role: 'bot', text: res.data.answer }])
    } catch {
      setMessages((m) => [...m, { role: 'bot', text: 'Sorry, I could not connect to the server. Please try again.' }])
    } finally {
      setLoading(false)
    }
  }

  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((msg, i) => <ChatBubble key={i} msg={msg} />)}
        {loading && (
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-primary-100 flex items-center justify-center flex-shrink-0">
              <Bot size={16} className="text-primary-600" />
            </div>
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2">
              <Spinner size="sm" />
              <span className="text-sm text-gray-500">Thinking...</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4 bg-white">
        <div className="flex gap-2">
          <textarea
            className="input flex-1 resize-none"
            rows={1}
            placeholder="Ask about your medications, lab results, or diagnoses..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKey}
          />
          <button
            className="btn-primary px-3 py-2 self-end"
            onClick={send}
            disabled={loading || !input.trim()}
          >
            <Send size={16} />
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1.5">
          For medical advice or emergencies, please contact your doctor directly.
        </p>
      </div>
    </div>
  )
}

function RecordsTab({ patientId }) {
  const [medications, setMedications] = useState([])
  const [labs, setLabs] = useState([])
  const [diagnoses, setDiagnoses] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      api.get(`/patients/${patientId}/medications`),
      api.get(`/patients/${patientId}/labs`),
      api.get(`/diagnosis/patient/${patientId}`),
    ])
      .then(([m, l, d]) => { setMedications(m.data); setLabs(l.data); setDiagnoses(d.data) })
      .catch(() => toast.error('Failed to load records'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="flex justify-center py-16"><Spinner size="lg" /></div>

  const currentMeds = medications.filter((m) => m.is_current)
  const confirmedDiagnoses = diagnoses.filter((d) => d.decision !== 'pending')

  return (
    <div className="p-4 space-y-4 overflow-y-auto">
      {/* Current Medications */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <Pill size={18} className="text-primary-600" />
          <h3 className="font-semibold text-gray-900">Current Medications</h3>
          <span className="badge-blue ml-auto">{currentMeds.length}</span>
        </div>
        {currentMeds.length === 0 ? (
          <p className="text-sm text-gray-500">No current medications</p>
        ) : (
          <div className="space-y-2">
            {currentMeds.map((m) => (
              <div key={m.id} className="flex items-center gap-3 p-2 bg-green-50 rounded-lg text-sm">
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{m.medicine_name}</p>
                  <p className="text-gray-500 text-xs">{m.dosage} · {m.frequency}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Recent Lab Results */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <FlaskConical size={18} className="text-primary-600" />
          <h3 className="font-semibold text-gray-900">Recent Lab Results</h3>
          <span className="badge-blue ml-auto">{labs.length}</span>
        </div>
        {labs.length === 0 ? (
          <p className="text-sm text-gray-500">No lab results on record</p>
        ) : (
          <div className="space-y-2">
            {labs.slice(0, 5).map((l) => (
              <div key={l.id} className={`flex items-center gap-3 p-2 rounded-lg text-sm ${l.is_abnormal ? 'bg-red-50' : 'bg-gray-50'}`}>
                <div className="flex-1">
                  <p className="font-medium text-gray-900">{l.test_name}</p>
                  <p className="text-gray-600">{l.result_value} {l.unit}</p>
                  <p className="text-xs text-gray-400">{l.test_date}</p>
                </div>
                {l.is_abnormal && <span className="badge-red flex items-center gap-1"><AlertTriangle size={10} /> Abnormal</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Confirmed Diagnoses */}
      <div className="card p-4">
        <div className="flex items-center gap-2 mb-3">
          <FileText size={18} className="text-primary-600" />
          <h3 className="font-semibold text-gray-900">Doctor's Diagnoses</h3>
          <span className="badge-blue ml-auto">{confirmedDiagnoses.length}</span>
        </div>
        {confirmedDiagnoses.length === 0 ? (
          <p className="text-sm text-gray-500">No confirmed diagnoses yet</p>
        ) : (
          <div className="space-y-2">
            {confirmedDiagnoses.map((d) => (
              <div key={d.id} className="p-3 bg-blue-50 rounded-lg text-sm">
                <p className="font-medium text-gray-900">{d.final_diagnosis}</p>
                <p className="text-xs text-gray-500 mt-0.5">
                  {d.decided_at ? new Date(d.decided_at).toLocaleDateString() : '—'}
                </p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function PatientDashboard() {
  const { user, logout } = useAuth()
  const [tab, setTab] = useState('chat')

  const patientId = user?.sub

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-primary-600 flex items-center justify-center text-white font-bold text-sm">M</div>
          <div>
            <p className="text-sm font-semibold text-gray-900">MedAI Patient Portal</p>
            <p className="text-xs text-gray-400">{user?.hospital_name}</p>
          </div>
        </div>
        <button onClick={logout} className="text-xs text-gray-500 hover:text-gray-700 font-medium">Sign out</button>
      </header>

      {/* Tabs */}
      <div className="flex border-b border-gray-200 bg-white px-4">
        {[
          { key: 'chat', label: 'Chat', icon: <Bot size={15} /> },
          { key: 'records', label: 'My Records', icon: <FileText size={15} /> },
        ].map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`flex items-center gap-1.5 px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? 'border-primary-600 text-primary-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.icon} {t.label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {tab === 'chat' && <ChatTab patientId={patientId} />}
        {tab === 'records' && <RecordsTab patientId={patientId} />}
      </div>
    </div>
  )
}
