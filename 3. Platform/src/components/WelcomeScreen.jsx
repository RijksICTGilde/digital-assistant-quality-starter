import { motion } from 'framer-motion'
import { Bot, Shield, Users, ArrowRight, AlertCircle } from 'lucide-react'

const WelcomeScreen = ({ onContinue }) => {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-2xl mx-auto text-center">
        {/* Hero Section */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
        >
          <div className="mb-8">
            <motion.div
              className="inline-flex items-center justify-center w-20 h-20 bg-chatbot-primary rounded-2xl mb-6"
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            >
              <Bot className="w-10 h-10 text-white" />
            </motion.div>
            
            <h1 className="text-4xl md:text-5xl font-bold text-chatbot-neutral-800 mb-4">
              AI Kwaliteitsassistent
            </h1>
            
            <p className="text-xl text-chatbot-neutral-600 mb-8 leading-relaxed">
              Jouw digitale gids voor gemeente digitalisering en AI implementatie
            </p>
          </div>

          {/* AI Disclosure - Prominent and Clear */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="bg-chatbot-light border border-chatbot-neutral-200 rounded-xl p-4 mb-8 max-w-lg mx-auto"
          >
            <div className="flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 text-chatbot-secondary flex-shrink-0 mt-0.5" />
              <div className="text-left">
                <p className="text-sm font-medium text-chatbot-dark mb-1">
                  Je praat met kunstmatige intelligentie
                </p>
                <p className="text-xs text-chatbot-neutral-600">
                  Voor complexe juridische of technische zaken verbinden we je altijd door met een expert
                </p>
              </div>
            </div>
          </motion.div>

          {/* Features */}
          <div className="grid md:grid-cols-3 gap-6 mb-10">
            {[
              {
                icon: Shield,
                title: "Privacy & Compliance",
                description: "GDPR, AI Act en andere regelgeving compliant"
              },
              {
                icon: Users,
                title: "Voor Iedereen",
                description: "Ambtenaren, projectleiders en IT managers"  
              },
              {
                icon: Bot,
                title: "AI Powered",
                description: "Actuele kennis en contextbewuste antwoorden"
              }
            ].map((feature, index) => (
              <motion.div
                key={feature.title}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.6 + index * 0.1 }}
                className="card text-center"
              >
                <feature.icon className="w-8 h-8 text-chatbot-primary mx-auto mb-3" />
                <h3 className="font-semibold text-chatbot-neutral-800 mb-2">{feature.title}</h3>
                <p className="text-sm text-chatbot-neutral-600">{feature.description}</p>
              </motion.div>
            ))}
          </div>

          {/* CTA Button */}
          <motion.button
            onClick={onContinue}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.8 }}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            className="btn-primary text-lg px-8 py-4 inline-flex items-center space-x-2 group"
          >
            <span>Aan de slag</span>
            <ArrowRight className="w-5 h-5 group-hover:translate-x-1 transition-transform duration-200" />
          </motion.button>

          {/* Human Fallback Option */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 1 }}
            className="mt-6"
          >
            <p className="text-sm text-chatbot-neutral-500 mb-2">
              Liever direct met een mens praten?
            </p>
            <button className="text-chatbot-primary hover:underline text-sm font-medium">
              Contact opnemen met expert →
            </button>
          </motion.div>
        </motion.div>
      </div>
    </div>
  )
}

export default WelcomeScreen