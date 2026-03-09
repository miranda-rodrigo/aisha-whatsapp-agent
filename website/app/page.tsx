import { Navbar } from "@/components/navbar"
import { Hero } from "@/components/hero"
import { TechStack } from "@/components/tech-stack"
import { Features } from "@/components/features"
import { Demo } from "@/components/demo"
import { HowItWorks } from "@/components/how-it-works"
import { CTA } from "@/components/cta"
import { Footer } from "@/components/footer"

export default function Home() {
  return (
    <main className="min-h-screen bg-background">
      <div className="fixed top-0 left-0 right-0 z-[60] w-full bg-primary/10 border-b border-primary/20 text-center py-2 px-4">
        <p className="text-sm text-primary font-medium">
          🚀 No momento aberto apenas para <strong>beta-testers</strong> — disponível em breve para o público geral!
        </p>
      </div>
      <Navbar />
      <Hero />
      <TechStack />
      <Features />
      <Demo />
      <section id="como-funciona">
        <HowItWorks />
      </section>
      <CTA />
      <Footer />
    </main>
  )
}
