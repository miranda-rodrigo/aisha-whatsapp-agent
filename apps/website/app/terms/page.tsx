import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Termos de Serviço — Aisha",
  description: "Termos de Serviço do Aisha, assistente pessoal inteligente via WhatsApp.",
}

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <div className="max-w-3xl mx-auto px-4 py-16 space-y-10">
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Termos de Serviço</h1>
          <p className="text-sm text-muted-foreground">Última atualização: março de 2026</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">1. Aceitação dos Termos</h2>
          <p className="text-muted-foreground leading-relaxed">
            Ao utilizar o Aisha, você concorda com estes Termos de Serviço e com a nossa Política de Privacidade. Se
            não concordar com qualquer parte destes termos, não utilize o serviço.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">2. Descrição do Serviço</h2>
          <p className="text-muted-foreground leading-relaxed">
            O Aisha é um assistente pessoal inteligente acessível via WhatsApp, desenvolvido pela{" "}
            <strong className="text-foreground">Price Pulse Consultoria Estratégica Ltda</strong> (CNPJ
            52.988.669/0001-37). O serviço oferece funcionalidades como transcrição de áudios, geração de imagens,
            criação de lembretes, análise de documentos e respostas a perguntas gerais.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">3. Elegibilidade</h2>
          <p className="text-muted-foreground leading-relaxed">
            O serviço é destinado a maiores de 18 anos. Ao utilizar o Aisha, você declara ter capacidade legal para
            aceitar estes termos.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">4. Uso Permitido</h2>
          <p className="text-muted-foreground leading-relaxed">Você se compromete a utilizar o serviço de forma lícita e a não:</p>
          <ul className="list-disc list-inside text-muted-foreground space-y-1 ml-2">
            <li>Enviar conteúdo ilegal, ofensivo, difamatório ou que viole direitos de terceiros</li>
            <li>Tentar burlar limites ou sistemas de segurança do serviço</li>
            <li>Utilizar o serviço para spam ou comunicações não solicitadas em massa</li>
            <li>Reproduzir, vender ou sublicenciar o serviço sem autorização expressa</li>
            <li>Utilizar o serviço para fins que violem as políticas da Meta/WhatsApp</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">5. Limitação de Responsabilidade</h2>
          <p className="text-muted-foreground leading-relaxed">
            O Aisha é fornecido "como está". Não garantimos que o serviço será ininterrupto, livre de erros ou que as
            respostas geradas pela IA serão sempre precisas. Não nos responsabilizamos por decisões tomadas com base
            nas respostas do assistente.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">6. Propriedade Intelectual</h2>
          <p className="text-muted-foreground leading-relaxed">
            Todo o conteúdo, marca, código e tecnologia do Aisha são de propriedade da Price Pulse Consultoria
            Estratégica Ltda. É proibida a cópia, distribuição ou engenharia reversa sem autorização.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">7. Pagamento e Cancelamento</h2>
          <p className="text-muted-foreground leading-relaxed">
            Os planos e valores do serviço são informados no ato da contratação. O cancelamento pode ser solicitado a
            qualquer momento pelo contato abaixo, sem multa. Valores já pagos não são reembolsáveis, salvo disposição
            legal em contrário.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">8. Alterações nos Termos</h2>
          <p className="text-muted-foreground leading-relaxed">
            Podemos atualizar estes termos a qualquer momento. Alterações relevantes serão comunicadas via WhatsApp.
            O uso continuado do serviço após as alterações implica aceitação dos novos termos.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">9. Lei Aplicável</h2>
          <p className="text-muted-foreground leading-relaxed">
            Estes termos são regidos pelas leis brasileiras. Fica eleito o foro da comarca de Fortaleza/CE para
            dirimir eventuais conflitos.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">10. Contato</h2>
          <div className="text-muted-foreground space-y-1">
            <p><strong className="text-foreground">Price Pulse Consultoria Estratégica Ltda</strong></p>
            <p>CNPJ: 52.988.669/0001-37</p>
            <p>Av. Oliveira Paiva, 1206, Sala M22 — Cidade dos Funcionários, Fortaleza/CE</p>
            <p>
              WhatsApp:{" "}
              <a
                href="https://wa.me/5585999065040"
                target="_blank"
                rel="noopener noreferrer"
                className="text-foreground hover:underline"
              >
                (85) 99906-5040
              </a>
            </p>
          </div>
        </section>
      </div>
      <Footer />
    </main>
  )
}
