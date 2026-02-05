import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  Send, 
  Bot, 
  User, 
  MessageCircle, 
  FileText, 
  Shield, 
  ExternalLink,
  Minimize2,
  Maximize2,
  Lightbulb,
  ArrowRight,
  X,
  Eye,
  Cookie
} from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { enhancedAPI } from '../services/enhanced_api'
import chatbotAvatar from '../assets/chatbot-avatar-new.png'

// Custom Kletsmajoor Icon Component
const KletsmajoorIcon = ({ className = "w-5 h-5" }) => (
  <div className={`${className} relative`}>
    <img 
      src={chatbotAvatar}
      alt="Kletsmajoor" 
      className="w-full h-full object-contain rounded-full"
    />
  </div>
)

// Context-specific example questions
const EXAMPLE_QUESTIONS = {
  waarom: {
    local: [
      "Hoe kan ik mijn gemeenteraad overtuigen van een chatbot?",
      "Wat zijn de kosten en baten voor een gemeente?",
      "Welke ROI kan ik verwachten?",
      "Hoe presenteer ik een business case?"
    ],
    provincial: [
      "Hoe rechtvaardigen we een chatbot voor provincie taken?",
      "Wat zijn de voordelen voor provinciale dienstverlening?",
      "Welke argumenten werken bij provinciale bestuurders?",
      "Hoe verhouden de kosten zich tot andere digitale initiatieven?"
    ],
    national: [
      "Hoe kan een chatbot rijksbrede doelen ondersteunen?",
      "Wat zijn de strategische voordelen voor het rijk?",
      "Hoe past dit in de digitale agenda van de overheid?",
      "Welke impact heeft dit op burgerservice?"
    ]
  },
  wat: {
    local: [
      "Welke chatbot technologie past bij onze gemeente?",
      "Intern of extern: wat is beter voor ons?",
      "Welke vendors zijn geschikt voor gemeenten?",
      "Hoe integreren we met onze huidige systemen?"
    ],
    provincial: [
      "Welke chatbot oplossingen werken op provinciaal niveau?",
      "Hoe kiezen we tussen verschillende platformen?",
      "Welke technische eisen heeft een provinciale chatbot?",
      "Welke integraties zijn belangrijk voor provincies?"
    ],
    national: [
      "Welke enterprise chatbot oplossingen zijn er?",
      "Hoe zorgen we voor schaalbaarheid op rijksniveau?",
      "Welke beveiligingseisen gelden voor rijksorganisaties?",
      "Hoe integreren we met rijksbrede IT-systemen?"
    ]
  },
  hoe: {
    local: [
      "Welke wet- en regelgeving geldt voor gemeentelijke chatbots?",
      "Hoe voeren we een DPIA uit voor onze chatbot?",
      "Welke privacy aspecten moeten we regelen?",
      "Hoe komen we van pilot naar productie?"
    ],
    provincial: [
      "Welke compliance eisen gelden voor provinciale AI?",
      "Hoe organiseren we governance voor onze chatbot?",
      "Welke stakeholders moeten we betrekken?",
      "Hoe zorgen we voor continue verbetering?"
    ],
    national: [
      "Welke rijksbrede richtlijnen gelden voor AI?",
      "Hoe implementeren we volgens overheidsstandaarden?",
      "Welke governance structuur hebben we nodig?",
      "Hoe zorgen we voor verantwoorde AI-inzet?"
    ]
  }
}

