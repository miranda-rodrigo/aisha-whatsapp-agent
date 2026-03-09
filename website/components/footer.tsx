export function Footer() {
  return (
    <footer className="py-10 px-4 border-t border-border">
      <div className="max-w-7xl mx-auto flex flex-col gap-6">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="text-2xl">🌙</span>
            <span className="font-semibold text-foreground">Aisha</span>
          </div>

          <p className="text-sm text-muted-foreground text-center">
            Assistente pessoal inteligente via WhatsApp
          </p>

          <p className="text-sm text-muted-foreground">
            &copy; {new Date().getFullYear()} Aisha
          </p>
        </div>

        <div className="border-t border-border pt-6 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="text-xs text-muted-foreground space-y-1">
            <p className="font-medium text-foreground">Price Pulse Consultoria Estratégica Ltda</p>
            <p>CNPJ: 52.988.669/0001-37</p>
            <p>Av. Oliveira Paiva, 1206, Sala M22 — Cidade dos Funcionários</p>
            <p>Fortaleza, CE — CEP 60822-130</p>
          </div>

          <div className="flex flex-col items-start md:items-end gap-2">
            <a
              href="https://wa.me/5585999065040"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              📱 (85) 99906-5040
            </a>
            <a
              href="/privacy"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
            >
              Política de Privacidade
            </a>
            <a
              href="/terms"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
            >
              Termos de Serviço
            </a>
            <a
              href="/delete"
              className="text-xs text-muted-foreground hover:text-foreground transition-colors underline underline-offset-2"
            >
              Exclusão de Dados
            </a>
          </div>
        </div>
      </div>
    </footer>
  )
}
