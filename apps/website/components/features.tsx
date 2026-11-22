"use client"

import { motion } from "framer-motion"
import { 
  MessageCircle, 
  Mic, 
  Image, 
  Bell, 
  FileText, 
  Youtube, 
  Globe, 
  Calendar,
  Sparkles,
  Search,
  Wand2,
  Clock,
  Download
} from "lucide-react"

const features = [
  {
    icon: MessageCircle,
    title: "Conversa Inteligente",
    description: "Chat natural com IA de última geração. A Aisha entende contexto e responde no seu idioma.",
    highlight: "GPT-4.1 & GPT-5.4"
  },
  {
    icon: Mic,
    title: "Transcrição de Áudio",
    description: "Envie áudios e receba textos limpos e refinados. Perfeito para reuniões e anotações.",
    highlight: "Whisper AI"
  },
  {
    icon: Image,
    title: "Geração de Imagens",
    description: "Crie imagens únicas diretamente no WhatsApp. Basta descrever o que você quer.",
    highlight: "GPT-Image 1.5"
  },
  {
    icon: Wand2,
    title: "Edição de Imagens",
    description: "Melhore qualidade, remova fundos, mude estilos e muito mais com edição iterativa.",
    highlight: "Edição por IA"
  },
  {
    icon: Search,
    title: "Busca na Web",
    description: "Informações atualizadas em tempo real. A Aisha pesquisa automaticamente quando precisa.",
    highlight: "Web Search"
  },
  {
    icon: Bell,
    title: "Lembretes",
    description: "Crie lembretes em linguagem natural. Receba avisos e link para Google Calendar.",
    highlight: "APScheduler"
  },
  {
    icon: Calendar,
    title: "Tarefas Agendadas",
    description: "Relatórios recorrentes com pesquisa na web. Receba briefings automáticos.",
    highlight: "Cron Jobs + IA"
  },
  {
    icon: FileText,
    title: "Análise de Documentos",
    description: "Envie PDFs e Word para resumos e análises. Suporta OCR para documentos escaneados.",
    highlight: "PDF & DOCX"
  },
  {
    icon: Youtube,
    title: "Análise de Vídeos",
    description: "Envie links do YouTube para resumos, transcrições e insights sobre o conteúdo.",
    highlight: "Gemini 2.5 Flash"
  },
  {
    icon: Download,
    title: "Download de Vídeos",
    description: "Baixe vídeos do YouTube, Instagram, TikTok e outras plataformas diretamente pelo WhatsApp.",
    highlight: "Multi-plataforma"
  },
  {
    icon: Globe,
    title: "Leitura de Páginas",
    description: "Envie qualquer URL para resumos, traduções e extração de informações.",
    highlight: "Jina Reader"
  },
  {
    icon: Sparkles,
    title: "Personalização",
    description: "A Aisha aprende sobre você e se adapta ao seu estilo e preferências.",
    highlight: "Perfil Pessoal"
  },
  {
    icon: Clock,
    title: "Memória de Contexto",
    description: "Mantém o contexto da conversa por até 10 minutos para respostas mais relevantes.",
    highlight: "Responses API"
  }
]

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
}

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.5 }
  }
}

export function Features() {
  return (
    <section id="funcionalidades" className="py-24 px-4">
      <div className="max-w-7xl mx-auto">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="text-center mb-16"
        >
          <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground mb-4 text-balance">
            Tudo que você precisa
          </h2>
          <p className="text-lg text-muted-foreground max-w-2xl mx-auto text-pretty">
            A Aisha combina os modelos de IA mais avançados em uma experiência simples pelo WhatsApp.
          </p>
        </motion.div>
        
        <motion.div
          variants={containerVariants}
          initial="hidden"
          whileInView="visible"
          viewport={{ once: true }}
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6"
        >
          {features.map((feature) => (
            <motion.div
              key={feature.title}
              variants={itemVariants}
              className="group relative rounded-xl border border-border bg-card p-6 hover:border-primary/50 transition-all duration-300 hover:shadow-lg hover:shadow-primary/5"
            >
              <div className="mb-4 inline-flex items-center justify-center w-12 h-12 rounded-lg bg-primary/10 text-primary group-hover:bg-primary group-hover:text-primary-foreground transition-colors duration-300">
                <feature.icon className="h-6 w-6" />
              </div>
              <h3 className="text-lg font-semibold text-foreground mb-2">{feature.title}</h3>
              <p className="text-sm text-muted-foreground mb-4">{feature.description}</p>
              <span className="inline-flex items-center text-xs font-medium text-primary bg-primary/10 px-2.5 py-1 rounded-full">
                {feature.highlight}
              </span>
            </motion.div>
          ))}
        </motion.div>
      </div>
    </section>
  )
}
