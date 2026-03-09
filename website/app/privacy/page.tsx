import { Navbar } from "@/components/navbar"
import { Footer } from "@/components/footer"
import type { Metadata } from "next"

export const metadata: Metadata = {
  title: "Política de Privacidade — Aisha",
  description: "Política de Privacidade do Aisha, assistente pessoal inteligente via WhatsApp.",
}

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-background">
      <Navbar />
      <div className="max-w-3xl mx-auto px-4 py-16 space-y-10">
        <div>
          <h1 className="text-3xl font-bold text-foreground mb-2">Política de Privacidade</h1>
          <p className="text-sm text-muted-foreground">Última atualização: março de 2026</p>
        </div>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">1. Quem somos</h2>
          <p className="text-muted-foreground leading-relaxed">
            O Aisha é um serviço de assistente pessoal inteligente via WhatsApp, desenvolvido e operado pela{" "}
            <strong className="text-foreground">Price Pulse Consultoria Estratégica Ltda</strong>, inscrita no CNPJ
            52.988.669/0001-37, com sede na Av. Oliveira Paiva, 1206, Sala M22, Cidade dos Funcionários, Fortaleza/CE,
            CEP 60822-130.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">2. Dados que coletamos</h2>
          <p className="text-muted-foreground leading-relaxed">
            Para o funcionamento do serviço, coletamos e processamos os seguintes dados:
          </p>
          <ul className="list-disc list-inside text-muted-foreground space-y-1 ml-2">
            <li>Número de telefone do WhatsApp</li>
            <li>Mensagens de texto enviadas para o assistente</li>
            <li>Áudios enviados para transcrição</li>
            <li>Imagens e documentos enviados para análise</li>
            <li>Preferências e configurações do usuário</li>
            <li>Lembretes e tarefas agendadas</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">3. Como usamos os dados</h2>
          <p className="text-muted-foreground leading-relaxed">
            Os dados coletados são utilizados exclusivamente para:
          </p>
          <ul className="list-disc list-inside text-muted-foreground space-y-1 ml-2">
            <li>Processar e responder às mensagens enviadas ao assistente</li>
            <li>Executar funcionalidades como transcrição de áudio, geração de imagens e análise de documentos</li>
            <li>Gerenciar lembretes e tarefas agendadas pelo usuário</li>
            <li>Melhorar a qualidade e personalização do serviço</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed">
            Não vendemos, alugamos nem compartilhamos seus dados pessoais com terceiros para fins comerciais.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">4. Compartilhamento com terceiros</h2>
          <p className="text-muted-foreground leading-relaxed">
            Para o funcionamento do serviço, seus dados podem ser processados por:
          </p>
          <ul className="list-disc list-inside text-muted-foreground space-y-1 ml-2">
            <li><strong className="text-foreground">Meta (WhatsApp)</strong> — plataforma de mensagens</li>
            <li><strong className="text-foreground">OpenAI</strong> — processamento de linguagem natural e geração de conteúdo</li>
            <li><strong className="text-foreground">Google</strong> — serviços de IA e infraestrutura</li>
          </ul>
          <p className="text-muted-foreground leading-relaxed">
            Todos os terceiros utilizados seguem políticas de privacidade próprias e estão em conformidade com as
            legislações aplicáveis.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">5. Retenção dos dados</h2>
          <p className="text-muted-foreground leading-relaxed">
            Mantemos seus dados enquanto você utilizar o serviço. Você pode solicitar a exclusão dos seus dados a
            qualquer momento pelo contato abaixo. Após a solicitação, os dados serão removidos em até 30 dias.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">6. Seus direitos (LGPD)</h2>
          <p className="text-muted-foreground leading-relaxed">
            Em conformidade com a Lei Geral de Proteção de Dados (Lei nº 13.709/2018), você tem direito a:
          </p>
          <ul className="list-disc list-inside text-muted-foreground space-y-1 ml-2">
            <li>Confirmar a existência de tratamento dos seus dados</li>
            <li>Acessar seus dados</li>
            <li>Corrigir dados incompletos ou desatualizados</li>
            <li>Solicitar a exclusão dos seus dados</li>
            <li>Revogar o consentimento a qualquer momento</li>
          </ul>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">7. Segurança</h2>
          <p className="text-muted-foreground leading-relaxed">
            Adotamos medidas técnicas e organizacionais para proteger seus dados contra acesso não autorizado,
            alteração, divulgação ou destruição. As comunicações são realizadas via canais criptografados.
          </p>
        </section>

        <section className="space-y-3">
          <h2 className="text-xl font-semibold text-foreground">8. Contato</h2>
          <p className="text-muted-foreground leading-relaxed">
            Para dúvidas, solicitações ou exercício dos seus direitos, entre em contato:
          </p>
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
