import axios from 'axios'

const BASE_URL = 'http://localhost:8000/api/v1'

const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Automatically attach token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Auth
export const register = (data) => api.post('/auth/register', data)
export const login = (data) => api.post('/auth/login', data)

// Chat
export const sendMessage = (data) => api.post('/chat/message', data)
export const endSession = (sessionId, resolved) =>
  api.post(`/chat/session/${sessionId}/end?resolved=${resolved}`)

// Progress
export const getProgress = () => api.get('/progress/summary')

export default api
