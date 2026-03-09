"use client"

import { Button } from "@/components/ui/button"
import { MessageCircle } from "lucide-react"
import { motion } from "framer-motion"
import Image from "next/image"

export function CTA() {
  return (
    <section className="py-24 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="max-w-4xl mx-auto text-center"
      >
        <div className="relative rounded-3xl border border-border bg-gradient-to-br from-card to-primary/5 p-12 md:p-16 overflow-hidden">
          {/* Background decoration */}
          <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.02)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.02)_1px,transparent_1px)] bg-[size:32px_32px] opacity-50" />
          
          <div className="relative z-10">
            <div className="inline-flex items-center justify-center w-20 h-20 rounded-2xl overflow-hidden mb-8">
              <Image src="/logo.png" alt="Aisha" width={80} height={80} className="object-cover" />
            </div>
            
            <h2 className="text-3xl sm:text-4xl md:text-5xl font-bold text-foreground mb-4 text-balance">
              Comece a usar agora
            </h2>
            
            <p className="text-lg text-muted-foreground max-w-xl mx-auto mb-8 text-pretty">
              Mande uma mensagem para a Aisha e descubra como a IA pode facilitar seu dia a dia.
            </p>
            
            <Button size="lg" className="gap-2 text-lg px-8 py-6" asChild>
              <a href="https://wa.me/5585941322222" target="_blank" rel="noopener noreferrer">
                <MessageCircle className="h-6 w-6" />
                Conversar com Aisha
              </a>
            </Button>
            
            <p className="text-sm text-muted-foreground mt-6">
              +55 85 9413-2222
            </p>
          </div>
        </div>
      </motion.div>
    </section>
  )
}
