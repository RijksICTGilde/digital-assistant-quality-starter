import { useState, useCallback } from 'react'
import { Routes, Route } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import ChatbotLanding from './components/ChatbotLanding'
import OrganizationSelector from './components/OrganizationSelector'
import RoleSelection from './components/RoleSelection'
import ContextGathering from './components/ContextGathering'
import InfoPages from './components/InfoPages'
import EnhancedChatInterface from './components/EnhancedChatInterface'
import LoadingScreen from './components/LoadingScreen'
import AdminDashboard from './pages/AdminDashboard'

const STEPS = {
  LANDING: 'landing',
  ORGANIZATION: 'organization',
  ROLE: 'role',
  CONTEXT: 'context',
  INFO: 'info',
  CHAT: 'chat'
}

function MainApp() {
  const [currentStep, setCurrentStep] = useState(STEPS.LANDING)
  const [userContext, setUserContext] = useState({
    selectedChoice: null,
    selectedOrganization: null,
    role: null,
    projectPhase: null,
    focusArea: null,
    specificNeeds: []
  })
  const [isLoading, setIsLoading] = useState(false)

  const handleStepTransition = useCallback(async (nextStep, data = {}) => {
    setIsLoading(true)

    // Update context with new data
    setUserContext(prev => ({
      ...prev,
      ...data
    }))

    // Simulate processing time for better UX
    await new Promise(resolve => setTimeout(resolve, 500))

    setCurrentStep(nextStep)
    setIsLoading(false)
  }, [])

  const handleChoiceSelect = (choice) => {
    handleStepTransition(STEPS.ORGANIZATION, { selectedChoice: choice })
  }

  const handleOrganizationSelect = (organization) => {
    handleStepTransition(STEPS.ROLE, { selectedOrganization: organization })
  }

  const handleRoleSelect = (roleData) => {
    handleStepTransition(STEPS.CONTEXT, { role: roleData.role })
  }

  const handleContextSubmit = (contextData) => {
    handleStepTransition(STEPS.INFO, {
      projectPhase: contextData.projectPhase,
      focusAreas: contextData.focusAreas,
      customContext: contextData.customContext,
      specificNeeds: contextData.specificNeeds
    })
  }

  const handleChoiceChange = (newChoice) => {
    setUserContext(prev => ({
      ...prev,
      selectedChoice: newChoice
    }))
  }

  const handleChatbotAccess = () => {
    // Role is already set by RoleSelection step
    handleStepTransition(STEPS.CHAT, {
      projectPhase: userContext.selectedChoice,
      focusArea: userContext.selectedOrganization?.id
    })
  }

  const handleRestart = () => {
    setUserContext({
      selectedChoice: null,
      selectedOrganization: null,
      role: null,
      projectPhase: null,
      focusArea: null,
      specificNeeds: []
    })
    setCurrentStep(STEPS.LANDING)
  }

  const renderCurrentStep = () => {
    switch (currentStep) {
      case STEPS.LANDING:
        return <ChatbotLanding onChoiceSelect={handleChoiceSelect} />

      case STEPS.ORGANIZATION:
        return (
          <OrganizationSelector
            selectedChoice={userContext.selectedChoice}
            onOrganizationSelect={handleOrganizationSelect}
            onBack={() => setCurrentStep(STEPS.LANDING)}
          />
        )

      case STEPS.ROLE:
        return (
          <RoleSelection
            onRoleSelect={handleRoleSelect}
            onBack={() => setCurrentStep(STEPS.ORGANIZATION)}
          />
        )

      case STEPS.CONTEXT:
        return (
          <ContextGathering
            selectedRole={userContext.role}
            onContextSubmit={handleContextSubmit}
            onBack={() => setCurrentStep(STEPS.ROLE)}
          />
        )

      case STEPS.INFO:
        return (
          <InfoPages
            selectedChoice={userContext.selectedChoice}
            selectedOrganization={userContext.selectedOrganization}
            onChatbotAccess={handleChatbotAccess}
            onBack={() => setCurrentStep(STEPS.CONTEXT)}
            onChoiceChange={handleChoiceChange}
          />
        )

      case STEPS.CHAT:
        return (
          <EnhancedChatInterface
            userContext={userContext}
            onRestart={handleRestart}
          />
        )

      default:
        return <ChatbotLanding onChoiceSelect={handleChoiceSelect} />
    }
  }

  const getStepProgress = () => {
    const steps = Object.values(STEPS)
    return steps.indexOf(currentStep)
  }

  return (
    <div className="min-h-screen bg-chatbot-light">
      <AnimatePresence mode="wait">
        {isLoading ? (
          <LoadingScreen key="loading" />
        ) : (
          <motion.div
            key={currentStep}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.3 }}
            className="min-h-screen"
          >
            {renderCurrentStep()}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Progress indicator - only show when not on landing or chat */}
      {currentStep !== STEPS.LANDING && currentStep !== STEPS.CHAT && (
        <div className="fixed bottom-0 left-0 right-0 bg-white/90 backdrop-blur-sm border-t border-chatbot-neutral-200 p-4">
          <div className="max-w-4xl mx-auto flex justify-between items-center">
            <div className="flex space-x-2">
              {Object.values(STEPS).slice(0, -1).map((step, index) => (
                <div
                  key={step}
                  className={`w-3 h-3 rounded-full transition-all duration-300 ${
                    getStepProgress() >= index
                      ? 'bg-chatbot-primary shadow-md'
                      : 'bg-chatbot-neutral-300'
                  }`}
                />
              ))}
            </div>

            <div className="text-sm text-chatbot-neutral-600">
              {userContext.selectedChoice && userContext.selectedOrganization && (
                <span className="flex items-center space-x-2">
                  <span>•</span>
                  <span className="capitalize">{userContext.selectedChoice}</span>
                  <span>•</span>
                  <span>{userContext.selectedOrganization.name}</span>
                </span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function App() {
  return (
    <Routes>
      <Route path="/admin" element={<AdminDashboard />} />
      <Route path="/*" element={<MainApp />} />
    </Routes>
  )
}

export default App
