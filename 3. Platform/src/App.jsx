import EnhancedChatInterface from './components/EnhancedChatInterface'

function App() {
  const userContext = {
    role: { id: 'hackathon-demo', name: 'Hackathon Demo' },
    projectPhase: 'demo',
    focusArea: 'quality'
  }

  return (
    <div className="min-h-screen bg-chatbot-light">
      <EnhancedChatInterface
        userContext={userContext}
        onRestart={() => window.location.reload()}
      />
    </div>
  )
}

export default App