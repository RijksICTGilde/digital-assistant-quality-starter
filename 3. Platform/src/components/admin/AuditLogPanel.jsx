import { useState, useEffect } from 'react'
import { Clock, ChevronDown, ChevronUp, RefreshCw } from 'lucide-react'
import { adminAPI } from '../../services/admin_api'

export default function AuditLogPanel() {
  const [auditLogs, setAuditLogs] = useState([])
  const [loading, setLoading] = useState(true)
  const [showLogs, setShowLogs] = useState(true)

  const loadLogs = async () => {
    setLoading(true)
    try {
      const res = await adminAPI.getRecentAuditLogs(20)
      setAuditLogs(res.data)
    } catch (err) {
      console.error('Failed to load audit logs:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadLogs()
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

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div
        className="flex items-center justify-between cursor-pointer"
        onClick={() => setShowLogs(!showLogs)}
      >
        <div className="flex items-center space-x-3">
          <Clock className="w-5 h-5 text-gray-600" />
          <h3 className="text-lg font-medium text-gray-900">Configuratie Wijzigingen</h3>
          {auditLogs.length > 0 && (
            <span className="px-2 py-0.5 bg-gray-100 text-gray-600 text-xs rounded-full">
              {auditLogs.length} recent
            </span>
          )}
        </div>
        <div className="flex items-center space-x-2">
          <button
            onClick={(e) => {
              e.stopPropagation()
              loadLogs()
            }}
            disabled={loading}
            className="p-1.5 text-gray-500 hover:text-gray-700 hover:bg-gray-100 rounded-lg disabled:opacity-50"
            title="Vernieuwen"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          {showLogs ? (
            <ChevronUp className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </div>

      {showLogs && (
        <div className="mt-4 space-y-2 max-h-60 overflow-y-auto">
          {loading ? (
            <div className="flex items-center justify-center py-4 text-gray-500">
              <RefreshCw className="w-4 h-4 animate-spin mr-2" />
              <span>Laden...</span>
            </div>
          ) : auditLogs.length > 0 ? (
            auditLogs.map((log) => (
              <div key={log.id} className="flex items-center justify-between p-2 bg-gray-50 rounded text-sm">
                <div className="flex items-center space-x-2">
                  <span className={`px-2 py-0.5 text-xs rounded ${
                    log.action === 'set' ? 'bg-blue-100 text-blue-700' :
                    log.action === 'reset' ? 'bg-amber-100 text-amber-700' :
                    'bg-gray-100 text-gray-700'
                  }`}>
                    {log.action}
                  </span>
                  <span className="text-gray-700">
                    {log.config_type}
                    {log.config_key && ` / ${log.config_key}`}
                  </span>
                </div>
                <div className="flex items-center space-x-3 text-xs text-gray-500">
                  {log.old_value && log.new_value && (
                    <span>
                      {log.old_value} → {log.new_value}
                    </span>
                  )}
                  <span>{formatDate(log.timestamp)}</span>
                </div>
              </div>
            ))
          ) : (
            <p className="text-center text-gray-500 py-4">
              Nog geen configuratie wijzigingen gelogd
            </p>
          )}
        </div>
      )}
    </div>
  )
}