const ChatSidebar = ({ userContext, isMinimized, onToggleMinimize }) => {
  const [messages, setMessages] = useState([])
  const [inputValue, setInputValue] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isInitialized, setIsInitialized] = useState(false)
  const [showSuggestions, setShowSuggestions] = useState(true)
  const [selectedDocument, setSelectedDocument] = useState(null)
  const [documentContent, setDocumentContent] = useState('')
  const [loadingDocument, setLoadingDocument] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  // Get context-specific example questions
  const getExampleQuestions = () => {
    const choice = userContext.selectedChoice
    const orgLevel = userContext.selectedOrganization?.id
    return EXAMPLE_QUESTIONS[choice]?.[orgLevel] || []
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  useEffect(() => {
    if (!isInitialized) {
      // Initialize with welcome message
      const welcomeMessage = {
        id: Date.now(),
        type: 'ai',
        content: `**Hallo! 👋**

Ik ben Kletsmajoor, jouw slimme gesprekspartner met toegang tot 350+ overheidsdocumenten! 

**Wat kan ik voor je doen?**
- Vragen beantwoorden over ${userContext.selectedChoice}
- Specifieke informatie voor ${userContext.selectedOrganization?.name} organisaties
- Bronnen uit de kennisbank opzoeken
- Compliance en juridische vragen

Stel gerust je vraag - ik kletsmaai er graag over! 🍪`,
        timestamp: new Date(),
        enhanced: true
      }
      setMessages([welcomeMessage])
      setIsInitialized(true)
    }
  }, [isInitialized, userContext])

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

    try {
      const response = await enhancedAPI.sendStructuredMessage(message, userContext)
      
      // Clean up the content by removing StructuredAIResponse references
      let cleanContent = response.main_answer || response.answer || 'Ik kon geen antwoord genereren.'
      
      // Remove common structured response artifacts
      cleanContent = cleanContent
        .replace(/^StructuredAIResponse\s*[\(\{][^)}\n]*[\)\}]\s*/i, '')
        .replace(/```json[\s\S]*?```/g, '')
        .replace(/\*\*StructuredAIResponse\*\*/gi, '')
        .replace(/StructuredAIResponse/gi, '')
        .replace(/main_answer:|answer:/gi, '')
        .replace(/^":\s*/g, '') // Remove leading ": at start
        .replace(/:\s*$/gm, '') // Remove trailing colons at end of lines
        .replace(/([a-zA-Z])\s*:\s*\n/g, '$1.\n') // Replace "text: \n" with "text.\n"
        .replace(/([a-zA-Z])\s*:\s*([A-Z])/g, '$1. $2') // Replace "text: Text" with "text. Text"
        .replace(/\s*"\s*:\s*/g, ' ') // Remove ": patterns
        .replace(/([.!?])\s*":\s*/g, '$1 ') // Replace ": after punctuation with space
        .replace(/^[\s\n]*/, '') // Remove leading whitespace
        .trim()
      
      const aiMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: cleanContent,
        timestamp: new Date(),
        sources: response.knowledge_sources || response.sources || [],
        confidence: response.confidence_level || response.confidence,
        responseType: response.response_type,
        actionItems: response.action_items,
        complianceChecks: response.compliance_checks,
        followUpSuggestions: response.follow_up_suggestions,
        processingTime: response.processing_time_ms,
        qualityScores: response.quality_scores || null,
        qualityTrace: response.quality_trace || null,
        qualityImproved: response.quality_improved || false,
        qualityExplanation: response.quality_explanation || null,
        enhanced: true
      }

      setMessages(prev => [...prev, aiMessage])
    } catch (error) {
      console.error('Chat error:', error)
      const errorMessage = {
        id: Date.now() + 1,
        type: 'ai',
        content: `**Oeps, er ging iets mis! 😅**

Ik kon je vraag niet verwerken. Dit kan komen door:
- Tijdelijke serverissues
- Netwerkproblemen

**Probeer het opnieuw** of herformuleer je vraag anders.`,
        timestamp: new Date(),
        error: true
      }
      setMessages(prev => [...prev, errorMessage])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

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

  const getConfidenceColor = (confidence) => {
    if (typeof confidence === 'number') {
      return confidence >= 0.8 ? 'text-chatbot-primary' : confidence >= 0.5 ? 'text-chatbot-secondary' : 'text-chatbot-neutral-600'
    }
    return confidence === 'high' ? 'text-chatbot-primary' : confidence === 'medium' ? 'text-chatbot-secondary' : 'text-chatbot-neutral-600'
  }

  if (isMinimized) {
    return (
      <motion.div
        initial={{ scale: 0, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        exit={{ scale: 0, opacity: 0 }}
        className="fixed bottom-6 right-6 z-50"
      >
        <button
          onClick={onToggleMinimize}
          className="w-16 h-16 bg-chatbot-primary text-white rounded-full shadow-lg hover:shadow-xl hover:bg-opacity-90 transition-all duration-200 flex items-center justify-center group relative"
        >
          <KletsmajoorIcon className="w-8 h-8 group-hover:scale-110 transition-transform duration-200" />
          <div className="absolute -top-1 -right-1 w-5 h-5 bg-chatbot-secondary rounded-full flex items-center justify-center">
            <span className="text-xs text-white font-bold">🤖</span>
          </div>
        </button>
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ x: 400, opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: 400, opacity: 0 }}
      className="fixed right-0 top-0 h-full w-96 bg-white border-l border-chatbot-neutral-200 shadow-xl z-50 flex flex-col"
    >
      {/* Header */}
      <div className="bg-chatbot-primary text-white p-4 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <KletsmajoorIcon className="w-8 h-8" />
          <div>
            <h3 className="font-semibold">Kletsmajoor</h3>
            <p className="text-xs text-white/80">350+ documenten beschikbaar</p>
          </div>
        </div>
        <button
          onClick={onToggleMinimize}
          className="p-1 hover:bg-white/20 rounded transition-colors duration-200"
        >
          <Minimize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        <AnimatePresence>
          {messages.map((message) => (
            <motion.div
              key={message.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className={`flex ${message.type === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex items-start space-x-2 max-w-[85%] ${message.type === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
                {/* Avatar */}
                <div className={`flex-shrink-0 w-7 h-7 rounded-full flex items-center justify-center ${
                  message.type === 'user' 
                    ? 'bg-chatbot-secondary' 
                    : message.error 
                    ? 'bg-chatbot-neutral-400' 
                    : ''
                }`}>
                  {message.type === 'user' ? (
                    <User className="w-4 h-4 text-white" />
                  ) : (
                    <KletsmajoorIcon className="w-7 h-7" />
                  )}
                </div>

                {/* Message Content */}
                <div className={`rounded-lg px-3 py-2 ${
                  message.type === 'user'
                    ? 'bg-chatbot-secondary text-white rounded-br-sm'
                    : message.error
                    ? 'bg-chatbot-neutral-100 text-chatbot-dark rounded-bl-sm'
                    : 'bg-chatbot-light text-chatbot-dark rounded-bl-sm border border-chatbot-neutral-200'
                }`}>
                  <ReactMarkdown 
                    className="text-sm prose prose-sm max-w-none prose-headings:font-aharoni prose-headings:text-chatbot-dark prose-p:text-chatbot-dark prose-strong:text-chatbot-dark prose-ul:text-chatbot-dark prose-li:text-chatbot-dark"
                    components={{
                      h1: ({children}) => <h1 className="text-lg font-aharoni font-bold text-chatbot-dark mb-2">{children}</h1>,
                      h2: ({children}) => <h2 className="text-base font-aharoni font-semibold text-chatbot-dark mb-2">{children}</h2>,
                      h3: ({children}) => <h3 className="text-sm font-aharoni font-medium text-chatbot-dark mb-1">{children}</h3>,
                      p: ({children}) => <p className="text-sm text-chatbot-dark mb-2 leading-relaxed">{children}</p>,
                      ul: ({children}) => <ul className="text-sm text-chatbot-dark space-y-1 ml-4">{children}</ul>,
                      li: ({children}) => <li className="text-sm text-chatbot-dark">{children}</li>,
                      strong: ({children}) => <strong className="font-semibold text-chatbot-dark">{children}</strong>
                    }}
                  >
                    {message.content}
                  </ReactMarkdown>
                  
                  {/* Message metadata for AI responses */}
                  {message.type === 'ai' && !message.error && (
                    <div className="mt-2 pt-2 border-t border-chatbot-neutral-200">
                      {/* Quality Scores Panel */}
                      {message.qualityScores && (
                        <div className="mb-3 p-2 bg-emerald-50 border border-emerald-200 rounded-lg">
                          <div className="flex items-center justify-between mb-2">
                            <span className="text-xs font-semibold text-emerald-800 flex items-center">
                              <Shield className="w-3 h-3 mr-1" />
                              Kwaliteitscontrole
                              {message.qualityImproved && (
                                <span className="ml-1 px-1.5 py-0.5 bg-amber-100 text-amber-700 text-[10px] rounded-full">
                                  Verbeterd
                                </span>
                              )}
                            </span>
                          </div>
                          <div className="grid grid-cols-2 gap-2">
                            {Object.entries(message.qualityScores).map(([dim, score]) => {
                              const labels = {
                                relevance: 'Relevantie',
                                tone: 'Toon',
                                completeness: 'Volledigheid',
                                policy_compliance: 'Beleid'
                              }
                              const pct = Math.round(score * 100)
                              const color = pct >= 80 ? 'bg-emerald-500' : pct >= 60 ? 'bg-amber-500' : 'bg-red-500'
                              return (
                                <div key={dim} className="space-y-0.5">
                                  <div className="flex justify-between text-[10px]">
                                    <span className="text-emerald-700">{labels[dim] || dim}</span>
                                    <span className="font-medium text-emerald-800">{pct}%</span>
                                  </div>
                                  <div className="h-1 bg-emerald-100 rounded-full overflow-hidden">
                                    <div className={`h-full ${color} rounded-full`} style={{width: `${pct}%`}} />
                                  </div>
                                </div>
                              )
                            })}
                          </div>
                          {message.qualityExplanation && (
                            <p className="text-[10px] text-emerald-600 mt-2 italic">
                              {message.qualityExplanation}
                            </p>
                          )}
                        </div>
                      )}

                      <div className="flex items-center justify-between text-xs text-chatbot-neutral-500">
                        {message.responseType && (
                          <span>{formatResponseType(message.responseType)}</span>
                        )}
                        {message.confidence && (
                          <span className={getConfidenceColor(message.confidence)}>
                            {formatConfidence(message.confidence)}
                          </span>
                        )}
                      </div>
                      
                      {/* Sources */}
                      {message.sources && message.sources.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-chatbot-neutral-500 mb-2 font-medium">
                            📚 Bronnen ({message.sources.length}):
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {message.sources.slice(0, 5).map((source, index) => {
                              // Handle different possible source URL fields and document IDs
                              const sourceUrl = source.url || source.source_url || source.link || source.document_url
                              const documentId = source.document_id || source.id || source.doc_id
                              const title = source.title || source.document_title || source.filename || `Document ${index + 1}`
                              
                              const handleSourceClick = async (e) => {
                                e.preventDefault()
                                setLoadingDocument(true)
                                
                                try {
                                  console.log('Opening document:', { sourceUrl, documentId, source })
                                  
                                  // Set the selected document info
                                  setSelectedDocument({
                                    title,
                                    url: sourceUrl,
                                    id: documentId,
                                    source: source
                                  })
                                  
                                  // Try to fetch full document markdown content
                                  if (documentId) {
                                    try {
                                      console.log('Fetching full document for ID:', documentId)
                                      
                                      // Try different endpoints for full markdown content
                                      let response
                                      try {
                                        // First try dedicated full markdown endpoint
                                        response = await enhancedAPI.getFullMarkdownDocument(documentId)
                                        console.log('Full markdown response:', response)
                                      } catch (fullMarkdownError) {
                                        console.log('Full markdown failed, trying enhanced RAG endpoint')
                                        try {
                                          response = await enhancedAPI.getEnhancedRAGDocument(documentId)
                                          console.log('Enhanced RAG response:', response)
                                        } catch (enhancedError) {
                                          console.log('Enhanced RAG failed, trying regular document endpoint')
                                          response = await enhancedAPI.getDocument(documentId)
                                          console.log('Regular document response:', response)
                                        }
                                      }
                                      
                                      // Look for different content fields
                                      const fullContent = response.content || 
                                                         response.markdown_content || 
                                                         response.full_text || 
                                                         response.raw_content ||
                                                         response.text
                                      
                                      if (fullContent) {
                                        console.log('Found full content, length:', fullContent.length)
                                        setDocumentContent(fullContent)
                                      } else {
                                        console.log('No full content found, using fallback')
                                        setDocumentContent(`# ${title}\n\n**Let op: Volledige document inhoud niet beschikbaar**\n\n**Beschikbare snippet:**\n\n${source.snippet || source.content || 'Geen preview beschikbaar.'}\n\n---\n\n*Dit is een excerpt uit het volledige document. Voor de complete inhoud, probeer de originele URL.*`)
                                      }
                                    } catch (error) {
                                      console.error('Error fetching full document content:', error)
                                      setDocumentContent(`# ${title}\n\n**Fout bij laden van volledige document**\n\nFoutmelding: ${error.message}\n\n**Beschikbare snippet:**\n\n${source.snippet || source.content || 'Preview niet beschikbaar.'}\n\n---\n\n*Probeer de originele URL voor volledige toegang.*`)
                                    }
                                  } else {
                                    // No document ID available - use snippet only
                                    console.log('No document ID, using snippet/content only')
                                    setDocumentContent(`# ${title}\n\n**Beschikbare inhoud:**\n\n${source.snippet || source.content || 'Geen preview beschikbaar voor dit document.'}\n\n---\n\n*Geen document ID beschikbaar voor volledige inhoud. Dit is een excerpt.*`)
                                  }
                                } finally {
                                  setLoadingDocument(false)
                                }
                              }

                              return (
                                <button
                                  key={index}
                                  onClick={handleSourceClick}
                                  disabled={loadingDocument}
                                  className="inline-flex items-center px-2 py-1 bg-white border border-chatbot-neutral-200 rounded text-xs hover:bg-chatbot-light hover:border-chatbot-secondary transition-colors duration-200 cursor-pointer group max-w-full disabled:opacity-50"
                                >
                                  <Eye className="w-3 h-3 mr-1 text-chatbot-neutral-400 group-hover:text-chatbot-secondary flex-shrink-0" />
                                  <span className="truncate font-medium text-chatbot-dark group-hover:text-chatbot-primary">
                                    {title.length > 25 ? `${title.substring(0, 25)}...` : title}
                                  </span>
                                </button>
                              )
                            })}
                          </div>
                          {message.sources.length > 5 && (
                            <p className="text-xs text-chatbot-neutral-500 mt-1">
                              +{message.sources.length - 5} meer bronnen beschikbaar
                            </p>
                          )}
                        </div>
                      )}
                      
                      {/* Action Items */}
                      {message.actionItems && message.actionItems.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-chatbot-neutral-500 mb-1 font-medium">
                            ✅ Actiepunten:
                          </p>
                          <div className="space-y-1">
                            {message.actionItems.slice(0, 2).map((item, index) => (
                              <div key={index} className="bg-chatbot-primary/5 rounded p-2">
                                <p className="text-xs font-medium text-chatbot-dark">
                                  {item.title}
                                </p>
                                <p className="text-xs text-chatbot-neutral-600 mt-1">
                                  {item.description}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Follow-up Suggestions */}
                      {message.followUpSuggestions && message.followUpSuggestions.length > 0 && (
                        <div className="mt-3">
                          <p className="text-xs text-chatbot-neutral-500 mb-2 font-medium">
                            💡 Vervolgvragen:
                          </p>
                          <div className="space-y-1">
                            {message.followUpSuggestions.slice(0, 3).map((suggestion, index) => (
                              <button
                                key={index}
                                onClick={() => handleSendMessage(suggestion.question || suggestion)}
                                disabled={isLoading}
                                className="w-full text-left p-2 bg-white border border-chatbot-neutral-200 rounded text-xs hover:border-chatbot-secondary hover:bg-chatbot-light transition-all duration-200 text-chatbot-dark group disabled:opacity-50"
                              >
                                <div className="flex items-center justify-between">
                                  <span className="flex-1">
                                    {typeof suggestion === 'string' ? suggestion : suggestion.question}
                                  </span>
                                  <ArrowRight className="w-3 h-3 text-chatbot-neutral-400 group-hover:text-chatbot-secondary transition-colors duration-200 opacity-0 group-hover:opacity-100 ml-2 flex-shrink-0" />
                                </div>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* Example Questions - Show after welcome message */}
        {showSuggestions && messages.length === 1 && !isLoading && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="mb-4"
          >
            <div className="flex items-center space-x-2 mb-3">
              <Lightbulb className="w-4 h-4 text-chatbot-secondary" />
              <h4 className="text-sm font-medium text-chatbot-dark">Voorbeeldvragen voor jouw situatie</h4>
            </div>
            <div className="space-y-2">
              {getExampleQuestions().slice(0, 4).map((question, index) => (
                <motion.button
                  key={index}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: index * 0.1 }}
                  onClick={() => handleSendMessage(question)}
                  className="w-full text-left p-3 bg-white border border-chatbot-neutral-200 rounded-lg hover:border-chatbot-secondary hover:bg-chatbot-light transition-all duration-200 text-sm text-chatbot-dark group"
                  disabled={isLoading}
                >
                  <div className="flex items-center justify-between">
                    <span>{question}</span>
                    <ArrowRight className="w-3 h-3 text-chatbot-neutral-400 group-hover:text-chatbot-secondary transition-colors duration-200 opacity-0 group-hover:opacity-100" />
                  </div>
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}
        
        {isLoading && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="flex justify-start"
          >
            <div className="flex items-start space-x-2 max-w-[85%]">
              <KletsmajoorIcon className="w-7 h-7 flex-shrink-0" />
              <div className="bg-chatbot-light rounded-lg rounded-bl-sm px-3 py-2 border border-chatbot-neutral-200">
                <div className="flex items-center space-x-2">
                  <div className="animate-spin rounded-full h-3 w-3 border-b-2 border-chatbot-primary"></div>
                  <span className="text-xs text-chatbot-neutral-600">Aan het denken...</span>
                </div>
              </div>
            </div>
          </motion.div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-chatbot-neutral-200 p-4">
        <div className="flex items-end space-x-2">
          <div className="flex-1">
            <textarea
              ref={inputRef}
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Stel je vraag..."
              className="w-full resize-none border border-chatbot-neutral-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-chatbot-primary focus:border-transparent"
              rows={1}
              disabled={isLoading}
              style={{ maxHeight: '80px' }}
              onInput={(e) => {
                e.target.style.height = 'auto'
                e.target.style.height = Math.min(e.target.scrollHeight, 80) + 'px'
              }}
            />
          </div>
          
          <button
            onClick={() => handleSendMessage()}
            disabled={!inputValue.trim() || isLoading}
            className="flex-shrink-0 w-9 h-9 bg-chatbot-primary hover:bg-opacity-90 disabled:bg-chatbot-neutral-300 disabled:cursor-not-allowed text-white rounded-lg flex items-center justify-center transition-colors duration-200"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        
        <div className="mt-2 flex justify-between items-center text-xs text-chatbot-neutral-500">
          <span>🍪 Kletsmajoor • 350+ documenten</span>
          <span>{inputValue.length}/2000</span>
        </div>
      </div>

      {/* Document Viewer Modal */}
      <AnimatePresence>
        {selectedDocument && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black bg-opacity-50 z-50 flex items-center justify-center p-4"
            onClick={() => setSelectedDocument(null)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col"
              onClick={(e) => e.stopPropagation()}
            >
              {/* Header */}
              <div className="flex items-center justify-between p-4 border-b border-chatbot-neutral-200 bg-chatbot-light">
                <div className="flex-1">
                  <h3 className="font-semibold text-chatbot-dark text-lg">
                    {selectedDocument.title}
                  </h3>
                  <div className="flex items-center space-x-4 mt-1">
                    {selectedDocument.url && (
                      <a
                        href={selectedDocument.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-chatbot-secondary hover:text-chatbot-primary transition-colors duration-200 flex items-center"
                      >
                        <ExternalLink className="w-3 h-3 mr-1" />
                        Origineel document
                      </a>
                    )}
                    {selectedDocument.id && (
                      <span className="text-xs text-chatbot-neutral-500 font-mono">
                        ID: {selectedDocument.id}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-chatbot-neutral-600 mt-1">
                    📄 Volledige markdown document weergave
                  </p>
                </div>
                <button
                  onClick={() => setSelectedDocument(null)}
                  className="p-2 hover:bg-chatbot-neutral-200 rounded-lg transition-colors duration-200"
                >
                  <X className="w-5 h-5 text-chatbot-neutral-600" />
                </button>
              </div>

              {/* Content */}
              <div className="flex-1 overflow-y-auto p-6">
                {loadingDocument ? (
                  <div className="flex items-center justify-center py-12">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-chatbot-primary"></div>
                    <span className="ml-3 text-chatbot-neutral-600">Document laden...</span>
                  </div>
                ) : (
                  <ReactMarkdown 
                    className="prose prose-sm max-w-none prose-headings:font-aharoni prose-headings:text-chatbot-dark prose-p:text-chatbot-dark prose-strong:text-chatbot-dark prose-ul:text-chatbot-dark prose-li:text-chatbot-dark prose-a:text-chatbot-secondary hover:prose-a:text-chatbot-primary"
                    components={{
                      h1: ({children}) => <h1 className="text-2xl font-aharoni font-bold text-chatbot-dark mb-4">{children}</h1>,
                      h2: ({children}) => <h2 className="text-xl font-aharoni font-semibold text-chatbot-dark mb-3 mt-6">{children}</h2>,
                      h3: ({children}) => <h3 className="text-lg font-aharoni font-medium text-chatbot-dark mb-2 mt-4">{children}</h3>,
                      p: ({children}) => <p className="text-chatbot-dark mb-3 leading-relaxed">{children}</p>,
                      ul: ({children}) => <ul className="text-chatbot-dark space-y-1 ml-6 mb-3">{children}</ul>,
                      ol: ({children}) => <ol className="text-chatbot-dark space-y-1 ml-6 mb-3">{children}</ol>,
                      li: ({children}) => <li className="text-chatbot-dark">{children}</li>,
                      strong: ({children}) => <strong className="font-semibold text-chatbot-dark">{children}</strong>,
                      a: ({href, children}) => (
                        <a 
                          href={href} 
                          target="_blank" 
                          rel="noopener noreferrer"
                          className="text-chatbot-secondary hover:text-chatbot-primary underline"
                        >
                          {children}
                        </a>
                      )
                    }}
                  >
                    {documentContent}
                  </ReactMarkdown>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

export default ChatSidebar