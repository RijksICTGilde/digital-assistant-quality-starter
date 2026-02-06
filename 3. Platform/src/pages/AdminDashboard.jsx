import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowLeft, RefreshCw, Settings, MessageSquare, Database,
  Activity, AlertTriangle, BookOpen, BarChart3, Sliders
} from 'lucide-react'
import { adminAPI } from '../services/admin_api'
import FeedbackStats from '../components/admin/FeedbackStats'
import ThresholdEditor from '../components/admin/ThresholdEditor'
import RagConfigEditor from '../components/admin/RagConfigEditor'
import ReviewQueue from '../components/admin/ReviewQueue'
import GoldenAnswerManager from '../components/admin/GoldenAnswerManager'
import AnalyticsDashboard from '../components/admin/AnalyticsDashboard'
import AuditLogPanel from '../components/admin/AuditLogPanel'

const TABS = [
  { id: 'overview', label: 'Overzicht', icon: Activity },
  { id: 'config', label: 'Configuratie', icon: Sliders },
  { id: 'quality', label: 'Kwaliteitsbewaking', icon: AlertTriangle },
  { id: 'analytics', label: 'Analytics', icon: BarChart3 },
]

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('overview')
  const [config, setConfig] = useState(null)
  const goldenAnswerRef = useRef(null)
  const [defaults, setDefaults] = useState(null)
  const [feedbackStats, setFeedbackStats] = useState(null)
  const [reviewStats, setReviewStats] = useState(null)
  const [knowledgeStats, setKnowledgeStats] = useState(null)
  const [goldenStats, setGoldenStats] = useState(null)
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [lastUpdate, setLastUpdate] = useState(null)

  // Set page title for admin
  useEffect(() => {
    const originalTitle = document.title
    document.title = 'Admin - AI Kwaliteitsassistent'
    return () => { document.title = originalTitle }
  }, [])

  const loadData = async () => {
    setLoading(true)
    setError(null)
    try {
      const [configRes, defaultsRes, feedbackRes, reviewRes, knowledgeRes, goldenRes, healthRes] = await Promise.all([
        adminAPI.getConfig(),
        adminAPI.getDefaults(),
        adminAPI.getFeedbackStats(),
        adminAPI.getReviewStats(),
        adminAPI.getKnowledgeStats(),
        adminAPI.getGoldenAnswerStats(),
        adminAPI.getHealth()
      ])
      setConfig(configRes.data)
      setDefaults(defaultsRes.data)
      setFeedbackStats(feedbackRes.data)
      setReviewStats(reviewRes.data)
      setKnowledgeStats(knowledgeRes.data)
      setGoldenStats(goldenRes.data)
      setHealth(healthRes.data)
      setLastUpdate(new Date())
    } catch (err) {
      setError(err.message || 'Failed to load data')
      console.error('Failed to load admin data:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleConfigUpdate = async () => {
    try {
      const configRes = await adminAPI.getConfig()
      setConfig(configRes.data)
      setLastUpdate(new Date())
    } catch (err) {
      console.error('Failed to refresh config:', err)
    }
  }

  const handleFeedbackRefresh = async () => {
    try {
      const feedbackRes = await adminAPI.getFeedbackStats()
      setFeedbackStats(feedbackRes.data)
      setLastUpdate(new Date())
    } catch (err) {
      console.error('Failed to refresh feedback stats:', err)
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="flex items-center space-x-3 text-gray-600">
          <RefreshCw className="w-6 h-6 animate-spin" />
          <span>Laden...</span>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <Link to="/" className="p-2 hover:bg-gray-100 rounded-lg transition-colors">
                <ArrowLeft className="w-5 h-5 text-gray-600" />
              </Link>
              <div>
                <h1 className="text-xl font-semibold text-gray-900">Admin Dashboard</h1>
                <p className="text-sm text-gray-500">AI Kwaliteitsmanagement</p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              {lastUpdate && (
                <span className="text-xs text-gray-400">
                  {lastUpdate.toLocaleTimeString('nl-NL')}
                </span>
              )}
              <button
                onClick={loadData}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="Vernieuwen"
              >
                <RefreshCw className={`w-5 h-5 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>
          </div>

          {/* Tab Navigation */}
          <div className="flex space-x-1 mt-4 -mb-px">
            {TABS.map((tab) => {
              const Icon = tab.icon
              const isActive = activeTab === tab.id
              // Show badge for quality tab if there are pending reviews
              const badge = tab.id === 'quality' && reviewStats?.pending_count > 0
                ? reviewStats.pending_count
                : null

              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center space-x-2 px-4 py-2 text-sm font-medium rounded-t-lg border-b-2 transition-colors ${
                    isActive
                      ? 'border-blue-600 text-blue-600 bg-blue-50'
                      : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                  {badge && (
                    <span className="px-1.5 py-0.5 text-xs bg-amber-500 text-white rounded-full">
                      {badge}
                    </span>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      </header>

      {/* Error Banner */}
      {error && (
        <div className="bg-red-50 border-b border-red-200 px-4 py-3">
          <div className="max-w-6xl mx-auto flex items-center justify-between">
            <span className="text-red-700">{error}</span>
            <button onClick={() => setError(null)} className="text-red-500 hover:text-red-700">
              Sluiten
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6">
        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-6">
            {/* Status Cards */}
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {/* Health Status */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center space-x-3">
                  <div className={`p-3 rounded-lg ${health?.status === 'healthy' ? 'bg-green-100' : 'bg-red-100'}`}>
                    <Activity className={`w-6 h-6 ${health?.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Systeem</p>
                    <p className={`text-lg font-semibold ${health?.status === 'healthy' ? 'text-green-600' : 'text-red-600'}`}>
                      {health?.status === 'healthy' ? 'Operationeel' : 'Probleem'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Knowledge Base */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center space-x-3">
                  <div className="p-3 bg-blue-100 rounded-lg">
                    <Database className="w-6 h-6 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Kennisbank</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {knowledgeStats?.total_chunks?.toLocaleString() || 0} chunks
                    </p>
                    {knowledgeStats?.loaded_from_cache && (
                      <p className="text-xs text-gray-400">uit cache</p>
                    )}
                  </div>
                </div>
              </div>

              {/* Config Status */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center space-x-3">
                  <div className={`p-3 rounded-lg ${config?.is_modified ? 'bg-amber-100' : 'bg-gray-100'}`}>
                    <Settings className={`w-6 h-6 ${config?.is_modified ? 'text-amber-600' : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Configuratie</p>
                    <p className={`text-lg font-semibold ${config?.is_modified ? 'text-amber-600' : 'text-gray-600'}`}>
                      {config?.is_modified ? 'Aangepast' : 'Standaard'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Total Feedback */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center space-x-3">
                  <div className="p-3 bg-purple-100 rounded-lg">
                    <MessageSquare className="w-6 h-6 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Feedback</p>
                    <p className="text-lg font-semibold text-gray-900">
                      {feedbackStats?.total_feedback || 0}
                    </p>
                    {feedbackStats?.approval_rate > 0 && (
                      <p className="text-xs text-green-600">
                        {Math.round(feedbackStats.approval_rate * 100)}% positief
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Review Queue */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center space-x-3">
                  <div className={`p-3 rounded-lg ${reviewStats?.pending_count > 0 ? 'bg-amber-100' : 'bg-gray-100'}`}>
                    <AlertTriangle className={`w-6 h-6 ${reviewStats?.pending_count > 0 ? 'text-amber-600' : 'text-gray-500'}`} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Review Queue</p>
                    <p className={`text-lg font-semibold ${reviewStats?.pending_count > 0 ? 'text-amber-600' : 'text-gray-600'}`}>
                      {reviewStats?.pending_count || 0} wachtend
                    </p>
                  </div>
                </div>
              </div>

              {/* Golden Answers */}
              <div className="bg-white rounded-xl border border-gray-200 p-5">
                <div className="flex items-center space-x-3">
                  <div className="p-3 bg-indigo-100 rounded-lg">
                    <BookOpen className="w-6 h-6 text-indigo-600" />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Golden Answers</p>
                    <p className="text-lg font-semibold text-indigo-600">
                      {goldenStats?.active_answers || 0} actief
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Quick Stats */}
            <div className="bg-white rounded-xl border border-gray-200 p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Huidige Instellingen</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">
                    {Math.round((config?.thresholds?.relevance || 0.6) * 100)}%
                  </p>
                  <p className="text-sm text-gray-500">Relevantie drempel</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">
                    {Math.round((config?.thresholds?.tone || 0.7) * 100)}%
                  </p>
                  <p className="text-sm text-gray-500">Toon drempel</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">
                    {config?.rag?.max_results || 5}
                  </p>
                  <p className="text-sm text-gray-500">Max bronnen</p>
                </div>
                <div className="text-center p-4 bg-gray-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-600">
                    {config?.max_improvement_rounds || 2}
                  </p>
                  <p className="text-sm text-gray-500">Verbeterrondes</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Config Tab */}
        {activeTab === 'config' && (
          <div className="space-y-6">
            <ThresholdEditor
              config={config}
              defaults={defaults}
              onUpdate={handleConfigUpdate}
            />
            <RagConfigEditor
              config={config}
              defaults={defaults}
              knowledgeStats={knowledgeStats}
              onUpdate={handleConfigUpdate}
            />
            <AuditLogPanel />
          </div>
        )}

        {/* Quality Tab */}
        {activeTab === 'quality' && (
          <div className="space-y-6">
            <ReviewQueue
              onStatsUpdate={setReviewStats}
              onGoldenAnswerImported={() => goldenAnswerRef.current?.refresh()}
            />
            <GoldenAnswerManager ref={goldenAnswerRef} />
          </div>
        )}

        {/* Analytics Tab */}
        {activeTab === 'analytics' && (
          <div className="space-y-6">
            <FeedbackStats stats={feedbackStats} onRefresh={handleFeedbackRefresh} />
            <AnalyticsDashboard />
          </div>
        )}
      </main>
    </div>
  )
}
