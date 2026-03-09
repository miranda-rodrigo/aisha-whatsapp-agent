import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Exclusão de Dados — Aisha",
  description: "Instruções para solicitar a exclusão dos seus dados pessoais no Aisha.",
}

export default function DeletePage() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <div className="max-w-3xl mx-auto px-4 py-16 space-y-10">
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Exclusão de Dados</h1>
          <p className="text-sm text-muted-foreground">Instruções para solicitar a remoção dos seus dados pessoais</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">Como solicitar a exclusão</h2>
          <p className="text-muted-foreground leading-relaxed">
            Em conformidade com a Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018) e as políticas da Meta,
            você tem o direito de solicitar a exclusão de todos os seus dados pessoais armazenados pelo Aisha.
          </p>
        </section>

        <section className="space-y-4">
          <h2 className="text-xl font-semibold text-foreground">Passo a passo</h2>

          <div className="space-y-4">
            <div className="flex gap-4 items-start">
              <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-bold">1</span>
              <div>
                <p className="font-medium text-foreground">Entre em contato via WhatsApp</p>
                <p className="text-muted-foreground text-sm mt-1">
                  Envie uma mensagem para{" "}
                  <a
                    href="https://wa.me/5585999065040?text=Quero%20solicitar%20a%20exclusão%20dos%20meus%20dados"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-foreground hover:underline font-medium"
                  >
                    (85) 99906-5040
                  </a>{" "}
                  com o texto: <em>"Quero solicitar a exclusão dos meus dados"</em>
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start">
              <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-bold">2</span>
              <div>
                <p className="font-medium text-foreground">Confirmação da identidade</p>
                <p className="text-muted-foreground text-sm mt-1">
                  Confirmaremos sua identidade com base no número de telefone registrado no serviço.
                </p>
              </div>
            </div>

            <div className="flex gap-4 items-start">
              <span className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-bold">3</span>
              <div>
                <p className="font-medium text-foreground">Exclusão em até 30 dias</p>
                <p className="text-muted-foreground text-sm mt-1">
                  Após a confirmação, todos os seus dados serão removidos permanentemente dos nossos sistemas em até
                  30 dias. Você receberá uma confirmação quando a exclusão for concluída.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">O que será excluído</h2>
          <ul className="list-disc list-inside text-muted-foreground space-y-1 ml-2">
            <li>Histórico de conversas</li>
            <li>Lembretes e tarefas agendadas</li>
            <li>Preferências e configurações personalizadas</li>
            <li>Áudios, imagens e documentos enviados</li>
            <li>Quaisquer outros dados pessoais associados ao seu número</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">Dados retidos por obrigação legal</h2>
          <p className="text-muted-foreground leading-relaxed">
            Alguns dados podem ser retidos por prazo determinado em cumprimento a obrigações legais ou regulatórias,
            mesmo após a solicitação de exclusão. Nesse caso, informaremos sobre os dados retidos e o prazo de
            retenção.
          </p>
        </section>

        <div className="rounded-lg border border-border p-6 space-y-2">
          <p className="font-medium text-foreground">Contato direto</p>
          <p className="text-muted-foreground text-sm">
            Para dúvidas ou para iniciar o processo de exclusão:
          </p>
          <a
            href="https://wa.me/5585999065040?text=Quero%20solicitar%20a%20exclusão%20dos%20meus%20dados"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 mt-2 px-4 py-2 rounded-md bg-primary text-primary-foreground text-sm font-medium hover:bg-primary/90 transition-colors"
          >
            📱 Solicitar exclusão via WhatsApp
          </a>
        </div>
      </div>
      <Footer />
    </main>
  )
}
