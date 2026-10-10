import { Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './context/AuthContext'
import LoginPage from './pages/LoginPage'
import CreatorAdminDashboard from './pages/CreatorAdminDashboard'
import SuperAdminDashboard from './pages/SuperAdminDashboard'
import DoctorDashboard from './pages/DoctorDashboard'
import PatientDashboard from './pages/PatientDashboard'

function RequireAuth({ children, allowedRoles }) {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  if (allowedRoles && !allowedRoles.includes(user.role)) return <Navigate to="/login" replace />
  return children
}

function RoleRouter() {
  const { user } = useAuth()
  if (!user) return <Navigate to="/login" replace />
  const routes = {
    creator_admin: '/creator',
    super_admin: '/admin',
    doctor: '/doctor',
    patient: '/patient',
  }
  return <Navigate to={routes[user.role] || '/login'} replace />
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<RoleRouter />} />
        <Route
          path="/creator/*"
          element={
            <RequireAuth allowedRoles={['creator_admin']}>
              <CreatorAdminDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/admin/*"
          element={
            <RequireAuth allowedRoles={['super_admin']}>
              <SuperAdminDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/doctor/*"
          element={
            <RequireAuth allowedRoles={['doctor']}>
              <DoctorDashboard />
            </RequireAuth>
          }
        />
        <Route
          path="/patient/*"
          element={
            <RequireAuth allowedRoles={['patient']}>
              <PatientDashboard />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthProvider>
  )
}
