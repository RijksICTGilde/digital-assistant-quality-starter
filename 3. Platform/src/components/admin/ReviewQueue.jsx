import { useState, useEffect } from 'react'
import { AlertTriangle, CheckCircle, XCircle, Edit3, Clock, RefreshCw, ChevronDown, ChevronUp, BookOpen } from 'lucide-react'
import { adminAPI } from '../../services/admin_api'

const FLAG_REASON_LABELS = {
  low_confidence: { label: 'Lage Betrouwbaarheid', color: 'bg-amber-100 text-amber-800', icon: AlertTriangle },
  hallucination: { label: 'Hallucinatie', color: 'bg-red-100 text-red-800', icon: AlertTriangle },
  user_flagged: { label: 'Gebruiker Gemarkeerd', color: 'bg-blue-100 text-blue-800', icon: AlertTriangle },
  expert_required: { label: 'Expert Nodig', color: 'bg-purple-100 text-purple-800', icon: AlertTriangle },
  policy_violation: { label: 'Beleidsschending', color: 'bg-red-100 text-red-800', icon: AlertTriangle }
}

const STATUS_LABELS = {
  pending: { label: 'In Behandeling', color: 'bg-amber-100 text-amber-800' },
  approved: { label: 'Goedgekeurd', color: 'bg-green-100 text-green-800' },
  rejected: { label: 'Afgewezen', color: 'bg-red-100 text-red-800' },
  corrected: { label: 'Gecorrigeerd', color: 'bg-blue-100 text-blue-800' }
}

