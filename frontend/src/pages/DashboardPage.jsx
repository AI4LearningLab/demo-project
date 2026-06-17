import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { getProgress } from '../services/api'

// Mastery score bar
function MasteryBar({ score }) {
  const pct = Math.round(score * 100)
  const color =
    pct >= 80 ? 'bg-green-500' :
    pct >= 50 ? 'bg-yellow-500' :
    'bg-red-500'
  return (
    <div className="flex items-center gap-3">
      <div className="flex-1 bg-gray-700 rounded-full h-2">
        <div className={`${color} h-2 rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-gray-400 w-8 text-right">{pct}%</span>
    </div>
  )
}

// Stat card
function StatCard({ label, value, icon, color }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-gray-400 text-sm">{label}</span>
        <span className="text-2xl">{icon}</span>
      </div>
      <p className={`text-3xl font-bold ${color}`}>{value}</p>
    </div>
  )
}

export default function DashboardPage() {
  const [progress, setProgress] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  useEffect(() => {
    getProgress()
      .then((res) => setProgress(res.data))
      .catch(() => setError('Failed to load progress'))
      .finally(() => setLoading(false))
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-gray-400">Loading your progress...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <p className="text-red-400">{error}</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">

      {/* Nav */}
      <div className="bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xl">🧠</span>
          <h1 className="font-bold text-white">Progress Dashboard</h1>
        </div>
        <button
          onClick={() => navigate('/chat')}
          className="bg-indigo-600 hover:bg-indigo-700 text-white text-sm px-4 py-2 rounded-lg transition-colors"
        >
          Back to Chat
        </button>
      </div>

      <div className="max-w-4xl mx-auto px-6 py-8 space-y-8">

        {/* Stats row */}
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <StatCard
            label="Total Sessions"
            value={progress.total_sessions}
            icon="💬"
            color="text-indigo-400"
          />
          <StatCard
            label="Avg Hints / Session"
            value={progress.avg_hints_per_session.toFixed(1)}
            icon="💡"
            color="text-yellow-400"
          />
          <StatCard
            label="Concepts Tracked"
            value={progress.knowledge_states.length}
            icon="📚"
            color="text-green-400"
          />
        </div>

        {/* Knowledge mastery */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-1">Knowledge Mastery</h2>
          <p className="text-gray-500 text-sm mb-5">Your mastery score per concept and sub-skill</p>

          {progress.knowledge_states.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-4xl mb-3">🌱</p>
              <p className="text-gray-400 text-sm">No concepts tracked yet.</p>
              <p className="text-gray-500 text-xs mt-1">Start a debugging session to build your profile.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {progress.knowledge_states.map((ks, i) => (
                <div key={i}>
                  <div className="flex justify-between items-center mb-1">
                    <span className="text-sm text-gray-300">
                      {ks.concept}
                      <span className="text-gray-500 ml-2 text-xs">· {ks.sub_skill}</span>
                    </span>
                    <span className="text-xs text-gray-500">{ks.times_encountered}x</span>
                  </div>
                  <MasteryBar score={ks.mastery_score} />
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Struggle map */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
          <h2 className="font-semibold text-white mb-1">Recurring Struggles</h2>
          <p className="text-gray-500 text-sm mb-5">Bug types you have faced more than once</p>

          {progress.top_struggles.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-4xl mb-3">🎯</p>
              <p className="text-gray-400 text-sm">No recurring struggles yet.</p>
              <p className="text-gray-500 text-xs mt-1">Keep debugging — patterns will appear here.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {progress.top_struggles.map((s, i) => (
                <div key={i} className="flex items-center justify-between bg-gray-800 rounded-lg px-4 py-3">
                  <div>
                    <p className="text-sm text-white font-medium">{s.bug_type.replace(/_/g, ' ')}</p>
                    <p className="text-xs text-gray-500">{s.sub_skill}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-red-400 font-bold text-lg">{s.occurrence_count}x</p>
                    <p className={`text-xs ${s.resolved_eventually ? 'text-green-400' : 'text-gray-500'}`}>
                      {s.resolved_eventually ? 'resolved ✓' : 'unresolved'}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Due reviews */}
        {progress.upcoming_reviews.length > 0 && (
          <div className="bg-amber-900/20 border border-amber-700/40 rounded-xl p-6">
            <h2 className="font-semibold text-amber-300 mb-1">📅 Due for Review Today</h2>
            <p className="text-amber-400/70 text-sm mb-4">
              These concepts are scheduled for spaced repetition review
            </p>
            <div className="flex flex-wrap gap-2">
              {progress.upcoming_reviews.map((r, i) => (
                <span key={i} className="bg-amber-800/40 border border-amber-700/40 text-amber-300 text-sm px-3 py-1 rounded-full">
                  {r.concept.replace(/_/g, ' ')}
                </span>
              ))}
            </div>
            <button
              onClick={() => navigate('/chat')}
              className="mt-4 bg-amber-600 hover:bg-amber-700 text-white text-sm px-4 py-2 rounded-lg transition-colors"
            >
              Start review session →
            </button>
          </div>
        )}

      </div>
    </div>
  )
}
