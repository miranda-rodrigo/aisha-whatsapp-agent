"use client"

import { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { cn } from "@/lib/utils"
import Image from "next/image"

const demos = [
  {
    id: "chat",
    title: "Conversa",
    messages: [
      { type: "user", text: "Oi Aisha! Me explica o que são juros compostos?" },
      { type: "bot", text: "Olá! Juros compostos são quando os juros são calculados sobre o valor inicial mais os juros acumulados anteriormente. É o famoso \"juros sobre juros\".\n\nFórmula: M = C × (1 + i)^n\n\nExemplo: R$ 1.000 a 10% ao ano por 3 anos = R$ 1.331" }
    ]
  },
  {
    id: "audio",
    title: "Transcrição",
    messages: [
      { type: "user", text: "🎤 Áudio (1:32)", isAudio: true },
      { type: "bot", text: "📝 Transcrição refinada:\n\n\"Na reunião de hoje discutimos os próximos passos do projeto. Ficou definido que o João vai cuidar da parte técnica e a Maria vai liderar a comunicação com o cliente. Próxima reunião marcada para sexta-feira às 14h.\"" }
    ]
  },
  {
    id: "image",
    title: "Imagem",
    messages: [
      { type: "user", text: "Gera uma imagem de um gato astronauta em estilo aquarela" },
      { type: "bot", text: "✨ Gerando imagem...", isLoading: true },
      { type: "bot", text: "🖼️ Aqui está sua imagem!", isImage: true, image: "Um gato astronauta flutuando no espaço em estilo aquarela" }
    ]
  },
  {
    id: "reminder",
    title: "Lembrete",
    messages: [
      { type: "user", text: "Me lembra de ligar pro médico amanhã às 9h" },
      { type: "bot", text: "✅ Lembrete criado!\n\n📌 Ligar pro médico\n📅 Amanhã às 09:00\n⏰ Aviso: 15 min antes (às 08:45)\n\n🗓️ Adicionar ao Google Calendar:\nhttps://calendar.google.com/..." }
    ]
  },
  {
    id: "youtube",
    title: "YouTube",
    messages: [
      { type: "user", text: "https://youtu.be/dQw4w9WgXcQ resume esse vídeo" },
      { type: "bot", text: "🎬 Analisando vídeo...\n\n📺 \"Never Gonna Give You Up\" - Rick Astley\n\n**Resumo:**\nClássico dos anos 80, o videoclipe mostra Rick Astley dançando enquanto canta sobre compromisso e lealdade em um relacionamento. O vídeo se tornou um fenômeno da internet conhecido como \"Rickrolling\".\n\n⏱️ Duração: 3:33\n👁️ Visualizações: 1.5B+" }
    ]
  },
  {
    id: "download",
    title: "Download",
    messages: [
      { type: "user", text: "baixa esse vídeo https://www.instagram.com/reel/ABC123" },
      { type: "bot", text: "⬇️ Processando download...\n\n📱 Instagram Reels detectado\n🎵 Com áudio: Sim\n📐 Qualidade: 1080p\n\n✅ Download concluído! Enviando..." },
      { type: "bot", text: "🎬 Aqui está seu vídeo!\n\nPlataformas suportadas:\n• YouTube\n• Instagram (posts, reels, stories)\n• TikTok\n• Twitter/X\n• Facebook" }
    ]
  },
  {
    id: "document",
    title: "Documento",
    messages: [
      { type: "user", text: "📄 contrato.pdf (enviado)" },
      { type: "bot", text: "📄 Processando documento...\n\n**Resumo do Contrato:**\n\n• **Partes:** Empresa ABC e Cliente XYZ\n• **Objeto:** Prestação de serviços de consultoria\n• **Valor:** R$ 50.000/mês\n• **Vigência:** 12 meses (renov. automática)\n• **Rescisão:** Aviso de 30 dias\n\nDeseja mais detalhes sobre alguma cláusula?" }
    ]
  }
]

export function Demo() {
  const [activeDemo, setActiveDemo] = useState("chat")
  const currentDemo = demos.find(d => d.id === activeDemo)

  return (
    <section className="py-24 px-4 bg-secondary/30">
      <div className="max-w-5xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-12"
        >
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground mb-4 text-balance">
            Veja como funciona
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            Exemplos reais de conversas com a Aisha. Simples, rápido e inteligente.
          </p>
        </motion.div>
        
        {/* Demo tabs */}
        <div className="flex flex-wrap justify-center gap-2 mb-8">
          {demos.map((demo) => (
            <button
              key={demo.id}
              onClick={() => setActiveDemo(demo.id)}
              className={cn(
                "px-4 py-2 rounded-full text-sm font-medium transition-all duration-200",
                activeDemo === demo.id
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground hover:bg-secondary/80"
              )}
            >
              {demo.title}
            </button>
          ))}
        </div>
        
        {/* Chat preview */}
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="max-w-2xl mx-auto"
        >
          <div className="rounded-2xl border border-border bg-card overflow-hidden shadow-2xl shadow-primary/5">
            {/* Chat header */}
            <div className="flex items-center gap-3 p-4 border-b border-border bg-secondary/50">
              <div className="w-10 h-10 rounded-full overflow-hidden">
                <Image src="/logo.png" alt="Aisha" width={40} height={40} className="object-cover" />
              </div>
              <div>
                <h3 className="font-semibold text-foreground">Aisha</h3>
                <p className="text-xs text-muted-foreground">Online</p>
              </div>
            </div>
            
            {/* Chat messages */}
            <div className="p-4 min-h-[300px] max-h-[400px] overflow-y-auto">
              <AnimatePresence mode="wait">
                <motion.div
                  key={activeDemo}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ duration: 0.3 }}
                  className="space-y-4"
                >
                  {currentDemo?.messages.map((message, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.1 }}
                      className={cn(
                        "flex",
                        message.type === "user" ? "justify-end" : "justify-start"
                      )}
                    >
                      <div
                        className={cn(
                          "px-4 py-3 rounded-2xl max-w-[85%]",
                          message.type === "user"
                            ? "bg-primary text-primary-foreground rounded-br-md"
                            : "bg-secondary text-secondary-foreground rounded-bl-md"
                        )}
                      >
                        <p className="text-sm whitespace-pre-line">{message.text}</p>
                      </div>
                    </motion.div>
                  ))}
                </motion.div>
              </AnimatePresence>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  )
}
