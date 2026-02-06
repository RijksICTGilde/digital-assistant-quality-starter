import { useState, useEffect } from 'react'
import {
  TrendingUp, BarChart3, RefreshCw,
  ThumbsUp, ThumbsDown, AlertTriangle
} from 'lucide-react'
import { adminAPI } from '../../services/admin_api'

const DIMENSION_LABELS = {
  relevance: 'Relevantie',
  tone: 'Toon',
  completeness: 'Volledigheid',
  policy_compliance: 'Beleidsconformiteit'
}

export default function AnalyticsDashboard() {
  const [analytics, setAnalytics] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadData = async () => {
    setLoading(true)
    try {
      const analyticsRes = await adminAPI.getFeedbackAnalytics()
      setAnalytics(analyticsRes.data)
    } catch (err) {
      console.error('Failed to load analytics:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const formatDate = (timestamp) => {
    if (!timestamp) return ''
    return new Date(timestamp).toLocaleString('nl-NL', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  if (loading) {
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
    <div className="space-y-6">
      {/* Feedback Trends */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center space-x-3">
            <TrendingUp className="w-5 h-5 text-blue-600" />
            <h3 className="text-lg font-medium text-gray-900">Feedback Trends</h3>
          </div>
          <button
            onClick={loadData}
            disabled={loading}
            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className={`w-4 h-4 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>

        {analytics?.daily_trends && analytics.daily_trends.length > 0 ? (
          <div className="space-y-4">
            {/* Mini bar chart using CSS */}
            <div className="overflow-x-auto">
              <div className="flex items-end space-x-1 min-w-max h-32 px-2">
                {analytics.daily_trends.slice(-14).map((day, i) => {
                  const maxTotal = Math.max(...analytics.daily_trends.map(d => d.total), 1)
                  const height = (day.total / maxTotal) * 100
                  const positiveHeight = (day.positive / maxTotal) * 100
                  const negativeHeight = (day.negative / maxTotal) * 100

                  return (
                    <div key={i} className="flex flex-col items-center" style={{ width: '40px' }}>
                      <div className="flex flex-col-reverse h-24 w-6 relative">
                        {day.total > 0 && (
                          <>
                            <div
                              className="bg-green-500 w-full rounded-t"
                              style={{ height: `${positiveHeight}%` }}
                              title={`${day.positive} positief`}
                            />
                            <div
                              className="bg-red-400 w-full"
                              style={{ height: `${negativeHeight}%` }}
                              title={`${day.negative} negatief`}
                            />
                          </>
                        )}
                      </div>
                      <span className="text-xs text-gray-500 mt-1">
                        {day.date.slice(5)}
                      </span>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Legend */}
            <div className="flex items-center justify-center space-x-4 text-sm">
              <div className="flex items-center space-x-1">
                <div className="w-3 h-3 bg-green-500 rounded" />
                <span className="text-gray-600">Positief</span>
              </div>
              <div className="flex items-center space-x-1">
                <div className="w-3 h-3 bg-red-400 rounded" />
                <span className="text-gray-600">Negatief</span>
              </div>
            </div>

            {/* Summary stats */}
            <div className="grid grid-cols-4 gap-4 mt-4 text-sm">
              <div className="text-center p-3 bg-gray-50 rounded">
                <p className="text-gray-500">Laatste 7 dagen</p>
                <p className="font-semibold text-lg">
                  {analytics.daily_trends.slice(-7).reduce((sum, d) => sum + d.total, 0)}
                </p>
              </div>
              <div className="text-center p-3 bg-green-50 rounded">
                <p className="text-gray-500">Positief</p>
                <p className="font-semibold text-lg text-green-600">
                  {analytics.daily_trends.slice(-7).reduce((sum, d) => sum + d.positive, 0)}
                </p>
              </div>
              <div className="text-center p-3 bg-red-50 rounded">
                <p className="text-gray-500">Negatief</p>
                <p className="font-semibold text-lg text-red-600">
                  {analytics.daily_trends.slice(-7).reduce((sum, d) => sum + d.negative, 0)}
                </p>
              </div>
              <div className="text-center p-3 bg-blue-50 rounded">
                <p className="text-gray-500">Gem. Score</p>
                <p className="font-semibold text-lg text-blue-600">
                  {(analytics.daily_trends.slice(-7)
                    .filter(d => d.total > 0)
                    .reduce((sum, d) => sum + d.approval_rate, 0) /
                    Math.max(analytics.daily_trends.slice(-7).filter(d => d.total > 0).length, 1) * 100
                  ).toFixed(0)}%
                </p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <BarChart3 className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>Nog geen feedback data beschikbaar</p>
          </div>
        )}
      </div>

      {/* Quality Score Distribution */}
      <div className="bg-white rounded-lg border border-gray-200 p-6">
        <div className="flex items-center space-x-3 mb-4">
          <BarChart3 className="w-5 h-5 text-purple-600" />
          <h3 className="text-lg font-medium text-gray-900">Kwaliteitsscores per Dimensie</h3>
        </div>

        {analytics?.quality_distribution && analytics.quality_distribution.length > 0 ? (
          <div className="space-y-4">
            {analytics.quality_distribution.map((dist) => (
              <div key={dist.dimension} className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-gray-700">
                    {DIMENSION_LABELS[dist.dimension] || dist.dimension}
                  </span>
                  <span className="text-sm text-gray-500">
                    Gem: {(dist.avg_overall * 100).toFixed(0)}%
                  </span>
                </div>
                <div className="flex space-x-2">
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <ThumbsUp className="w-3 h-3 text-green-500" />
                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-green-500 rounded-full"
                          style={{ width: `${dist.avg_positive * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-10 text-right">
                        {(dist.avg_positive * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center space-x-2">
                      <ThumbsDown className="w-3 h-3 text-red-500" />
                      <div className="flex-1 h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-red-500 rounded-full"
                          style={{ width: `${dist.avg_negative * 100}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500 w-10 text-right">
                        {(dist.avg_negative * 100).toFixed(0)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            ))}

            <p className="text-xs text-gray-500 mt-4">
              Vergelijking van gemiddelde kwaliteitsscores voor positieve vs negatieve feedback.
              Hogere scores bij negatieve feedback kunnen wijzen op andere oorzaken van ontevredenheid.
            </p>
          </div>
        ) : (
          <div className="text-center py-8 text-gray-500">
            <BarChart3 className="w-12 h-12 mx-auto mb-2 text-gray-300" />
            <p>Nog geen kwaliteitsdata beschikbaar</p>
          </div>
        )}
      </div>

      {/* Hallucination Stats */}
      {analytics?.hallucination_feedback && analytics.hallucination_feedback.total_with_hallucination > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <AlertTriangle className="w-5 h-5 text-amber-600" />
            <h3 className="text-lg font-medium text-gray-900">Hallucinatie Feedback</h3>
          </div>

          <div className="grid grid-cols-3 gap-4 text-sm">
            <div className="text-center p-3 bg-amber-50 rounded">
              <p className="text-gray-500">Met Hallucinatie</p>
              <p className="font-semibold text-lg text-amber-600">
                {analytics.hallucination_feedback.total_with_hallucination}
              </p>
            </div>
            <div className="text-center p-3 bg-green-50 rounded">
              <p className="text-gray-500">Toch Positief</p>
              <p className="font-semibold text-lg text-green-600">
                {analytics.hallucination_feedback.positive_despite_hallucination}
              </p>
            </div>
            <div className="text-center p-3 bg-red-50 rounded">
              <p className="text-gray-500">Negatief</p>
              <p className="font-semibold text-lg text-red-600">
                {analytics.hallucination_feedback.negative_due_to_hallucination}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Recent Negative Feedback */}
      {analytics?.recent_negative && analytics.recent_negative.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <div className="flex items-center space-x-3 mb-4">
            <ThumbsDown className="w-5 h-5 text-red-600" />
            <h3 className="text-lg font-medium text-gray-900">Recente Negatieve Feedback</h3>
          </div>

          <div className="space-y-3 max-h-60 overflow-y-auto">
            {analytics.recent_negative.map((fb) => (
              <div key={fb.id} className="p-3 bg-red-50 rounded-lg text-sm">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-gray-700 font-medium truncate flex-1">
                    {fb.original_question}
                  </span>
                  <span className="text-xs text-gray-500 ml-2">
                    {formatDate(fb.timestamp)}
                  </span>
                </div>
                {fb.comment && (
                  <p className="text-gray-600 text-xs mt-1 italic">
                    "{fb.comment}"
                  </p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  )
}
