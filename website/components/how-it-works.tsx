"use client"

import { motion } from "framer-motion"
import { MessageCircle, Zap, CheckCircle } from "lucide-react"

const steps = [
  {
    icon: MessageCircle,
    title: "1. Envie uma mensagem",
    description: "Mande texto, áudio, imagem, documento ou link para o WhatsApp da Aisha."
  },
  {
    icon: Zap,
    title: "2. IA processa",
    description: "A Aisha escolhe automaticamente o melhor modelo de IA para sua solicitação."
  },
  {
    icon: CheckCircle,
    title: "3. Receba a resposta",
    description: "Em segundos, você recebe a resposta inteligente diretamente no WhatsApp."
  }
]

export function HowItWorks() {
  return (
    <section className="py-24 px-4">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground mb-4 text-balance">
            Simples de usar
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            Não precisa instalar nada. Basta mandar mensagem pelo WhatsApp.
          </p>
        </motion.div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {steps.map((step, index) => (
            <motion.div
              key={step.title}
              initial={{ opacity: 0, y: 20 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="relative text-center"
            >
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="hidden md:block absolute top-12 left-[60%] w-[80%] h-0.5 bg-gradient-to-r from-primary/50 to-primary/10" />
              )}
              
              <div className="relative z-10 inline-flex items-center justify-center w-24 h-24 rounded-2xl bg-primary/10 text-primary mb-6 border border-primary/20">
                <step.icon className="h-10 w-10" />
              </div>
              
              <h3 className="text-xl font-semibold text-foreground mb-2">{step.title}</h3>
              <p className="text-muted-foreground">{step.description}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
