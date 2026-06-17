import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { sendMessage, endSession } from '../services/api'
import useAuthStore from '../store/authStore'

// Single message bubble
function Message({ role, content }) {
  const isUser = role === 'user'
  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-sm mr-3 mt-1 shrink-0">
          🧠
        </div>
      )}
      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isUser
            ? 'bg-indigo-600 text-white rounded-br-sm'
            : 'bg-gray-800 text-gray-100 rounded-bl-sm'
        }`}
      >
        {content}
      </div>
    </div>
  )
}

// Reminder banner shown when system detects prerequisite gaps
function ReminderBanner({ reminders }) {
  if (!reminders || reminders.length === 0) return null
  return (
    <div className="mx-4 mb-3 bg-amber-900/40 border border-amber-700/50 rounded-lg px-4 py-3">
      <p className="text-amber-300 text-xs font-medium mb-1">📚 Quick reminder</p>
      {reminders.map((r, i) => (
        <p key={i} className="text-amber-200 text-xs">{r}</p>
      ))}
    </div>
  )
}

export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [reminders, setReminders] = useState([])
  const [resolved, setResolved] = useState(false)
  const bottomRef = useRef(null)
  const navigate = useNavigate()
  const { user, logout } = useAuthStore()

  // Scroll to bottom on new message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Add welcome message on first load
  useEffect(() => {
    setMessages([{
      role: 'assistant',
      content: "Hi! I'm your Socratic debugging tutor. Describe the bug you're facing and I'll guide you through solving it with questions — not answers. What are you working on?"
    }])
  }, [])

  const handleSend = async () => {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setLoading(true)
    setReminders([])

    try {
      const res = await sendMessage({
        content: userMessage,
        session_id: sessionId,
      })

      setSessionId(res.data.session_id)
      setReminders(res.data.reminders || [])
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.reply }])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: 'Sorry, something went wrong. Please try again.' },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleEndSession = async (wasResolved) => {
    if (!sessionId) return
    try {
      await endSession(sessionId, wasResolved)
      setResolved(true)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: wasResolved
            ? '✅ Great work! Session saved. Your progress has been updated. Start a new conversation anytime.'
            : '📝 Session ended. Keep practising — debugging is a skill that improves with repetition!',
        },
      ])
      setSessionId(null)
    } catch (err) {
      console.error(err)
    }
  }

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="flex flex-col h-screen bg-gray-950">

      {/* Top nav */}
      <div className="bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-xl">🧠</span>
          <div>
            <p className="text-white font-medium text-sm">Socratic Debug Tutor</p>
            <p className="text-gray-500 text-xs">
              {sessionId ? '🟢 Session active' : '⚪ No active session'}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-400 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Dashboard
          </button>
          <button
            onClick={handleLogout}
            className="text-gray-400 hover:text-white text-sm px-3 py-1.5 rounded-lg hover:bg-gray-800 transition-colors"
          >
            Logout
          </button>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 pt-4">
        {messages.map((msg, i) => (
          <Message key={i} role={msg.role} content={msg.content} />
        ))}

        {/* Loading indicator */}
        {loading && (
          <div className="flex justify-start mb-4">
            <div className="w-8 h-8 rounded-full bg-indigo-600 flex items-center justify-center text-white text-sm mr-3 mt-1 shrink-0">
              🧠
            </div>
            <div className="bg-gray-800 px-4 py-3 rounded-2xl rounded-bl-sm">
              <div className="flex gap-1 items-center h-4">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Reminders */}
      <ReminderBanner reminders={reminders} />

      {/* End session buttons — show only when session is active */}
      {sessionId && !resolved && (
        <div className="px-4 pb-2 flex gap-2">
          <button
            onClick={() => handleEndSession(true)}
            className="flex-1 bg-green-800/50 hover:bg-green-700/50 border border-green-700/50 text-green-300 text-xs py-2 rounded-lg transition-colors"
          >
            ✅ I solved it
          </button>
          <button
            onClick={() => handleEndSession(false)}
            className="flex-1 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-700/50 text-gray-400 text-xs py-2 rounded-lg transition-colors"
          >
            💾 Save & end session
          </button>
        </div>
      )}

      {/* Input area */}
      <div className="px-4 pb-4 pt-2 bg-gray-950 shrink-0">
        <div className="flex gap-2 items-end bg-gray-900 border border-gray-700 rounded-2xl px-4 py-3 focus-within:border-indigo-500 transition-colors">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault()
                handleSend()
              }
            }}
            placeholder="Describe your bug or paste your error message..."
            rows={1}
            className="flex-1 bg-transparent text-white placeholder-gray-500 text-sm resize-none focus:outline-none max-h-32"
            style={{ fieldSizing: 'content' }}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="bg-indigo-600 hover:bg-indigo-700 disabled:opacity-40 text-white p-2 rounded-xl transition-colors shrink-0"
          >
            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-4 h-4">
              <path d="M3.478 2.405a.75.75 0 00-.926.94l2.432 7.905H13.5a.75.75 0 010 1.5H4.984l-2.432 7.905a.75.75 0 00.926.94 60.519 60.519 0 0018.445-8.986.75.75 0 000-1.218A60.517 60.517 0 003.478 2.405z" />
            </svg>
          </button>
        </div>
        <p className="text-gray-600 text-xs text-center mt-2">
          Press Enter to send · Shift+Enter for new line
        </p>
      </div>
    </div>
  )
}
