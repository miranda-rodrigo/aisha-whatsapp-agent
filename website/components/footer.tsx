export function Footer() {
  return (
    <footer className="py-8 px-4 border-t border-border">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
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
    </footer>
  )
}