export default function ReviewQueue({ onStatsUpdate, onGoldenAnswerImported }) {
  const [items, setItems] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [expandedItem, setExpandedItem] = useState(null)
  const [actionInProgress, setActionInProgress] = useState(null)
  const [correctionText, setCorrectionText] = useState('')
  const [reviewNotes, setReviewNotes] = useState('')
  const [showAll, setShowAll] = useState(false)

  const loadData = async () => {
    setLoading(true)
    try {
      const [itemsRes, statsRes] = await Promise.all([
        showAll ? adminAPI.getAllReviews() : adminAPI.getPendingReviews(),
        adminAPI.getReviewStats()
      ])
      setItems(itemsRes.data)
      setStats(statsRes.data)
      onStatsUpdate?.(statsRes.data)
    } catch (err) {
      console.error('Failed to load review data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [showAll])

  const handleApprove = async (id) => {
    setActionInProgress(id)
    try {
      await adminAPI.approveReview(id, { notes: reviewNotes || null })
      setReviewNotes('')
      setExpandedItem(null)
      await loadData()
    } catch (err) {
      console.error('Failed to approve:', err)
    } finally {
      setActionInProgress(null)
    }
  }

  const handleReject = async (id) => {
    setActionInProgress(id)
    try {
      await adminAPI.rejectReview(id, { notes: reviewNotes || null })
      setReviewNotes('')
      setExpandedItem(null)
      await loadData()
    } catch (err) {
      console.error('Failed to reject:', err)
    } finally {
      setActionInProgress(null)
    }
  }

  const handleCorrect = async (id) => {
    if (!correctionText.trim()) {
      alert('Voer een gecorrigeerde tekst in')
      return
    }
    setActionInProgress(id)
    try {
      await adminAPI.correctReview(id, {
        corrected_response: correctionText,
        notes: reviewNotes || null
      })
      setCorrectionText('')
      setReviewNotes('')
      setExpandedItem(null)
      await loadData()
    } catch (err) {
      console.error('Failed to correct:', err)
    } finally {
      setActionInProgress(null)
    }
  }

  const handleImportAsGolden = async (id) => {
    setActionInProgress(id)
    try {
      const res = await adminAPI.importFromReview(id)
      if (res.data.success) {
        alert('Succesvol geïmporteerd als Golden Answer!')
        await loadData()
        // Refresh the golden answer panel
        onGoldenAnswerImported?.()
      } else {
        alert(`Import mislukt: ${res.data.error}`)
      }
    } catch (err) {
      console.error('Failed to import as golden answer:', err)
      alert('Import mislukt')
    } finally {
      setActionInProgress(null)
    }
  }

  const formatDate = (timestamp) => {
    if (!timestamp) return ''
    return new Date(timestamp).toLocaleString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading && items.length === 0) {
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
          <AlertTriangle className="w-5 h-5 text-amber-600" />
          <h3 className="text-lg font-medium text-gray-900">Review Queue</h3>
          {stats && (
            <span className="px-2 py-0.5 bg-amber-100 text-amber-800 text-xs rounded-full font-medium">
              {stats.pending_count} in behandeling
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <label className="flex items-center space-x-1 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showAll}
              onChange={(e) => setShowAll(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span>Toon alle</span>
          </label>
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
          <div className="p-2 bg-amber-50 rounded text-center">
            <p className="text-amber-700 font-semibold">{stats.pending_count}</p>
            <p className="text-amber-600 text-xs">In behandeling</p>
          </div>
          <div className="p-2 bg-green-50 rounded text-center">
            <p className="text-green-700 font-semibold">{stats.approved_count}</p>
            <p className="text-green-600 text-xs">Goedgekeurd</p>
          </div>
          <div className="p-2 bg-red-50 rounded text-center">
            <p className="text-red-700 font-semibold">{stats.rejected_count}</p>
            <p className="text-red-600 text-xs">Afgewezen</p>
          </div>
          <div className="p-2 bg-blue-50 rounded text-center">
            <p className="text-blue-700 font-semibold">{stats.corrected_count}</p>
            <p className="text-blue-600 text-xs">Gecorrigeerd</p>
          </div>
        </div>
      )}

      {/* Items List */}
      {items.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-400" />
          <p>Geen items in de wachtrij</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto">
          {items.map((item) => {
            const flagInfo = FLAG_REASON_LABELS[item.flag_reason] || FLAG_REASON_LABELS.low_confidence
            const statusInfo = STATUS_LABELS[item.status] || STATUS_LABELS.pending
            const isExpanded = expandedItem === item.id
            const FlagIcon = flagInfo.icon

            return (
              <div key={item.id} className="border border-gray-200 rounded-lg overflow-hidden">
                {/* Header */}
                <div
                  className="p-3 bg-gray-50 cursor-pointer hover:bg-gray-100 transition-colors"
                  onClick={() => setExpandedItem(isExpanded ? null : item.id)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-1">
                        <span className={`px-2 py-0.5 text-xs rounded-full ${flagInfo.color}`}>
                          {flagInfo.label}
                        </span>
                        <span className={`px-2 py-0.5 text-xs rounded-full ${statusInfo.color}`}>
                          {statusInfo.label}
                        </span>
                        {item.hallucination_detected && (
                          <span className="px-2 py-0.5 text-xs rounded-full bg-red-100 text-red-800">
                            Hallucinatie
                          </span>
                        )}
                      </div>
                      <p className="text-sm text-gray-900 truncate">
                        <strong>Vraag:</strong> {item.original_question}
                      </p>
                      <div className="flex items-center space-x-3 mt-1 text-xs text-gray-500">
                        <span className="flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {formatDate(item.timestamp)}
                        </span>
                        {item.agent_type && (
                          <span className="capitalize">{item.agent_type} agent</span>
                        )}
                      </div>
                    </div>
                    <div className="ml-2">
                      {isExpanded ? (
                        <ChevronUp className="w-5 h-5 text-gray-400" />
                      ) : (
                        <ChevronDown className="w-5 h-5 text-gray-400" />
                      )}
                    </div>
                  </div>
                </div>

                {/* Expanded Content */}
                {isExpanded && (
                  <div className="p-4 border-t border-gray-200 space-y-4">
                    {/* Original Question */}
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">Oorspronkelijke Vraag</p>
                      <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded">{item.original_question}</p>
                    </div>

                    {/* AI Response */}
                    <div>
                      <p className="text-xs font-medium text-gray-500 mb-1">AI Antwoord</p>
                      <p className="text-sm text-gray-900 bg-gray-50 p-2 rounded max-h-40 overflow-y-auto whitespace-pre-wrap">
                        {item.ai_response}
                      </p>
                    </div>

                    {/* Ungrounded Claims */}
                    {item.ungrounded_claims && item.ungrounded_claims.length > 0 && (
                      <div className="p-3 bg-red-50 border border-red-200 rounded">
                        <p className="text-xs font-medium text-red-700 mb-1">Ongecontroleerde Claims</p>
                        <ul className="text-sm text-red-800 list-disc list-inside">
                          {item.ungrounded_claims.map((claim, i) => (
                            <li key={i}>{claim}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Quality Scores */}
                    {item.quality_scores && (
                      <div className="grid grid-cols-4 gap-2">
                        {Object.entries(item.quality_scores).map(([dim, score]) => (
                          <div key={dim} className="text-center p-2 bg-gray-50 rounded">
                            <p className="text-xs text-gray-500 capitalize">{dim.replace('_', ' ')}</p>
                            <p className={`font-semibold ${score >= 0.7 ? 'text-green-600' : score >= 0.5 ? 'text-amber-600' : 'text-red-600'}`}>
                              {Math.round(score * 100)}%
                            </p>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Previous Review Info */}
                    {item.status !== 'pending' && (
                      <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                        <p className="text-xs font-medium text-blue-700">
                          {statusInfo.label} op {formatDate(item.reviewed_at)}
                          {item.reviewed_by && ` door ${item.reviewed_by}`}
                        </p>
                        {item.reviewer_notes && (
                          <p className="text-sm text-blue-800 mt-1">{item.reviewer_notes}</p>
                        )}
                        {item.corrected_response && (
                          <div className="mt-2">
                            <p className="text-xs font-medium text-blue-700">Gecorrigeerd Antwoord:</p>
                            <p className="text-sm text-blue-900 mt-1 whitespace-pre-wrap">{item.corrected_response}</p>
                          </div>
                        )}
                      </div>
                    )}

                    {/* Import as Golden Answer - for approved/corrected items */}
                    {(item.status === 'approved' || item.status === 'corrected') && (
                      <div className="pt-2 border-t border-gray-200">
                        <button
                          onClick={() => handleImportAsGolden(item.id)}
                          disabled={actionInProgress === item.id}
                          className="flex items-center justify-center space-x-2 w-full px-3 py-2 bg-indigo-600 text-white text-sm rounded hover:bg-indigo-700 disabled:opacity-50"
                        >
                          <BookOpen className="w-4 h-4" />
                          <span>Importeer als Golden Answer</span>
                        </button>
                        <p className="text-xs text-gray-500 mt-1 text-center">
                          Voeg dit vraag-antwoord paar toe aan de golden answers database
                        </p>
                      </div>
                    )}

                    {/* Actions for Pending Items */}
                    {item.status === 'pending' && (
                      <div className="space-y-3 pt-2 border-t border-gray-200">
                        {/* Notes Input */}
                        <div>
                          <label className="text-xs font-medium text-gray-500">Opmerkingen (optioneel)</label>
                          <input
                            type="text"
                            value={reviewNotes}
                            onChange={(e) => setReviewNotes(e.target.value)}
                            placeholder="Voeg opmerkingen toe..."
                            className="w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </div>

                        {/* Correction Input */}
                        <div>
                          <label className="text-xs font-medium text-gray-500">Gecorrigeerd Antwoord (voor correctie)</label>
                          <textarea
                            value={correctionText}
                            onChange={(e) => setCorrectionText(e.target.value)}
                            placeholder="Voer het gecorrigeerde antwoord in..."
                            rows={3}
                            className="w-full mt-1 px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-1 focus:ring-blue-500"
                          />
                        </div>

                        {/* Action Buttons */}
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleApprove(item.id)}
                            disabled={actionInProgress === item.id}
                            className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-green-600 text-white text-sm rounded hover:bg-green-700 disabled:opacity-50"
                          >
                            <CheckCircle className="w-4 h-4" />
                            <span>Goedkeuren</span>
                          </button>
                          <button
                            onClick={() => handleReject(item.id)}
                            disabled={actionInProgress === item.id}
                            className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 disabled:opacity-50"
                          >
                            <XCircle className="w-4 h-4" />
                            <span>Afwijzen</span>
                          </button>
                          <button
                            onClick={() => handleCorrect(item.id)}
                            disabled={actionInProgress === item.id || !correctionText.trim()}
                            className="flex-1 flex items-center justify-center space-x-1 px-3 py-2 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 disabled:opacity-50"
                          >
                            <Edit3 className="w-4 h-4" />
                            <span>Corrigeren</span>
                          </button>
                        </div>
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
}
