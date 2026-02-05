import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Send, 
  Bot, 
  User, 
  RotateCcw, 
  HelpCircle, 
  Download,
  ExternalLink,
  AlertCircle,
  CheckCircle,
  Clock,
  ThumbsUp,
  ThumbsDown,
  Zap,
  FileText,
  Shield,
  Settings
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { enhancedAPI, demoResponses } from '../services/enhanced_api'
import DocumentViewer from './DocumentViewer'

const QUICK_SUGGESTIONS = {
  'digital-guide': [
    'Welke stakeholders moet ik betrekken bij een AI implementatie?',
    'Hoe zorg ik voor draagvlak in de organisatie?',
    'Wat zijn de belangrijkste risico\'s die ik moet managen?'
  ],
  'civil-servant': [
    'Welke GDPR maatregelen zijn nodig voor een chatbot?',
    'Hoe ga ik om met de AI Act verplichtingen?',
    'Wat zijn best practices voor transparantie?'
  ],
  'it-manager': [
    'Welke architectuur principes moet ik volgen?',
    'Hoe voorkom ik vendor lock-in?',
    'Welke security maatregelen zijn essentieel?'
  ],
  'project-manager': [
    'Hoe plan ik een AI implementatie stap voor stap?',
    'Welke success metrics moet ik definiëren?',
    'Hoe manage ik risico\'s bij AI projecten?'
  ],
  'developer': [
    'Welke open standaarden moet ik gebruiken?',
    'Hoe implementeer ik Common Ground principes?',
    'Welke APIs zijn beschikbaar voor gemeentes?'
  ],
  'other': [
    'Wat zijn de belangrijkste juridische aandachtspunten?',
    'Hoe begin ik met digitale transformatie?',
    'Welke best practices moet ik kennen?'
  ]
}

