"use client"

import { motion } from "framer-motion"

const technologies = [
  { name: "OpenAI", description: "GPT-5.4, GPT-4.1, Whisper" },
  { name: "Google AI", description: "Gemini 2.5 Flash" },
  { name: "WhatsApp", description: "Business API" },
  { name: "FastAPI", description: "Backend Python" },
  { name: "Supabase", description: "Banco de dados" },
  { name: "Railway", description: "Hospedagem" }
]

export function TechStack() {
  return (
    <section className="py-16 px-4 border-y border-border">
      <div className="max-w-7xl mx-auto">
        <motion.p
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center text-sm text-muted-foreground uppercase tracking-widest mb-8"
        >
          Powered by
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, y: 10 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="flex flex-wrap justify-center items-center gap-8 md:gap-12"
        >
          {technologies.map((tech, index) => (
            <motion.div
              key={tech.name}
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true }}
              transition={{ duration: 0.3, delay: index * 0.05 }}
              className="text-center group"
            >
              <p className="text-lg font-semibold text-foreground group-hover:text-primary transition-colors">
                {tech.name}
              </p>
              <p className="text-xs text-muted-foreground">{tech.description}</p>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
