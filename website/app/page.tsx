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
