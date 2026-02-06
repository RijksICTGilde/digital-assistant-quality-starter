import { useState, useRef } from 'react'
import { RotateCcw, Save, AlertTriangle, Download, Upload } from 'lucide-react'
import { adminAPI } from '../../services/admin_api'

const DIMENSION_LABELS = {
  relevance: { label: 'Relevantie', description: 'Beantwoordt het antwoord de vraag?' },
  tone: { label: 'Toon', description: 'Is de toon professioneel en passend?' },
  completeness: { label: 'Volledigheid', description: 'Is de informatie compleet?' },
  policy_compliance: { label: 'Beleidsconformiteit', description: 'Voldoet het aan beleidskaders?' }
}

export default function ThresholdEditor({ config, defaults, onUpdate }) {
  const [localValues, setLocalValues] = useState({})
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(null)
  const fileInputRef = useRef(null)

  const getValue = (key) => {
    if (localValues[key] !== undefined) return localValues[key]
    if (key === 'policy_compliance') {
      return config?.thresholds?.policy_compliance ?? defaults?.thresholds?.policy_compliance ?? 0.6
    }
    return config?.thresholds?.[key] ?? defaults?.thresholds?.[key] ?? 0.5
  }

  const getDefault = (key) => {
    if (key === 'policy_compliance') {
      return defaults?.thresholds?.policy_compliance ?? 0.6
    }
    return defaults?.thresholds?.[key] ?? 0.5
  }

  const isModified = (key) => {
    const current = getValue(key)
    const defaultVal = getDefault(key)
    return Math.abs(current - defaultVal) > 0.001
  }

  const hasChanges = Object.keys(localValues).length > 0

  const handleChange = (key, value) => {
    setLocalValues(prev => ({
      ...prev,
      [key]: parseFloat(value)
    }))
  }

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      // Backend expects snake_case for policy_compliance due to @JsonProperty
      const thresholds = {
        relevance: localValues.relevance ?? getValue('relevance'),
        tone: localValues.tone ?? getValue('tone'),
        completeness: localValues.completeness ?? getValue('completeness'),
        policy_compliance: localValues.policy_compliance ?? getValue('policy_compliance')
      }
      console.log('Saving thresholds:', thresholds)
      const response = await adminAPI.setAllThresholds(thresholds)
      console.log('Save response:', response)
      setLocalValues({})
      onUpdate?.()
    } catch (err) {
      console.error('Save error:', err)
      setError(err.response?.data?.message || err.message || 'Kon niet opslaan')
    } finally {
      setSaving(false)
    }
  }

  const handleResetAll = async () => {
    setSaving(true)
    setError(null)
    try {
      await adminAPI.resetThresholds()
      setLocalValues({})
      onUpdate?.()
    } catch (err) {
      setError(err.message || 'Kon niet resetten')
    } finally {
      setSaving(false)
    }
  }

  const handleResetOne = async (key) => {
    // Map frontend key to backend key
    const backendKey = key === 'policy_compliance' ? 'policyCompliance' : key
    setSaving(true)
    try {
      await adminAPI.resetThreshold(backendKey)
      setLocalValues(prev => {
        const next = { ...prev }
        delete next[key]
        return next
      })
      onUpdate?.()
    } catch (err) {
      setError(err.message || 'Kon niet resetten')
    } finally {
      setSaving(false)
    }
  }

  const getColorClass = (value) => {
    if (value >= 0.7) return 'bg-green-500'
    if (value >= 0.5) return 'bg-amber-500'
    return 'bg-red-500'
  }

  const handleExport = async () => {
    try {
      const response = await adminAPI.exportConfig()
      const configData = response.data
      const blob = new Blob([JSON.stringify(configData, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `gemeente-ai-config-${new Date().toISOString().slice(0, 10)}.json`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch (err) {
      setError('Exporteren mislukt: ' + (err.message || 'onbekende fout'))
    }
  }

  const handleImport = async (event) => {
    const file = event.target.files?.[0]
    if (!file) return

    try {
      const text = await file.text()
      const configData = JSON.parse(text)
      await adminAPI.importConfig(configData)
      setLocalValues({})
      onUpdate?.()
      alert('Configuratie succesvol geïmporteerd!')
    } catch (err) {
      setError('Importeren mislukt: ' + (err.message || 'ongeldig bestand'))
    } finally {
      // Reset file input
      if (fileInputRef.current) {
        fileInputRef.current.value = ''
      }
    }
  }

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-medium text-gray-900">Kwaliteitsdrempels</h3>
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
            onClick={handleResetAll}
            disabled={saving}
            className="flex items-center space-x-1 px-3 py-1.5 text-gray-600 text-sm hover:bg-gray-100 rounded-lg disabled:opacity-50"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Reset Alles</span>
          </button>
          <button
            onClick={handleExport}
            className="flex items-center space-x-1 px-3 py-1.5 text-gray-600 text-sm hover:bg-gray-100 rounded-lg"
            title="Exporteer configuratie"
          >
            <Download className="w-4 h-4" />
          </button>
          <label className="flex items-center space-x-1 px-3 py-1.5 text-gray-600 text-sm hover:bg-gray-100 rounded-lg cursor-pointer" title="Importeer configuratie">
            <Upload className="w-4 h-4" />
            <input
              ref={fileInputRef}
              type="file"
              accept=".json"
              onChange={handleImport}
              className="hidden"
            />
          </label>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-700 rounded-lg flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      <p className="text-sm text-gray-500 mb-4">
        Antwoorden onder deze drempels worden automatisch verbeterd.
      </p>

      <div className="space-y-4">
        {Object.entries(DIMENSION_LABELS).map(([key, { label, description }]) => {
          const value = getValue(key)
          const defaultVal = getDefault(key)
          const modified = isModified(key)

          return (
            <div key={key} className="space-y-1">
              <div className="flex items-center justify-between">
                <div>
                  <span className={`text-sm font-medium ${modified ? 'text-amber-600' : 'text-gray-700'}`}>
                    {label}
                  </span>
                  <p className="text-xs text-gray-400">{description}</p>
                </div>
                <div className="flex items-center space-x-2">
                  <span className={`text-sm font-mono ${modified ? 'text-amber-600 font-bold' : 'text-gray-600'}`}>
                    {(value * 100).toFixed(0)}%
                  </span>
                  <span className="text-xs text-gray-400">
                    (standaard: {(defaultVal * 100).toFixed(0)}%)
                  </span>
                  {modified && (
                    <button
                      onClick={() => handleResetOne(key)}
                      className="text-xs text-blue-600 hover:text-blue-800"
                    >
                      Reset
                    </button>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-3">
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={value}
                  onChange={(e) => handleChange(key, e.target.value)}
                  className="flex-1 h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer"
                />
                <div className={`w-3 h-3 rounded-full ${getColorClass(value)}`} />
              </div>
            </div>
          )
        })}
      </div>

      {config?.is_modified && (
        <div className="mt-4 p-3 bg-amber-50 border border-amber-200 rounded-lg">
          <p className="text-sm text-amber-700">
            Configuratie is aangepast ten opzichte van de standaardwaarden.
          </p>
        </div>
      )}
    </div>
  )
}
