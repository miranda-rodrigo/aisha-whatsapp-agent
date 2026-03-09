"use client"

import { Button } from "@/components/ui/button"
import { MessageCircle, ArrowRight, Sparkles } from "lucide-react"
import { motion } from "framer-motion"

export function Hero() {
  return (
    <section className="relative min-h-screen flex items-center justify-center overflow-hidden px-4 py-20">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-background via-background to-primary/10" />
      
      {/* Animated grid */}
      <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:radial-gradient(ellipse_at_center,black_20%,transparent_70%)]" />
      
      <div className="relative z-10 max-w-5xl mx-auto text-center">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-full border border-border bg-secondary/50 text-sm text-muted-foreground"
        >
          <Sparkles className="h-4 w-4 text-primary" />
          <span>Powered by GPT-5.4 & Gemini 2.5 Flash</span>
        </motion.div>
        
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="text-4xl sm:text-5xl md:text-7xl font-bold tracking-tight text-foreground mb-6 text-balance"
        >
          Sua assistente pessoal{" "}
          <span className="text-primary">inteligente</span>{" "}
          no WhatsApp
        </motion.h1>
        
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2 }}
          className="text-lg sm:text-xl text-muted-foreground max-w-3xl mx-auto mb-10 text-pretty"
        >
          Converse, transcreva áudios, gere imagens, crie lembretes, analise documentos e vídeos do YouTube — tudo pelo WhatsApp com inteligência artificial de última geração.
        </motion.p>
        
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3 }}
          className="flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Button size="lg" className="gap-2 text-base px-6 py-6" asChild>
            <a href="https://wa.me/5585941322222" target="_blank" rel="noopener noreferrer">
              <MessageCircle className="h-5 w-5" />
              Conversar com Aisha
            </a>
          </Button>
          <Button variant="outline" size="lg" className="gap-2 text-base px-6 py-6" asChild>
            <a href="#funcionalidades">
              Ver funcionalidades
              <ArrowRight className="h-5 w-5" />
            </a>
          </Button>
        </motion.div>
        
        {/* Floating elements */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.5, delay: 0.5 }}
          className="mt-16 relative"
        >
          <div className="relative mx-auto max-w-2xl">
            {/* Chat preview */}
            <div className="rounded-2xl border border-border bg-card p-6 shadow-2xl shadow-primary/5">
              <div className="flex items-center gap-3 mb-6 pb-4 border-b border-border">
                <div className="w-10 h-10 rounded-full bg-primary/20 flex items-center justify-center">
                  <span className="text-xl">🌙</span>
                </div>
                <div>
                  <h3 className="font-semibold text-foreground">Aisha</h3>
                  <p className="text-xs text-muted-foreground">Online agora</p>
                </div>
              </div>
              
              <div className="space-y-4">
                <div className="flex justify-end">
                  <div className="bg-primary text-primary-foreground px-4 py-2 rounded-2xl rounded-br-md max-w-xs">
                    <p className="text-sm">Me lembra da reunião amanhã às 10h</p>
                  </div>
                </div>
                <div className="flex justify-start">
                  <div className="bg-secondary text-secondary-foreground px-4 py-2 rounded-2xl rounded-bl-md max-w-sm">
                    <p className="text-sm">✅ Lembrete criado!</p>
                    <p className="text-sm mt-1">📌 Reunião</p>
                    <p className="text-sm">📅 Amanhã às 10:00</p>
                    <p className="text-sm">⏰ Aviso: 15 min antes</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
