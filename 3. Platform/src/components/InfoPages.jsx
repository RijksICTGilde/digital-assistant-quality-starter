import React, { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  ArrowLeft, 
  MessageCircle, 
  ArrowRight, 
  ChevronDown, 
  ChevronRight,
  CheckCircle,
  AlertCircle,
  Info,
  Lightbulb,
  Target,
  Shield,
  Users,
  Zap,
  BookOpen,
  FileText,
  Settings,
  HelpCircle,
  Wrench,
  PlayCircle
} from 'lucide-react'
import ChatSidebar from './ChatSidebar'

const InfoPages = ({ selectedChoice, selectedOrganization, onChatbotAccess, onBack, onChoiceChange }) => {
  const [expandedSections, setExpandedSections] = useState(new Set(['introduction']))
  const [completedSections, setCompletedSections] = useState(new Set())
  const [isChatMinimized, setIsChatMinimized] = useState(false)

  // Reset sections when choice changes
  React.useEffect(() => {
    setExpandedSections(new Set(['introduction']))
    setCompletedSections(new Set())
  }, [selectedChoice])

  const toggleSection = (sectionId) => {
    const newExpanded = new Set(expandedSections)
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId)
    } else {
      newExpanded.add(sectionId)
      // Mark as completed when expanded
      setCompletedSections(prev => new Set([...prev, sectionId]))
    }
    setExpandedSections(newExpanded)
  }

  const getContentForChoice = (choice, orgLevel) => {
    const baseContent = {
      waarom: {
        title: 'Waarom een chatbot implementeren?',
        subtitle: 'Overtuig je organisatie van de toegevoegde waarde',
        sections: [
          {
            id: 'introduction',
            title: 'Waarom deze gids?',
            icon: Info,
            content: (
              <div className="space-y-4">
                <p className="text-lg">
                  Een chatbot implementeren is meer dan een technische beslissing. Het raakt de kernprocessen 
                  van je organisatie en de ervaring van burgers en medewerkers.
                </p>
                <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-2">Deze gids helpt je om:</h4>
                  <ul className="space-y-2">
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-chatbot-primary" />
                      <span>Concrete business case te ontwikkelen</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-chatbot-primary" />
                      <span>Stakeholders te overtuigen met feiten</span>
                    </li>
                    <li className="flex items-center space-x-2">
                      <CheckCircle className="w-4 h-4 text-chatbot-primary" />
                      <span>Realistische verwachtingen te stellen</span>
                    </li>
                  </ul>
                </div>
              </div>
            )
          },
          {
            id: 'benefits',
            title: 'Voordelen voor je organisatie',
            icon: Target,
            content: (
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2 flex items-center">
                      <Users className="w-5 h-5 mr-2 text-chatbot-secondary" />
                      Voor Burgers
                    </h4>
                    <ul className="space-y-2 text-chatbot-neutral-600">
                      <li>• 24/7 beschikbaarheid</li>
                      <li>• Snellere eerste respons</li>
                      <li>• Minder wachttijden</li>
                      <li>• Consistente informatie</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2 flex items-center">
                      <Settings className="w-5 h-5 mr-2 text-chatbot-primary" />
                      Voor de Organisatie
                    </h4>
                    <ul className="space-y-2 text-chatbot-neutral-600">
                      <li>• Lagere operationele kosten</li>
                      <li>• Meer tijd voor complexe vragen</li>
                      <li>• Betere data en inzichten</li>
                      <li>• Schaalbare ondersteuning</li>
                    </ul>
                  </div>
                </div>
                
                {orgLevel === 'local' && (
                  <div className="bg-chatbot-secondary/10 rounded-lg p-4 border border-chatbot-secondary/20">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Specifiek voor gemeenten:</h4>
                    <p className="text-chatbot-neutral-600">
                      Gemeenten zien gemiddeld 40% reductie in simpele vragen na chatbot implementatie. 
                      Dit betekent meer tijd voor maatwerk en complexe dienstverlening.
                    </p>
                  </div>
                )}
              </div>
            )
          },
          {
            id: 'business-case',
            title: 'Business Case ontwikkelen',
            icon: FileText,
            content: (
              <div className="space-y-6">
                <div className="bg-chatbot-primary/10 rounded-lg p-4 border border-chatbot-primary/20">
                  <h4 className="font-semibold text-chatbot-dark mb-2 flex items-center">
                    <AlertCircle className="w-5 h-5 mr-2 text-chatbot-primary" />
                    Belangrijk om te meten
                  </h4>
                  <p className="text-chatbot-neutral-600">
                    Zonder concrete cijfers is het moeilijk om draagvlak te creëren. 
                    Meet je huidige situatie eerst.
                  </p>
                </div>
                
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200 shadow-sm">
                    <h5 className="font-semibold text-chatbot-dark mb-2">Meet nu:</h5>
                    <ul className="text-sm space-y-1 text-chatbot-neutral-600">
                      <li>• Aantal contactmomenten/maand</li>
                      <li>• Gemiddelde afhandeltijd</li>
                      <li>• Kosten per contact</li>
                      <li>• Klanttevredenheid</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200 shadow-sm">
                    <h5 className="font-semibold text-chatbot-dark mb-2">Bereken potentieel:</h5>
                    <ul className="text-sm space-y-1 text-chatbot-neutral-600">
                      <li>• 30-50% reductie eenvoudige vragen</li>
                      <li>• 70% snellere eerste respons</li>
                      <li>• 20-30% kostenreductie</li>
                      <li>• Hoghere tevredenheid</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200 shadow-sm">
                    <h5 className="font-semibold text-chatbot-dark mb-2">ROI periode:</h5>
                    <ul className="text-sm space-y-1 text-chatbot-neutral-600">
                      <li>• Kleine gemeente: 8-12 maanden</li>
                      <li>• Middelgrote gemeente: 6-9 maanden</li>
                      <li>• Grote gemeente: 4-6 maanden</li>
                    </ul>
                  </div>
                </div>
              </div>
            )
          },
          {
            id: 'risks',
            title: 'Risico\'s en uitdagingen',
            icon: Shield,
            content: (
              <div className="space-y-4">
                <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-2">Veelvoorkomende valkuilen:</h4>
                  <ul className="space-y-2 text-chatbot-neutral-600">
                    <li>• Te hoge verwachtingen over AI-mogelijkheden</li>
                    <li>• Onvoldoende training data</li>
                    <li>• Gebrek aan organisatiewide commitment</li>
                    <li>• Onderschatting van onderhoudskosten</li>
                  </ul>
                </div>
                
                <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-2">Zo voorkom je problemen:</h4>
                  <ul className="space-y-2 text-chatbot-neutral-600">
                    <li>• Start met een duidelijk afgebakende pilot</li>
                    <li>• Betrek eindgebruikers vanaf dag 1</li>
                    <li>• Plan voldoende tijd voor training en testing</li>
                    <li>• Zorg voor technische en juridische expertise</li>
                  </ul>
                </div>
              </div>
            )
          }
        ]
      },
      wat: {
        title: 'Wat voor chatbot past bij jou?',
        subtitle: 'Verken de technische mogelijkheden en keuzes',
        sections: [
          {
            id: 'introduction',
            title: 'Soorten chatbots',
            icon: Info,
            content: (
              <div className="space-y-6">
                <p className="text-lg">
                  Niet alle chatbots zijn hetzelfde. De keuze hangt af van je doelen, budget en technische mogelijkheden.
                </p>
                
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Rule-based</h4>
                    <p className="text-chatbot-neutral-600 text-sm mb-2">
                      Volgt voorgedefinieerde scripts en beslisbomen
                    </p>
                    <ul className="text-xs text-chatbot-neutral-600 space-y-1">
                      <li>✓ Voorspelbaar en betrouwbaar</li>
                      <li>✓ Lagere kosten</li>
                      <li>✗ Beperkte flexibiliteit</li>
                    </ul>
                  </div>
                  
                  <div className="bg-white rounded-lg p-4 border border-chatbot-primary/20">
                    <h4 className="font-semibold text-chatbot-dark mb-2">AI-powered</h4>
                    <p className="text-chatbot-neutral-600 text-sm mb-2">
                      Gebruikt natuurlijke taalverwerking en machine learning
                    </p>
                    <ul className="text-xs text-chatbot-neutral-600 space-y-1">
                      <li>✓ Flexibel en leert bij</li>
                      <li>✓ Natuurlijke conversaties</li>
                      <li>✗ Complexer en duurder</li>
                    </ul>
                  </div>
                  
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Hybrid</h4>
                    <p className="text-chatbot-neutral-600 text-sm mb-2">
                      Combineert regels met AI voor optimale balans
                    </p>
                    <ul className="text-xs text-chatbot-neutral-600 space-y-1">
                      <li>✓ Beste van beide werelden</li>
                      <li>✓ Stapsgewijs uitbreidbaar</li>
                      <li>✓ Meest praktisch</li>
                    </ul>
                  </div>
                </div>
              </div>
            )
          },
          {
            id: 'internal-external',
            title: 'Intern vs. Extern',
            icon: Users,
            content: (
              <div className="space-y-6">
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-chatbot-light rounded-lg p-6 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-4 flex items-center">
                      <Users className="w-5 h-5 mr-2" />
                      Interne Chatbot
                    </h4>
                    <div className="space-y-4">
                      <div>
                        <h5 className="font-medium text-chatbot-dark mb-2">Voor wie:</h5>
                        <p className="text-chatbot-neutral-600 text-sm">Medewerkers, HR, IT-support, beleidsteams</p>
                      </div>
                      <div>
                        <h5 className="font-medium text-chatbot-dark mb-2">Voordelen:</h5>
                        <ul className="text-chatbot-neutral-600 text-sm space-y-1">
                          <li>• Snellere onboarding nieuwe medewerkers</li>
                          <li>• Minder IT-support tickets</li>
                          <li>• Betere toegang tot beleidsinformatie</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-white rounded-lg p-6 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-4 flex items-center">
                      <MessageCircle className="w-5 h-5 mr-2" />
                      Externe Chatbot
                    </h4>
                    <div className="space-y-4">
                      <div>
                        <h5 className="font-medium text-chatbot-dark mb-2">Voor wie:</h5>
                        <p className="text-chatbot-neutral-600 text-sm">Burgers, ondernemers, bezoekers</p>
                      </div>
                      <div>
                        <h5 className="font-medium text-chatbot-dark mb-2">Voordelen:</h5>
                        <ul className="text-chatbot-neutral-600 text-sm space-y-1">
                          <li>• 24/7 eerste lijns ondersteuning</li>
                          <li>• Minder telefoontjes naar balies</li>
                          <li>• Betere digitale dienstverlening</li>
                        </ul>
                      </div>
                    </div>
                  </div>
                </div>
                
                {orgLevel === 'local' && (
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Tip voor gemeenten:</h4>
                    <p className="text-chatbot-neutral-600">
                      Start vaak met een externe chatbot voor burgerzaken. 
                      De impact is direct zichtbaar en de business case is makkelijker te maken.
                    </p>
                  </div>
                )}
              </div>
            )
          },
          {
            id: 'technologies',
            title: 'Technische opties',
            icon: Settings,
            content: (
              <div className="space-y-6">
                <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-2">Belangrijkste keuzes:</h4>
                  <div className="grid md:grid-cols-2 gap-4 mt-4">
                    <div>
                      <h5 className="font-medium text-chatbot-dark mb-2">Platform keuze:</h5>
                      <ul className="text-sm text-chatbot-neutral-600 space-y-1">
                        <li>• Cloud-based (Microsoft, Google, AWS)</li>
                        <li>• On-premise oplossingen</li>
                        <li>• Open source alternatieven</li>
                      </ul>
                    </div>
                    <div>
                      <h5 className="font-medium text-chatbot-dark mb-2">Integraties:</h5>
                      <ul className="text-sm text-chatbot-neutral-600 space-y-1">
                        <li>• Bestaande CRM/ERP systemen</li>
                        <li>• Website en apps</li>
                        <li>• Telefonie en email</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200 shadow-sm">
                    <h5 className="font-semibold text-chatbot-dark mb-2">SaaS Oplossingen</h5>
                    <ul className="text-sm space-y-1 text-chatbot-neutral-600">
                      <li>✓ Snelle implementatie</li>
                      <li>✓ Lage startkosten</li>
                      <li>✓ Automatische updates</li>
                      <li>✗ Minder maatwerk</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200 shadow-sm">
                    <h5 className="font-semibold text-chatbot-dark mb-2">Custom Development</h5>
                    <ul className="text-sm space-y-1 text-chatbot-neutral-600">
                      <li>✓ Volledig maatwerk</li>
                      <li>✓ Eigen data en controle</li>
                      <li>✗ Hogere kosten</li>
                      <li>✗ Langere ontwikkeltijd</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200 shadow-sm">
                    <h5 className="font-semibold text-chatbot-dark mb-2">Open Source</h5>
                    <ul className="text-sm space-y-1 text-chatbot-neutral-600">
                      <li>✓ Geen licentiekosten</li>
                      <li>✓ Volledige controle</li>
                      <li>✗ Meer technische expertise nodig</li>
                      <li>✗ Support op eigen risiko</li>
                    </ul>
                  </div>
                </div>
              </div>
            )
          }
        ]
      },
      hoe: {
        title: 'Hoe implementeer je een chatbot?',
        subtitle: 'Van pilot naar productie: praktische stappen',
        sections: [
          {
            id: 'introduction',
            title: 'Stappenplan implementatie',
            icon: Info,
            content: (
              <div className="space-y-6">
                <p className="text-lg">
                  Een succesvolle chatbot implementatie vraagt om een doordachte aanpak. 
                  Hier vind je een praktisch stappenplan.
                </p>
                
                <div className="grid md:grid-cols-4 gap-4">
                  {[
                    { phase: 'Fase 1', title: 'Verkenning', duration: '2-4 weken', color: 'blue' },
                    { phase: 'Fase 2', title: 'Pilot', duration: '8-12 weken', color: 'purple' },
                    { phase: 'Fase 3', title: 'Uitrol', duration: '12-16 weken', color: 'green' },
                    { phase: 'Fase 4', title: 'Optimalisatie', duration: 'Doorlopend', color: 'orange' }
                  ].map((phase, index) => (
                    <div key={index} className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                      <div className="text-chatbot-dark font-semibold text-sm mb-1">{phase.phase}</div>
                      <div className="text-chatbot-dark font-medium mb-1">{phase.title}</div>
                      <div className="text-chatbot-neutral-600 text-xs">{phase.duration}</div>
                    </div>
                  ))}
                </div>
              </div>
            )
          },
          {
            id: 'pilot',
            title: 'Van pilot naar productie',
            icon: Zap,
            content: (
              <div className="space-y-6">
                <div className="bg-chatbot-light rounded-lg p-6 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-4">Succesfactoren voor pilots:</h4>
                  <div className="grid md:grid-cols-2 gap-6">
                    <div>
                      <h5 className="font-medium text-chatbot-dark mb-2 flex items-center">
                        <Target className="w-4 h-4 mr-2" />
                        Duidelijke scope
                      </h5>
                      <ul className="text-sm text-chatbot-neutral-600 space-y-1">
                        <li>• Begin met 1 specifiek onderwerp</li>
                        <li>• Maximaal 20-30 veelgestelde vragen</li>
                        <li>• Duidelijke success criteria</li>
                        <li>• Afgebakende gebruikersgroep</li>
                      </ul>
                    </div>
                    <div>
                      <h5 className="font-medium text-chatbot-dark mb-2 flex items-center">
                        <Users className="w-4 h-4 mr-2" />
                        Gebruikersfeedback
                      </h5>
                      <ul className="text-sm text-chatbot-neutral-600 space-y-1">
                        <li>• Wekelijkse feedback sessies</li>
                        <li>• Analytics en gebruik data</li>
                        <li>• A/B testing van antwoorden</li>
                        <li>• Handoff naar menselijke agent</li>
                      </ul>
                    </div>
                  </div>
                </div>
                
                <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-2 flex items-center">
                    <AlertCircle className="w-5 h-5 mr-2" />
                    Pilot valkuilen
                  </h4>
                  <ul className="text-chatbot-neutral-600 space-y-1">
                    <li>• Te brede scope vanaf het begin</li>
                    <li>• Onvoldoende training data</li>
                    <li>• Geen duidelijke exit criteria</li>
                    <li>• Te weinig stakeholder betrokkenheid</li>
                  </ul>
                </div>
              </div>
            )
          },
          {
            id: 'compliance',
            title: 'Wet- en regelgeving',
            icon: Shield,
            content: (
              <div className="space-y-6">
                <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-2 flex items-center">
                    <Shield className="w-5 h-5 mr-2" />
                    Verplichte compliance
                  </h4>
                  <ul className="text-chatbot-neutral-600 space-y-2">
                    <li>• <strong>AVG/GDPR:</strong> Persoonsgegevens verwerking</li>
                    <li>• <strong>AI Act (EU):</strong> Transparantie en risicobeoordeling</li>
                    <li>• <strong>WOO:</strong> Openbaarheid van algoritmes</li>
                    <li>• <strong>Toegankelijkheid:</strong> WCAG richtlijnen</li>
                  </ul>
                </div>
                
                <div className="grid md:grid-cols-2 gap-6">
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Privacy & Data</h4>
                    <ul className="text-chatbot-neutral-600 text-sm space-y-1">
                      <li>• DPIA uitvoeren als nodig</li>
                      <li>• Data minimalisatie principe</li>
                      <li>• Bewaaretermijnen vastleggen</li>
                      <li>• Gebruiker rechten faciliteren</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Transparantie</h4>
                    <ul className="text-chatbot-neutral-600 text-sm space-y-1">
                      <li>• Duidelijk dat het AI is</li>
                      <li>• Algoritme in register</li>
                      <li>• Uitlegbare beslissingen</li>
                      <li>• Mogelijkheid tot bezwaar</li>
                    </ul>
                  </div>
                </div>
                
                {orgLevel === 'local' && (
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Specifiek voor gemeenten:</h4>
                    <p className="text-chatbot-neutral-600 text-sm">
                      Gemeenten moeten algoritmes publiceren in het Algoritmeregister. 
                      Ook bij chatbots die besluiten nemen of adviezen geven.
                    </p>
                  </div>
                )}
              </div>
            )
          },
          {
            id: 'stakeholders',
            title: 'Wie betrekken?',
            icon: Users,
            content: (
              <div className="space-y-6">
                <div className="grid md:grid-cols-3 gap-4">
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Business kant</h4>
                    <ul className="text-chatbot-neutral-600 text-sm space-y-1">
                      <li>• Afdelingshoofd</li>
                      <li>• Projectleider</li>
                      <li>• Communicatie</li>
                      <li>• Klantenservice</li>
                    </ul>
                  </div>
                  <div className="bg-white rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Technische kant</h4>
                    <ul className="text-chatbot-neutral-600 text-sm space-y-1">
                      <li>• IT Manager</li>
                      <li>• Architect</li>
                      <li>• Developer</li>
                      <li>• Security officer</li>
                    </ul>
                  </div>
                  <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                    <h4 className="font-semibold text-chatbot-dark mb-2">Governance</h4>
                    <ul className="text-chatbot-neutral-600 text-sm space-y-1">
                      <li>• Privacy officer</li>
                      <li>• Juridisch adviseur</li>
                      <li>• Compliance officer</li>
                      <li>• Ethiek commissie</li>
                    </ul>
                  </div>
                </div>
                
                <div className="bg-chatbot-light rounded-lg p-4 border border-chatbot-neutral-200">
                  <h4 className="font-semibold text-chatbot-dark mb-2">Tip: Begin klein, denk groot</h4>
                  <p className="text-chatbot-neutral-600">
                    Start met een kernteam van 3-4 mensen voor de pilot. 
                    Breid uit naarmate het project groeit en complexer wordt.
                  </p>
                </div>
              </div>
            )
          }
        ]
      }
    }

    return baseContent[choice] || baseContent.waarom
  }

  const content = getContentForChoice(selectedChoice, selectedOrganization?.id)

  const progressPercentage = (completedSections.size / content.sections.length) * 100

  return (
    <div className="min-h-screen bg-chatbot-light">
      <div className={`transition-all duration-300 ${!isChatMinimized ? 'pr-96' : ''}`}>
        <div className="max-w-7xl ml-8 px-6 py-12">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-12"
        >
          <div className="bg-chatbot-light rounded-2xl p-6 mb-8 border border-chatbot-neutral-200">
            <div className="flex items-center justify-center space-x-4 mb-4">
              <div className="w-12 h-12 bg-chatbot-primary rounded-xl flex items-center justify-center">
                <Lightbulb className="w-6 h-6 text-white" />
              </div>
              <div className="text-left">
                <p className="text-chatbot-neutral-600 text-sm">
                  {selectedOrganization?.name} niveau • Interactieve gids
                </p>
                <h1 className="text-3xl md:text-4xl font-bold text-chatbot-dark">
                  {content.title}
                </h1>
              </div>
            </div>
            <p className="text-lg text-chatbot-neutral-600">
              {content.subtitle}
            </p>
          </div>

          {/* Progress Bar */}
          <div className="bg-white rounded-full h-3 mb-6 shadow-inner border border-chatbot-neutral-200">
            <motion.div
              className="bg-chatbot-primary h-3 rounded-full"
              initial={{ width: 0 }}
              animate={{ width: `${progressPercentage}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <p className="text-sm text-chatbot-neutral-600">
            {completedSections.size} van {content.sections.length} secties voltooid
          </p>
        </motion.div>

        {/* Navigation Buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="flex justify-center mb-8"
        >
          <div className="flex bg-white rounded-xl p-2 shadow-sm border border-chatbot-neutral-200">
            {[
              { id: 'waarom', label: 'Waarom', icon: HelpCircle },
              { id: 'wat', label: 'Wat', icon: Wrench },
              { id: 'hoe', label: 'Hoe', icon: PlayCircle }
            ].map((choice) => (
              <button
                key={choice.id}
                onClick={() => onChoiceChange && onChoiceChange(choice.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-all duration-200 ${
                  selectedChoice === choice.id
                    ? 'bg-chatbot-primary text-white shadow-sm'
                    : 'text-chatbot-neutral-600 hover:bg-chatbot-light hover:text-chatbot-dark'
                }`}
              >
                <choice.icon className="w-4 h-4" />
                <span className="font-medium">{choice.label}</span>
              </button>
            ))}
          </div>
        </motion.div>

        {/* Content Sections */}
        <div className="space-y-6 mb-12">
          {content.sections.map((section, index) => (
            <motion.div
              key={section.id}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="bg-white rounded-xl shadow-sm border border-chatbot-neutral-200 overflow-hidden"
            >
              <button
                onClick={() => toggleSection(section.id)}
                className="w-full p-6 flex items-center justify-between text-left hover:bg-chatbot-neutral-50 transition-colors duration-200"
              >
                <div className="flex items-center space-x-4">
                  <div className={`p-2 rounded-lg ${completedSections.has(section.id) ? 'bg-chatbot-secondary/20' : 'bg-chatbot-primary/10'}`}>
                    {completedSections.has(section.id) ? (
                      <CheckCircle className="w-5 h-5 text-chatbot-secondary" />
                    ) : (
                      <section.icon className="w-5 h-5 text-chatbot-primary" />
                    )}
                  </div>
                  <h3 className="text-xl font-semibold text-chatbot-dark">
                    {section.title}
                  </h3>
                </div>
                {expandedSections.has(section.id) ? (
                  <ChevronDown className="w-5 h-5 text-chatbot-neutral-400" />
                ) : (
                  <ChevronRight className="w-5 h-5 text-chatbot-neutral-400" />
                )}
              </button>
              
              <AnimatePresence>
                {expandedSections.has(section.id) && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.3 }}
                    className="border-t border-chatbot-neutral-200"
                  >
                    <div className="p-6">
                      {section.content}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          ))}
        </div>


        {/* Navigation */}
        <div className="flex justify-between items-center mt-8">
          <button
            onClick={onBack}
            className="btn-outline flex items-center space-x-2"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Terug</span>
          </button>

          <div className="text-sm text-chatbot-neutral-500">
            Stap 3 van 3 • {Math.round(progressPercentage)}% voltooid
          </div>

          <button
            onClick={onChatbotAccess}
            className="btn-primary flex items-center space-x-2"
          >
            <MessageCircle className="w-4 h-4" />
            <span>Start Chatbot</span>
            <ArrowRight className="w-4 h-4" />
          </button>
        </div>
        </div>
      </div>

      {/* Chat Sidebar */}
      <ChatSidebar
        userContext={{ selectedChoice, selectedOrganization }}
        isMinimized={isChatMinimized}
        onToggleMinimize={() => setIsChatMinimized(!isChatMinimized)}
      />
    </div>
  )
}

export default InfoPages