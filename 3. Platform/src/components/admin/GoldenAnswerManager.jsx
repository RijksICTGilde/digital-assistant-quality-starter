import { useState, useEffect, useImperativeHandle, forwardRef } from 'react'
import {
  BookOpen, Plus, Trash2, Play, CheckCircle, XCircle,
  RefreshCw, ChevronDown, ChevronUp, FileText, Clock,
  TrendingUp, AlertTriangle
} from 'lucide-react'
import { adminAPI } from '../../services/admin_api'

const SOURCE_LABELS = {
  manual: { label: 'Handmatig', color: 'bg-blue-100 text-blue-800' },
  from_review: { label: 'Uit Review', color: 'bg-purple-100 text-purple-800' },
  from_feedback: { label: 'Uit Feedback', color: 'bg-green-100 text-green-800' }
}

const GoldenAnswerManager = forwardRef(function GoldenAnswerManager(props, ref) {
  const [answers, setAnswers] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [testRunning, setTestRunning] = useState(false)
  const [testResult, setTestResult] = useState(null)
  const [expandedAnswer, setExpandedAnswer] = useState(null)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newAnswer, setNewAnswer] = useState({
    question: '',
    answer: '',
    category: '',
    tags: ''
  })

  // Expose refresh function to parent
  useImperativeHandle(ref, () => ({
    refresh: loadData
  }))

  const loadData = async () => {
    setLoading(true)
    try {
      const [answersRes, statsRes] = await Promise.all([
        adminAPI.getGoldenAnswers(),
        adminAPI.getGoldenAnswerStats()
      ])
      setAnswers(answersRes.data)
      setStats(statsRes.data)
      if (statsRes.data.last_regression_test) {
        setTestResult(statsRes.data.last_regression_test)
      }
    } catch (err) {
      console.error('Failed to load golden answers:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleAddAnswer = async (e) => {
    e.preventDefault()
    try {
      const data = {
        question: newAnswer.question,
        answer: newAnswer.answer,
        category: newAnswer.category || null,
        tags: newAnswer.tags ? newAnswer.tags.split(',').map(t => t.trim()) : null
      }
      await adminAPI.addGoldenAnswer(data)
      setNewAnswer({ question: '', answer: '', category: '', tags: '' })
      setShowAddForm(false)
      await loadData()
    } catch (err) {
      console.error('Failed to add golden answer:', err)
      alert('Kon golden answer niet toevoegen')
    }
  }

  const handleDeactivate = async (id) => {
    if (!confirm('Weet je zeker dat je dit golden answer wilt deactiveren?')) return
    try {
      await adminAPI.deactivateGoldenAnswer(id)
      await loadData()
    } catch (err) {
      console.error('Failed to deactivate:', err)
    }
  }

  const handleRunTest = async () => {
    if (stats?.active_answers === 0) {
      alert('Geen actieve golden answers om te testen')
      return
    }
    setTestRunning(true)
    try {
      const result = await adminAPI.runRegressionTest()
      setTestResult(result.data)
      await loadData() // Refresh stats
    } catch (err) {
      console.error('Failed to run regression test:', err)
      alert('Regressietest mislukt')
    } finally {
      setTestRunning(false)
    }
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return ''
    return new Date(timestamp).toLocaleString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      year: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading && answers.length === 0) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center space-x-2 text-gray-500">
          <RefreshCw className="w-4 h-4 animate-spin" />
          <span>Laden...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <BookOpen className="w-5 h-5 text-indigo-600" />
          <h3 className="text-lg font-medium text-gray-900">Golden Answers</h3>
          {stats && (
            <span className="px-2 py-0.5 bg-indigo-100 text-indigo-800 text-xs rounded-full font-medium">
              {stats.active_answers} actief
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowAddForm(!showAddForm)}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
          >
            <Plus className="w-4 h-4" />
            <span>Nieuw</span>
          </button>
          <button
            onClick={handleRunTest}
            disabled={testRunning || stats?.active_answers === 0}
            className="flex items-center space-x-1 px-3 py-1.5 text-sm bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50"
          >
            {testRunning ? (
              <RefreshCw className="w-4 h-4 animate-spin" />
            ) : (
              <Play className="w-4 h-4" />
            )}
            <span>{testRunning ? 'Bezig...' : 'Test'}</span>
          </button>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Stats Summary */}
      {stats && (
        <div className="grid grid-cols-4 gap-2 mb-4 text-sm">
          <div className="p-2 bg-indigo-50 rounded text-center">
            <p className="text-indigo-700 font-semibold">{stats.total_answers}</p>
            <p className="text-indigo-600 text-xs">Totaal</p>
          </div>
          <div className="p-2 bg-green-50 rounded text-center">
            <p className="text-green-700 font-semibold">{stats.active_answers}</p>
            <p className="text-green-600 text-xs">Actief</p>
          </div>
          <div className="p-2 bg-purple-50 rounded text-center">
            <p className="text-purple-700 font-semibold">{stats.by_source?.from_review || 0}</p>
            <p className="text-purple-600 text-xs">Uit Reviews</p>
          </div>
          <div className="p-2 bg-blue-50 rounded text-center">
            <p className="text-blue-700 font-semibold">{stats.by_source?.manual || 0}</p>
            <p className="text-blue-600 text-xs">Handmatig</p>
          </div>
        </div>
      )}

      {/* Regression Test Result */}
      {testResult && (
        <div className={`p-4 rounded-lg mb-4 ${testResult.pass_rate >= 0.8 ? 'bg-green-50 border border-green-200' : testResult.pass_rate >= 0.5 ? 'bg-amber-50 border border-amber-200' : 'bg-red-50 border border-red-200'}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center space-x-2">
              <TrendingUp className={`w-5 h-5 ${testResult.pass_rate >= 0.8 ? 'text-green-600' : testResult.pass_rate >= 0.5 ? 'text-amber-600' : 'text-red-600'}`} />
              <span className="font-medium text-gray-900">Laatste Regressietest</span>
            </div>
            <span className="text-xs text-gray-500">{formatDate(testResult.timestamp)}</span>
          </div>
          <div className="grid grid-cols-4 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Totaal</p>
              <p className="font-semibold">{testResult.total_tests}</p>
            </div>
            <div>
              <p className="text-gray-500">Geslaagd</p>
              <p className="font-semibold text-green-600">{testResult.passed}</p>
            </div>
            <div>
              <p className="text-gray-500">Gefaald</p>
              <p className="font-semibold text-red-600">{testResult.failed}</p>
            </div>
            <div>
              <p className="text-gray-500">Score</p>
              <p className={`font-semibold ${testResult.pass_rate >= 0.8 ? 'text-green-600' : testResult.pass_rate >= 0.5 ? 'text-amber-600' : 'text-red-600'}`}>
                {Math.round(testResult.pass_rate * 100)}%
              </p>
            </div>
          </div>
          {testResult.results && testResult.results.length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200">
              <p className="text-xs font-medium text-gray-500 mb-2">Details per test:</p>
              <div className="space-y-1 max-h-40 overflow-y-auto">
                {testResult.results.map((r, i) => (
                  <div key={i} className="flex items-center justify-between text-xs py-1 px-2 bg-white rounded">
                    <span className="truncate flex-1 mr-2" title={r.question}>{r.question}</span>
                    <div className="flex items-center space-x-2">
                      <span className="text-gray-500">{Math.round(r.similarity_score * 100)}%</span>
                      {r.passed ? (
                        <CheckCircle className="w-4 h-4 text-green-500" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-500" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Add Form */}
      {showAddForm && (
        <form onSubmit={handleAddAnswer} className="p-4 bg-gray-50 rounded-lg mb-4 space-y-3">
          <div>
            <label className="text-xs font-medium text-gray-500">Vraag</label>
            <input
              type="text"
              value={newAnswer.question}
              onChange={(e) => setNewAnswer({ ...newAnswer, question: e.target.value })}
              placeholder="De vraag die de gebruiker zou stellen..."
              required
              className="w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-gray-500">Ideaal Antwoord</label>
            <textarea
              value={newAnswer.answer}
              onChange={(e) => setNewAnswer({ ...newAnswer, answer: e.target.value })}
              placeholder="Het perfecte antwoord op deze vraag..."
              required
              rows={4}
              className="w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs font-medium text-gray-500">Categorie (optioneel)</label>
              <select
                value={newAnswer.category}
                onChange={(e) => setNewAnswer({ ...newAnswer, category: e.target.value })}
                className="w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value="">Selecteer...</option>
                <option value="GDPR">GDPR/AVG</option>
                <option value="AI_ACT">AI Act</option>
                <option value="WOO">Wet Open Overheid</option>
                <option value="TECHNICAL">Technisch</option>
                <option value="GENERAL">Algemeen</option>
              </select>
            </div>
            <div>
              <label className="text-xs font-medium text-gray-500">Tags (komma-gescheiden)</label>
              <input
                type="text"
                value={newAnswer.tags}
                onChange={(e) => setNewAnswer({ ...newAnswer, tags: e.target.value })}
                placeholder="privacy, gemeente, ..."
                className="w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-indigo-500"
              />
            </div>
          </div>
          <div className="flex justify-end space-x-2">
            <button
              type="button"
              onClick={() => setShowAddForm(false)}
              className="px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-200 rounded"
            >
              Annuleren
            </button>
            <button
              type="submit"
              className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              Toevoegen
            </button>
          </div>
        </form>
      )}

      {/* Answers List */}
      {answers.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <BookOpen className="w-12 h-12 mx-auto mb-2 text-gray-300" />
          <p>Geen golden answers</p>
          <p className="text-xs mt-1">Voeg handmatig toe of importeer uit goedgekeurde reviews</p>
        </div>
      ) : (
        <div className="space-y-2 max-h-[400px] overflow-y-auto">
          {answers.map((answer) => {
            const sourceInfo = SOURCE_LABELS[answer.source] || SOURCE_LABELS.manual
            const isExpanded = expandedAnswer === answer.id

            return (
              <div key={answer.id} className={`border rounded-lg overflow-hidden ${answer.is_active ? 'border-gray-200' : 'border-gray-100 opacity-60'}`}>
                <div
                  className="p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => setExpandedAnswer(isExpanded ? null : answer.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${sourceInfo.color}`}>
                          {sourceInfo.label}
                        </span>
                        {answer.category && (
                          <span className="px-2 py-0.5 text-xs rounded-full bg-gray-100 text-gray-700">
                            {answer.category}
                          </span>
                        )}
                        {!answer.is_active && (
                          <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-700">
                            Inactief
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900 truncate">
                        <strong>V:</strong> {answer.question}
                      </p>
                      <p className="text-xs text-gray-500 mt-1">
                        <Clock className="w-3 h-3 inline mr-1" />
                        {formatDate(answer.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center space-x-2 ml-2">
                      {answer.is_active && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDeactivate(answer.id)
                          }}
                          className="p-1 hover:bg-red-100 rounded text-red-500"
                          title="Deactiveren"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 border-t border-gray-200 space-y-3">
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Vraag</p>
                      <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{answer.question}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Ideaal Antwoord</p>
                      <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded whitespace-pre-wrap max-h-40 overflow-y-auto">
                        {answer.answer}
                      </p>
                    </div>
                    {answer.tags && answer.tags.length > 0 && (
                      <div className="flex flex-wrap gap-1">
                        {answer.tags.map((tag, i) => (
                          <span key={i} className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
                            {tag}
                          </span>
                        ))}
                      </div>
                    )}
                    {answer.quality_scores && (
                      <div className="grid grid-cols-4 gap-2">
                        {Object.entries(answer.quality_scores).map(([dim, score]) => (
                          <div key={dim} className="text-center p-2 bg-gray-50 rounded">
                            <p className="text-xs text-gray-500 capitalize">{dim.replace('_', ' ')}</p>
                            <p className={`font-semibold ${score >= 0.7 ? 'text-green-600' : score >= 0.5 ? 'text-amber-600' : 'text-red-600'}`}>
                              {Math.round(score * 100)}%
                            </p>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
})

export default GoldenAnswerManager
