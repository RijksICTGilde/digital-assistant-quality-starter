import { useState } from 'react'
import { ThumbsUp, ThumbsDown, TrendingUp, MessageCircle, RefreshCw } from 'lucide-react'

export default function FeedbackStats({ stats, onRefresh }) {
  const [refreshing, setRefreshing] = useState(false)

  const handleRefresh = async () => {
    if (!onRefresh || refreshing) return
    setRefreshing(true)
    try {
      await onRefresh()
    } finally {
      setRefreshing(false)
    }
  }

  if (!stats) {
    return (
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-medium text-gray-900">Feedback Statistieken</h3>
          {onRefresh && (
            <button
              onClick={handleRefresh}
              disabled={refreshing}
              className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
              title="Vernieuwen"
            >
              <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
            </button>
          )}
        </div>
        <p className="text-gray-500">Geen feedback data beschikbaar</p>
      </div>
    )
  }

  const approvalRate = stats.approval_rate || 0
  const approvalColor = approvalRate >= 0.8 ? 'text-green-600' : approvalRate >= 0.6 ? 'text-amber-600' : 'text-red-600'
  const approvalBg = approvalRate >= 0.8 ? 'bg-green-100' : approvalRate >= 0.6 ? 'bg-amber-100' : 'bg-red-100'

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Feedback Statistieken</h3>
        {onRefresh && (
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
            title="Vernieuwen"
          >
            <RefreshCw className={`w-4 h-4 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
        )}
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="flex items-center space-x-3 p-3 bg-green-50 rounded-lg">
          <ThumbsUp className="w-5 h-5 text-green-600" />
          <div>
            <p className="text-2xl font-bold text-green-600">{stats.positive_count || 0}</p>
            <p className="text-xs text-green-700">Positief</p>
          </div>
        </div>

        <div className="flex items-center space-x-3 p-3 bg-red-50 rounded-lg">
          <ThumbsDown className="w-5 h-5 text-red-600" />
          <div>
            <p className="text-2xl font-bold text-red-600">{stats.negative_count || 0}</p>
            <p className="text-xs text-red-700">Negatief</p>
          </div>
        </div>
      </div>

      {/* Approval Rate */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-gray-600">Goedkeuringspercentage</span>
          <span className={`text-lg font-bold ${approvalColor}`}>
            {(approvalRate * 100).toFixed(0)}%
          </span>
        </div>
        <div className="h-3 bg-gray-200 rounded-full overflow-hidden">
          <div
            className={`h-full ${approvalBg} transition-all duration-500`}
            style={{ width: `${approvalRate * 100}%` }}
          />
        </div>
      </div>

      {/* Improvement Stats */}
      {stats.improved_responses_feedback && (
        <div className="border-t border-gray-100 pt-4 mb-4">
          <div className="flex items-center space-x-2 mb-2">
            <TrendingUp className="w-4 h-4 text-blue-600" />
            <span className="text-sm font-medium text-gray-700">Verbeterde Antwoorden</span>
          </div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div className="p-2 bg-gray-50 rounded">
              <p className="text-gray-500">Totaal verbeterd</p>
              <p className="font-semibold">{stats.improved_responses_feedback.total_improved || 0}</p>
            </div>
            <div className="p-2 bg-gray-50 rounded">
              <p className="text-gray-500">Positief na verbetering</p>
              <p className="font-semibold text-green-600">
                {stats.improved_responses_feedback.positive_after_improvement || 0}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Feedback with Comments */}
      <div className="flex items-center space-x-2 text-sm text-gray-600">
        <MessageCircle className="w-4 h-4" />
        <span>{stats.feedback_with_comments || 0} feedback met opmerkingen</span>
      </div>

      {/* By Agent Type */}
      {stats.by_agent_type && Object.keys(stats.by_agent_type).length > 0 && (
        <div className="border-t border-gray-100 pt-4 mt-4">
          <p className="text-sm font-medium text-gray-700 mb-2">Per Agent Type</p>
          <div className="space-y-2">
            {Object.entries(stats.by_agent_type).map(([agent, data]) => (
              <div key={agent} className="flex items-center justify-between text-sm">
                <span className="capitalize text-gray-600">{agent}</span>
                <div className="flex items-center space-x-2">
                  <span className="text-green-600">{data.positive}</span>
                  <span className="text-gray-400">/</span>
                  <span className="text-red-600">{data.negative}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
