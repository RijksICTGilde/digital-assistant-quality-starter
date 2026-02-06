import { useState } from 'react'
import { RotateCcw, Save, Database, AlertTriangle } from 'lucide-react'
import { adminAPI } from '../../services/admin_api'

export default function RagConfigEditor({ config, defaults, knowledgeStats, onUpdate }) {
  const [localSimilarity, setLocalSimilarity] = useState(null)
  const [localMaxResults, setLocalMaxResults] = useState(null)
  const [localMaxRounds, setLocalMaxRounds] = useState(null)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)

  const similarity = localSimilarity ?? config?.rag?.similarity_threshold ?? 0.5
  const maxResults = localMaxResults ?? config?.rag?.max_results ?? 5
  const maxRounds = localMaxRounds ?? config?.max_improvement_rounds ?? 1

  const defaultSimilarity = defaults?.rag?.similarity_threshold ?? 0.5
  const defaultMaxResults = defaults?.rag?.max_results ?? 5
  const defaultMaxRounds = defaults?.max_improvement_rounds ?? 1

  const similarityModified = Math.abs(similarity - defaultSimilarity) > 0.001
  const maxResultsModified = maxResults !== defaultMaxResults
  const maxRoundsModified = maxRounds !== defaultMaxRounds
  const hasChanges = localSimilarity !== null || localMaxResults !== null || localMaxRounds !== null

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const promises = []
      if (localSimilarity !== null) {
        promises.push(adminAPI.setSimilarityThreshold(localSimilarity))
      }
      if (localMaxResults !== null) {
        promises.push(adminAPI.setMaxResults(localMaxResults))
      }
      if (localMaxRounds !== null) {
        promises.push(adminAPI.setMaxImprovementRounds(localMaxRounds))
      }
      await Promise.all(promises)
      setLocalSimilarity(null)
      setLocalMaxResults(null)
      setLocalMaxRounds(null)
      onUpdate?.()
    } catch (err) {
      setError(err.message || 'Kon niet opslaan')
    } finally {
      setSaving(false)
    }
  }

  const handleResetRag = async () => {
    setSaving(true)
    setError(null)
    try {
      await adminAPI.resetRag()
      setLocalSimilarity(null)
      setLocalMaxResults(null)
      setLocalMaxRounds(null)
      onUpdate?.()
    } catch (err) {
      setError(err.message || 'Kon niet resetten')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <Database className="w-5 h-5 text-blue-600" />
          <h3 className="text-lg font-medium text-gray-900">RAG & Verbeteringsinstellingen</h3>
        </div>
        <div className="flex items-center space-x-2">
          {hasChanges && (
            <button
              onClick={handleSave}
              disabled={saving}
              className="flex items-center space-x-1 px-3 py-1.5 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              <span>Opslaan</span>
            </button>
          )}
          <button
            onClick={handleResetRag}
            disabled={saving}
            className="flex items-center space-x-1 px-3 py-1.5 text-gray-600 text-sm hover:bg-gray-100 rounded-lg disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      {/* Knowledge Base Stats */}
      {knowledgeStats && (
        <div className="mb-6 p-4 bg-gray-50 rounded-lg">
          <p className="text-sm font-medium text-gray-700 mb-2">Kennisbank Status</p>
          <div className="grid grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-gray-500">Documenten</p>
              <p className="font-semibold">{knowledgeStats.total_documents || 0}</p>
            </div>
            <div>
              <p className="text-gray-500">Chunks</p>
              <p className="font-semibold">{knowledgeStats.total_chunks || 0}</p>
            </div>
            <div>
              <p className="text-gray-500">Status</p>
              <p className={`font-semibold ${knowledgeStats.is_loaded ? 'text-green-600' : 'text-amber-600'}`}>
                {knowledgeStats.is_loaded ? 'Geladen' : 'Laden...'}
              </p>
            </div>
          </div>
        </div>
      )}

      <div className="space-y-6">
        {/* Similarity Threshold */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className={`text-sm font-medium ${similarityModified ? 'text-amber-600' : 'text-gray-700'}`}>
                Similarity Threshold
              </span>
              <p className="text-xs text-gray-400">
                Minimale relevantiescore voor bronnen (hoger = strengere filtering)
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-mono ${similarityModified ? 'text-amber-600 font-bold' : 'text-gray-600'}`}>
                {(similarity * 100).toFixed(0)}%
              </span>
              <span className="text-xs text-gray-400">
                (standaard: {(defaultSimilarity * 100).toFixed(0)}%)
              </span>
            </div>
          </div>
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={similarity}
            onChange={(e) => setLocalSimilarity(parseFloat(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0% (alles)</span>
            <span>100% (exact)</span>
          </div>
        </div>

        {/* Max Results */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className={`text-sm font-medium ${maxResultsModified ? 'text-amber-600' : 'text-gray-700'}`}>
                Max Resultaten
              </span>
              <p className="text-xs text-gray-400">
                Maximum aantal bronnen per zoekopdracht
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-mono ${maxResultsModified ? 'text-amber-600 font-bold' : 'text-gray-600'}`}>
                {maxResults}
              </span>
              <span className="text-xs text-gray-400">
                (standaard: {defaultMaxResults})
              </span>
            </div>
          </div>
          <input
            type="range"
            min="1"
            max="10"
            step="1"
            value={maxResults}
            onChange={(e) => setLocalMaxResults(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>1</span>
            <span>10</span>
          </div>
        </div>

        {/* Max Improvement Rounds */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div>
              <span className={`text-sm font-medium ${maxRoundsModified ? 'text-amber-600' : 'text-gray-700'}`}>
                Max Verbeterrondes
              </span>
              <p className="text-xs text-gray-400">
                Maximum aantal keren dat een antwoord verbeterd wordt
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <span className={`text-sm font-mono ${maxRoundsModified ? 'text-amber-600 font-bold' : 'text-gray-600'}`}>
                {maxRounds}
              </span>
              <span className="text-xs text-gray-400">
                (standaard: {defaultMaxRounds})
              </span>
            </div>
          </div>
          <input
            type="range"
            min="0"
            max="5"
            step="1"
            value={maxRounds}
            onChange={(e) => setLocalMaxRounds(parseInt(e.target.value))}
            className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0 (geen)</span>
            <span>5 (max)</span>
          </div>
        </div>
      </div>

      {/* Info Box */}
      <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-700">
          <strong>Let op:</strong> Hogere similarity threshold betekent relevantere bronnen, maar mogelijk minder resultaten.
          Meer verbeterrondes verhogen de kwaliteit maar ook de responstijd.
        </p>
      </div>
    </div>
  )
}