const cleanRawResponse = (rawText) => {
  if (!rawText || typeof rawText !== 'string') return rawText

  // Remove Python dict prefixes and common parsing artifacts
  let cleaned = rawText
    .replace(/^StructuredAIResponse\(.*?main_answer=["']/, '')
    .replace(/^QuickAnswer\(.*?answer=["']/, '')
    .replace(/^ComplianceAnalysis\(.*?main_answer=["']/, '')
    .replace(/^TechnicalGuidance\(.*?main_answer=["']/, '')
    .replace(/main_answer=["']/, '')
    .replace(/answer=["']/, '')
    .replace(/["'], response_type=.*$/, '')
    .replace(/["'], confidence_level=.*$/, '')
    .replace(/["'], action_items=.*$/, '')
    .replace(/["'], .*?\)$/, '')
    .replace(/\\n/g, '\n')
    .replace(/\\"/g, '"')
    .replace(/\\'/g, "'")
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  // If still looks like raw data, try to extract meaningful content
  if (cleaned.includes('=') && cleaned.includes('(') && cleaned.includes(')')) {
    const matches = cleaned.match(/(?:main_)?answer[s]?[="']*([^,'"]*)/i)
    if (matches && matches[1]) {
      cleaned = matches[1].trim()
    }
  }

  return cleaned.length < 10 ? rawText : cleaned
}

// Helper functions remain the same...
const formatResponseType = (type) => {
  const types = {
    'structured': '📋 Gestructureerd',
    'quick': '⚡ Snel',
    'compliance': '🔒 Compliance',
    'technical': '⚙️ Technisch',
    'error_fallback': '⚠️ Fallback'
  }
  return types[type] || type
}

const formatConfidence = (confidence) => {
  if (typeof confidence === 'number') {
    return confidence >= 0.8 ? 'Hoog' : confidence >= 0.5 ? 'Gemiddeld' : 'Laag'
  }
  return confidence === 'high' ? 'Hoog' : confidence === 'medium' ? 'Gemiddeld' : 'Laag'
}

const formatProcessingTime = (time) => {
  if (!time) return ''
  return time < 1000 ? `${time}ms` : `${(time/1000).toFixed(1)}s`
}

const getConfidenceColor = (confidence) => {
  if (typeof confidence === 'number') {
    return confidence >= 0.8 ? 'text-chatbot-primary' : confidence >= 0.5 ? 'text-chatbot-secondary' : 'text-chatbot-neutral-600'
  }
  return confidence === 'high' ? 'text-chatbot-primary' : confidence === 'medium' ? 'text-chatbot-secondary' : 'text-chatbot-neutral-600'
}

const getRiskLevelColor = (level) => {
  return level === 'high' ? 'text-chatbot-neutral-700' : level === 'medium' ? 'text-chatbot-secondary' : 'text-chatbot-primary'
}

const generateWelcomeMessage = (context) => {
  const { role, projectPhase, focusAreas, customContext } = context
  
  let message = `**Je profiel:**
- **Rol:** ${role?.name || 'Niet gespecificeerd'}
- **Fase:** ${projectPhase || 'Niet gespecificeerd'}
- **Focus:** ${focusAreas?.map(area => area.name).join(', ') || 'Algemeen'}`
  
  if (customContext) {
    message += `\n- **Context:** ${customContext}`
  }
  
  message += `

Stel je vraag of kies een suggestie hieronder! 👇`
  
  return message
}

const EnhancedChatInterface = ({ userContext, onRestart }) => {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(true)
  const [viewingDocument, setViewingDocument] = useState(null)
  const [streamProgress, setStreamProgress] = useState(null) // For streaming progress
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    // Welcome message with enhanced context
    const welcomeMessage = {
      id: Date.now(),
      type: 'ai',
      content: generateWelcomeMessage(userContext),
      timestamp: new Date(),
      suggestions: QUICK_SUGGESTIONS[userContext.role?.id] || QUICK_SUGGESTIONS.other,
      enhanced: true
    }
    setMessages([welcomeMessage])
  }, [userContext])

  const handleSendMessage = async (message = inputValue.trim()) => {
    if (!message || isLoading) return

    const userMessage = {
      id: Date.now(),
      type: 'user',
      content: message,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInputValue('')
    setIsLoading(true)
    setShowSuggestions(false)
    setStreamProgress(null)

    try {
      let response

      // Try streaming first, fallback to regular if it fails
      try {
        response = await enhancedAPI.sendStreamingMessage(message, userContext, (event) => {
          // Update progress based on stream events
          setStreamProgress(event)
        })
      } catch (streamError) {
        console.warn('Streaming failed, falling back to regular API:', streamError)
        // Fallback to non-streaming
        try {
          response = await enhancedAPI.sendStructuredMessage(message, userContext)
        } catch (apiError) {
          console.warn('API call failed, using fallback:', apiError)
          response = {
            main_answer: `## API Error - Fallback Response

Er ging iets mis met de API verbinding. Dit is een fallback response.

**Oorspronkelijke vraag:** ${message}

### Troubleshooting:
1. Check of de backend draait op http://localhost:8080
2. Controleer of de GreenPT API key correct is geconfigureerd
3. Bekijk de browser console voor meer details

**Error:** ${apiError.message}`,
            response_type: "error_fallback",
            confidence_level: "low",
            knowledge_sources: [],
            follow_up_suggestions: [],
            needs_human_expert: true,
            processing_time_ms: 100
          }
        }
      }

      // Clear stream progress after completion
      setStreamProgress(null)

      // Always use structured response format
      let mainContent = response.main_answer || 'Geen antwoord beschikbaar'
      let actionItems = response.action_items || []
      let complianceChecks = response.compliance_checks || []

      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: mainContent,
        timestamp: new Date(),
        enhanced: true,
        responseType: 'structured',
        structured: response,
        confidence: response.confidence_level || response.confidence || 'medium',
        sources: response.knowledge_sources || response.sources || [],
        actionItems: actionItems,
        complianceChecks: complianceChecks,
        followUpSuggestions: response.follow_up_suggestions || [],
        needsHumanHelp: response.needs_human_expert || response.needs_human_help || false,
        processingTime: response.processing_time_ms || response.responseTime,
        qualityScores: response.quality_scores || null,
        qualityTrace: response.quality_trace || null,
        qualityImproved: response.quality_improved || false,
        qualityExplanation: response.quality_explanation || null,
        originalAnswer: response.original_answer || null,
        hallucinationDetected: response.hallucination_detected || false,
        ungroundedClaims: response.ungrounded_claims || [],
        improvementIterations: response.improvement_iterations || null,
        iterationHistory: response.iteration_history || null
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('Enhanced chat error:', error)
      setStreamProgress(null)
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: `## ⚠️ Fout bij Verwerken

Er ging iets mis bij het verwerken van je bericht. Probeer het opnieuw.

**Error:** ${error.message}
**Type:** ${error.name}

### Mogelijke oplossingen:
- Controleer je internetverbinding
- Herlaad de pagina
- Probeer een kortere vraag

Als het probleem aanhoudt, neem contact op met support.`,
        timestamp: new Date(),
        enhanced: true,
        responseType: 'error',
        confidence: 'low',
        sources: [],
        actionItems: [],
        complianceChecks: [],
        followUpSuggestions: [],
        needsHumanHelp: true
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleSuggestionClick = (suggestion) => {
    handleSendMessage(suggestion)
  }

  const handleFeedback = (messageId, isPositive) => {
    console.log(`Feedback for message ${messageId}: ${isPositive ? 'positive' : 'negative'}`)
  }

  const handleDocumentClick = (source) => {
    // First try to open original URL if available
    if (source && source.original_url && source.original_url !== '') {
      window.open(source.original_url, '_blank', 'noopener,noreferrer')
      return
    }
    
    // Fallback to regular URL if no original_url
    if (source && source.url && source.url !== '' && !source.url.startsWith('#') && !source.url.startsWith('/api/')) {
      window.open(source.url, '_blank', 'noopener,noreferrer')
      return
    }
    
    // Handle legacy string URLs or internal document viewing
    if (typeof source === 'string') {
      // Legacy URL handling
      const match = source.match(/\/api\/knowledge\/document\/(.+)$/)
      if (match) {
        const documentId = match[1]
        setViewingDocument(documentId)
      }
    } else if (source && source.document_id) {
      // Enhanced RAG source object with document_id - open internal viewer
      setViewingDocument(source.document_id)
    }
  }

  const renderEnhancedMessage = (message) => {
    if (!message.enhanced) {
      return <ReactMarkdown className="prose prose-sm max-w-none">{message.content}</ReactMarkdown>
    }

    return (
      <div className="space-y-4">
        {/* Main Content */}
        <div className="prose prose-sm max-w-none">
          <ReactMarkdown>{message.content}</ReactMarkdown>
        </div>

        {/* Action Items */}
        {message.actionItems && message.actionItems.length > 0 && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-blue-900 mb-3 flex items-center">
              <CheckCircle className="w-4 h-4 mr-2" />
              Action Items ({message.actionItems.length})
            </h4>
            <div className="space-y-2">
              {message.actionItems.slice(0, 4).map((item, index) => (
                <div key={index} className="flex items-start space-x-3 text-sm">
                  <div className={`flex-shrink-0 w-5 h-5 rounded-full flex items-center justify-center text-xs font-medium ${
                    item.priority === 'high' ? 'bg-red-100 text-red-700' :
                    item.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                    'bg-green-100 text-green-700'
                  }`}>
                    {index + 1}
                  </div>
                  <div className="flex-1">
                    <p className="font-medium text-chatbot-neutral-900">{item.title}</p>
                    <p className="text-chatbot-neutral-600 text-xs mt-1">{item.description}</p>
                    {item.timeline && (
                      <span className="inline-flex items-center text-xs text-chatbot-neutral-500 mt-1">
                        <Clock className="w-3 h-3 mr-1" />
                        {item.timeline}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Compliance Checks */}
        {message.complianceChecks && message.complianceChecks.length > 0 && (
          <div className="bg-chatbot-light border border-chatbot-neutral-200 rounded-lg p-4">
            <h4 className="text-sm font-semibold text-chatbot-dark mb-3 flex items-center">
              <Shield className="w-4 h-4 mr-2" />
              Compliance Status
            </h4>
            {message.complianceChecks.map((check, index) => (
              <div key={index} className="space-y-2 text-sm">
                <div className="flex justify-between items-center">
                  <span className="font-medium">{check.regulation}</span>
                  <span className={`px-2 py-1 rounded-full text-xs ${getRiskLevelColor(check.risk_level)}`}>
                    {check.status}
                  </span>
                </div>
                {check.requirements && check.requirements.length > 0 && (
                  <div>
                    <p className="font-medium text-chatbot-neutral-700">Vereisten:</p>
                    <ul className="list-disc list-inside text-chatbot-neutral-600 text-xs">
                      {check.requirements.slice(0, 3).map((req, idx) => (
                        <li key={idx}>{req}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Quality Dashboard */}
        {message.qualityScores && (
          <div className="bg-gradient-to-r from-emerald-50 to-teal-50 border border-emerald-200 rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <h4 className="text-sm font-semibold text-emerald-900 flex items-center">
                <Shield className="w-4 h-4 mr-2" />
                Kwaliteitscontrole
                {message.qualityImproved && (
                  <span className="ml-2 px-2 py-0.5 bg-amber-100 text-amber-800 text-xs rounded-full font-medium">
                    Verbeterd
                    {message.improvementIterations && message.improvementIterations >= 1 && ` (${message.improvementIterations}x)`}
                  </span>
                )}
              </h4>
            </div>
            <div className="grid grid-cols-2 gap-3 mb-3">
              {Object.entries(message.qualityScores).map(([dim, score]) => {
                const labels = {
                  relevance: 'Relevantie',
                  tone: 'Toon',
                  completeness: 'Volledigheid',
                  policy_compliance: 'Beleidsconformiteit'
                }
                const pct = Math.round(score * 100)
                const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'
                return (
                  <div key={dim} className="space-y-1">
                    <div className="flex justify-between text-xs">
                      <span className="text-emerald-800 font-medium">{labels[dim] || dim}</span>
                      <span className="text-emerald-700 font-semibold">{pct}%</span>
                    </div>
                    <div className="h-2 bg-emerald-100 rounded-full overflow-hidden">
                      <div className={`h-full ${color} rounded-full transition-all duration-500`}
                           style={{ width: `${pct}%` }} />
                    </div>
                  </div>
                )
              })}
            </div>
            {/* Hallucination Warning */}
            {message.hallucinationDetected && (
              <div className="bg-red-50 border border-red-300 rounded-lg p-3 mb-3">
                <div className="flex items-start space-x-2">
                  <AlertCircle className="w-4 h-4 text-red-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <p className="text-xs font-semibold text-red-800">
                      Mogelijk ongecontroleerde informatie gedetecteerd
                    </p>
                    <p className="text-xs text-red-700 mt-1">
                      Dit antwoord bevat mogelijk informatie die niet in de bronnen staat. Controleer de feiten.
                    </p>
                    {message.ungroundedClaims && message.ungroundedClaims.length > 0 && (
                      <details className="mt-2">
                        <summary className="text-xs text-red-600 cursor-pointer hover:text-red-800">
                          Bekijk mogelijke hallucinaties ({message.ungroundedClaims.length})
                        </summary>
                        <ul className="mt-1 text-xs text-red-700 list-disc list-inside space-y-1">
                          {message.ungroundedClaims.map((claim, i) => (
                            <li key={i}>{claim}</li>
                          ))}
                        </ul>
                      </details>
                    )}
                  </div>
                </div>
              </div>
            )}
            {message.qualityExplanation && (
              <p className="text-xs text-emerald-700 italic border-t border-emerald-200 pt-2">
                {message.qualityExplanation}
              </p>
            )}
            {/* Before/After Comparison when response was improved */}
            {message.qualityImproved && message.originalAnswer && (
              <details className="mt-3 border-t border-emerald-200 pt-2">
                <summary className="text-xs text-amber-700 cursor-pointer hover:text-amber-900 font-medium flex items-center">
                  <span className="mr-1">📊</span> Voor/Na vergelijking bekijken
                </summary>
                <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                    <div className="text-xs font-semibold text-red-800 mb-2 flex items-center">
                      <span className="w-2 h-2 rounded-full bg-red-500 mr-2" />
                      VOOR (Oorspronkelijk)
                    </div>
                    <div className="text-xs text-red-900 prose prose-xs max-w-none">
                      <ReactMarkdown>{message.originalAnswer}</ReactMarkdown>
                    </div>
                  </div>
                  <div className="bg-green-50 border border-green-200 rounded-lg p-3">
                    <div className="text-xs font-semibold text-green-800 mb-2 flex items-center">
                      <span className="w-2 h-2 rounded-full bg-green-500 mr-2" />
                      NA (Verbeterd)
                    </div>
                    <div className="text-xs text-green-900 prose prose-xs max-w-none">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  </div>
                </div>
              </details>
            )}
            {/* Iteration History - only shows when there was actual iterative improvement */}
            {message.qualityImproved && message.iterationHistory && message.iterationHistory.length > 1 && (
              <details className="mt-2">
                <summary className="text-xs text-blue-600 cursor-pointer hover:text-blue-800 font-medium">
                  📈 Kwaliteitsverloop bekijken ({message.iterationHistory.length} metingen)
                </summary>
                <div className="mt-2 bg-blue-50 rounded-lg p-3">
                  <div className="space-y-2">
                    {message.iterationHistory.map((iter, i) => {
                      const pct = Math.round(iter.overall_score * 100)
                      const isLast = i === message.iterationHistory.length - 1
                      const color = iter.passed ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'
                      return (
                        <div key={i} className={`flex items-center space-x-3 ${isLast ? 'font-medium' : ''}`}>
                          <span className="text-xs text-blue-700 w-16">
                            {iter.iteration === 0 ? 'Start' : `Ronde ${iter.iteration}`}
                          </span>
                          <div className="flex-1 h-3 bg-blue-100 rounded-full overflow-hidden">
                            <div
                              className={`h-full ${color} rounded-full transition-all duration-500`}
                              style={{ width: `${pct}%` }}
                            />
                          </div>
                          <span className={`text-xs w-12 text-right ${iter.passed ? 'text-emerald-700' : 'text-blue-700'}`}>
                            {pct}% {iter.passed && '✓'}
                          </span>
                        </div>
                      )
                    })}
                  </div>
                  <div className="mt-2 pt-2 border-t border-blue-200 text-xs text-blue-600">
                    Kwaliteit verbeterde van {Math.round(message.iterationHistory[0].overall_score * 100)}%
                    naar {Math.round(message.iterationHistory[message.iterationHistory.length - 1].overall_score * 100)}%
                  </div>
                </div>
              </details>
            )}
            {message.qualityTrace && message.qualityTrace.length > 0 && (
              <details className="mt-2">
                <summary className="text-xs text-emerald-600 cursor-pointer hover:text-emerald-800">
                  Kwaliteitsstappen bekijken ({message.qualityTrace.length} stappen)
                </summary>
                <div className="mt-2 space-y-1 pl-2 border-l-2 border-emerald-200">
                  {message.qualityTrace.map((step, i) => (
                    <div key={i} className="text-xs text-emerald-700 flex items-center space-x-2">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                      <span className="font-mono">
                        {step.action.replace(/_/g, ' ')}
                        {step.dimension && ` [${step.dimension}]`}
                        {step.score !== undefined && step.score !== null && ` → ${Math.round(step.score * 100)}%`}
                        {step.passed !== undefined && (step.passed ? ' ✓' : ' ✗')}
                      </span>
                    </div>
                  ))}
                </div>
              </details>
            )}
          </div>
        )}

        {/* Knowledge Sources */}
        {message.sources && message.sources.length > 0 && (
          <div className="border-t border-chatbot-neutral-200 pt-3">
            <p className="text-xs text-chatbot-neutral-500 mb-3 font-medium">
              📚 Bronnen uit Enhanced RAG Knowledge Base:
            </p>
            <div className="space-y-2">
              {message.sources.slice(0, 3).map((source, index) => (
                <div key={index} className="bg-white rounded-lg p-3 border border-chatbot-neutral-200">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-2 flex-1">
                      <button
                        onClick={() => handleDocumentClick(source)}
                        className="flex items-start space-x-2 text-chatbot-primary hover:underline text-left hover:bg-chatbot-neutral-50 rounded p-1 -m-1 transition-colors"
                        title={source.original_url ? `Klik om originele bron te openen: ${source.original_url}` : "Klik om document te bekijken"}
                      >
                        <div className="flex items-center space-x-1 flex-shrink-0 mt-0.5">
                          <FileText className="w-4 h-4" />
                          {(source.original_url || (source.url && !source.url.startsWith('#') && !source.url.startsWith('/api/'))) && (
                            <ExternalLink className="w-3 h-3 text-chatbot-neutral-500" />
                          )}
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm truncate">{source.title}</div>
                          {source.section_title && (
                            <div className="text-xs text-chatbot-neutral-600 mt-1">
                              📄 Sectie: {source.section_title}
                            </div>
                          )}
                          {source.file_path && (
                            <div className="text-xs text-chatbot-neutral-500 mt-1">
                              📁 {source.file_path.split('/').pop().replace('.md', '')}
                              {source.chunk_index !== undefined && source.total_chunks > 1 && (
                                <span className="ml-1 text-chatbot-neutral-400">
                                  (Deel {source.chunk_index + 1}/{source.total_chunks})
                                </span>
                              )}
                            </div>
                          )}
                          {source.snippet && (
                            <div className="text-xs text-chatbot-neutral-600 mt-2 line-clamp-2">
                              "{source.snippet.substring(0, 100)}..."
                            </div>
                          )}
                          {/* Show original URL info if available */}
                          {source.original_url && (
                            <div className="text-xs text-chatbot-primary mt-1 opacity-75">
                              🔗 {source.original_url.replace(/^https?:\/\//, '').split('/')[0]}
                            </div>
                          )}
                        </div>
                      </button>
                    </div>
                    <div className="flex flex-col items-end text-xs text-chatbot-neutral-400 ml-3">
                      <span className="font-medium">
                        {Math.round((source.relevance_score || 0.5) * 100)}%
                      </span>
                      <span className="text-xs">relevantie</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Follow-up Suggestions */}
        {message.followUpSuggestions && message.followUpSuggestions.length > 0 && (
          <div className="space-y-2">
            <p className="text-sm text-chatbot-neutral-600 font-medium">
              💡 Vervolgvragen:
            </p>
            {message.followUpSuggestions.slice(0, 2).map((suggestion, index) => (
              <button
                key={index}
                onClick={() => handleSuggestionClick(suggestion.question)}
                className="block w-full text-left text-sm bg-chatbot-neutral-50 hover:bg-chatbot-neutral-100 border border-chatbot-neutral-200 rounded-lg p-3 transition-colors duration-200"
              >
                <div className="flex items-center justify-between">
                  <span>{suggestion.question}</span>
                  <span className="text-xs text-chatbot-neutral-400">
                    {suggestion.category}
                  </span>
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Message Metadata */}
        <div className="flex items-center justify-between text-xs text-chatbot-neutral-400 border-t border-chatbot-neutral-100 pt-2">
          <div className="flex items-center space-x-3">
            <span>{formatResponseType(message.responseType)}</span>
            <span className={getConfidenceColor(message.confidence)}>
              Vertrouwen: {formatConfidence(message.confidence)}
            </span>
            {message.processingTime && (
              <span>⏱️ {formatProcessingTime(message.processingTime)}</span>
            )}
          </div>
          <div className="flex space-x-2">
            <button
              onClick={() => handleFeedback(message.id, true)}
              className="hover:text-green-600 transition-colors"
            >
              <ThumbsUp className="w-3 h-3" />
            </button>
            <button
              onClick={() => handleFeedback(message.id, false)}
              className="hover:text-red-600 transition-colors"
            >
              <ThumbsDown className="w-3 h-3" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  return (
    <div className="flex flex-col h-screen bg-chatbot-neutral-50">
      {/* Header */}
      <div className="bg-white border-b border-chatbot-neutral-200 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-8 h-8 bg-chatbot-primary rounded-lg flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-semibold text-chatbot-neutral-900">
                Enhanced AI Assistant
              </h1>
              <p className="text-sm text-chatbot-neutral-500">
                {userContext.role?.name} • Quality-Aware RAG • Embabel GOAP Agent • Live Streaming
              </p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={onRestart}
              className="flex items-center space-x-2 px-3 py-2 text-sm text-chatbot-neutral-600 hover:text-chatbot-neutral-900 hover:bg-chatbot-neutral-100 rounded-lg transition-colors"
            >
              <RotateCcw className="w-4 h-4" />
              <span>Opnieuw</span>
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              className={`flex items-start space-x-3 ${
                message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''
              }`}
            >
              <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${
                message.type === 'user' 
                  ? 'bg-chatbot-primary text-white' 
                  : 'bg-chatbot-neutral-200 text-chatbot-neutral-600'
              }`}>
                {message.type === 'user' ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
              </div>
              
              <div className={`flex-1 min-w-0 ${
                message.type === 'user' ? 'text-right' : ''
              }`}>
                <div className={`inline-block max-w-full p-4 rounded-lg ${
                  message.type === 'user'
                    ? 'bg-chatbot-primary text-white'
                    : 'bg-white border border-chatbot-neutral-200'
                }`}>
                  {message.type === 'user' ? (
                    <p className="text-sm">{message.content}</p>
                  ) : (
                    renderEnhancedMessage(message)
                  )}
                </div>
                
                {message.type === 'ai' && message.suggestions && showSuggestions && (
                  <div className="mt-3 space-y-2">
                    <p className="text-sm text-chatbot-neutral-600 font-medium">
                      💡 Probeer deze vragen:
                    </p>
                    {message.suggestions.slice(0, 3).map((suggestion, index) => (
                      <button
                        key={index}
                        onClick={() => handleSuggestionClick(suggestion)}
                        className="block w-full text-left text-sm bg-chatbot-neutral-100 hover:bg-chatbot-neutral-200 border border-chatbot-neutral-200 rounded-lg p-3 transition-colors duration-200"
                      >
                        {suggestion}
                      </button>
                    ))}
                  </div>
                )}
                
                <div className="mt-2 text-xs text-chatbot-neutral-400">
                  {message.timestamp.toLocaleTimeString('nl-NL', { 
                    hour: '2-digit', 
                    minute: '2-digit' 
                  })}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
        
        {isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="flex items-start space-x-3"
          >
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-chatbot-neutral-200 flex items-center justify-center">
              <Bot className="w-4 h-4 text-chatbot-neutral-600" />
            </div>
            <div className="flex-1">
              <div className="inline-block bg-white border border-chatbot-neutral-200 rounded-lg p-4 min-w-[280px]">
                {streamProgress ? (
                  <div className="space-y-3">
                    {/* Progress Header */}
                    <div className="flex items-center space-x-2">
                      <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-chatbot-primary"></div>
                      <span className="text-sm font-medium text-chatbot-neutral-700">
                        {streamProgress.message}
                      </span>
                    </div>

                    {/* Progress Bar */}
                    {streamProgress.step && (streamProgress.totalSteps || streamProgress.total_steps) && (() => {
                      const totalSteps = streamProgress.totalSteps || streamProgress.total_steps
                      const pct = Math.round((streamProgress.step / totalSteps) * 100)
                      return (
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs text-chatbot-neutral-500">
                            <span>Stap {streamProgress.step} van {totalSteps}</span>
                            <span>{pct}%</span>
                          </div>
                          <div className="h-2 bg-chatbot-neutral-100 rounded-full overflow-hidden">
                            <motion.div
                              className="h-full bg-gradient-to-r from-chatbot-primary to-emerald-500 rounded-full"
                              initial={{ width: 0 }}
                              animate={{ width: `${pct}%` }}
                              transition={{ duration: 0.3 }}
                            />
                          </div>
                        </div>
                      )
                    })()}

                    {/* Pipeline Steps */}
                    <div className="text-xs text-chatbot-neutral-500 space-y-1">
                      {['retrieveContext', 'generateInitialResponse', 'evaluateQuality', 'improveResponse', 'assembleFinalResponse'].map((step, index) => {
                        const stepNum = index + 1
                        const currentStep = streamProgress.step || 0
                        const isDone = stepNum < currentStep || (streamProgress.type === 'action_complete' && streamProgress.action === step)
                        const isCurrent = stepNum === currentStep && streamProgress.type !== 'complete'
                        const stepLabels = {
                          retrieveContext: 'Context ophalen',
                          generateInitialResponse: 'Antwoord genereren',
                          evaluateQuality: 'Kwaliteit beoordelen',
                          improveResponse: 'Verbeteren',
                          assembleFinalResponse: 'Afronden'
                        }
                        return (
                          <div key={step} className={`flex items-center space-x-2 ${isDone ? 'text-emerald-600' : isCurrent ? 'text-chatbot-primary font-medium' : 'text-chatbot-neutral-400'}`}>
                            <span className="w-4 text-center">
                              {isDone ? '✓' : isCurrent ? '→' : '○'}
                            </span>
                            <span>{stepLabels[step]}</span>
                          </div>
                        )
                      })}
                    </div>

                    {/* Quality Scores (if available) */}
                    {streamProgress.type === 'quality_score' && streamProgress.data && (
                      <div className="mt-2 pt-2 border-t border-chatbot-neutral-100">
                        <div className="text-xs text-emerald-600">
                          📊 {streamProgress.message}
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center space-x-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-chatbot-primary"></div>
                    <span className="text-sm text-chatbot-neutral-600">Verbinding maken...</span>
                  </div>
                )}
              </div>
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="bg-white border-t border-chatbot-neutral-200 p-4">
        <div className="flex items-end space-x-3">
          <div className="flex-1 min-w-0">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Stel je vraag over gemeente digitalisering..."
              className="w-full resize-none border border-chatbot-neutral-300 rounded-lg px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-chatbot-primary focus:border-transparent"
              rows={1}
              disabled={isLoading}
              style={{ maxHeight: '120px' }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px'
              }}
            />
          </div>
          
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim() || isLoading}
            className="flex-shrink-0 w-10 h-10 bg-chatbot-primary hover:bg-chatbot-primary-hover disabled:bg-chatbot-neutral-300 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center transition-colors"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        
        <div className="mt-2 flex justify-between items-center text-xs text-chatbot-neutral-500">
          <div className="flex items-center space-x-4">
            <span>🔍 RAG: 320 documenten</span>
            <span>📊 4 kwaliteitsdimensies</span>
            <span>📡 Live streaming</span>
          </div>
          <span>{inputValue.length}/2000</span>
        </div>
      </div>

      {/* Document Viewer Modal */}
      {viewingDocument && (
        <DocumentViewer
          documentId={viewingDocument}
          onClose={() => setViewingDocument(null)}
        />
      )}
    </div>
  )
}

export default EnhancedChatInterface