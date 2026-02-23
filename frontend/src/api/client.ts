import axios from 'axios'

export const api = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Attach JWT token from localStorage
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Redirect to login on 401; surface FastAPI detail as error message
api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token')
      // Avoid reload loop: only redirect if we are NOT already on the login page.
      if (!window.location.pathname.startsWith('/login')) {
        window.location.href = '/login'
      }
    }
    // Extract backend detail so React Query's onError receives a readable message
    const detail = err.response?.data?.detail
    if (detail) {
      if (typeof detail === 'string') {
        err.message = detail
      } else if (Array.isArray(detail)) {
        // FastAPI validation errors: [{loc, msg, type}, ...]
        err.message = detail.map((d: { msg?: string }) => d.msg ?? JSON.stringify(d)).join('; ')
      } else {
        err.message = JSON.stringify(detail)
      }
    }
    return Promise.reject(err)
  },
)
