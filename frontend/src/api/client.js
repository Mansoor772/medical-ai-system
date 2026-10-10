import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      window.location.href = '/login'
      return Promise.reject(err)
    }
    // Normalize FastAPI 422 validation errors (array of {loc, msg, type}) to a string
    const detail = err.response?.data?.detail
    if (Array.isArray(detail)) {
      err.response.data.detail = detail.map((d) => d.msg || JSON.stringify(d)).join('; ')
    }
    return Promise.reject(err)
  },
)

export function apiError(err, fallback = 'An error occurred') {
  return err?.response?.data?.detail || fallback
}

export default api
