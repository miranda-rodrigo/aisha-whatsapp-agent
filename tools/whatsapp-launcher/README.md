# WhatsApp Launcher (macOS)

Utilitário da Aisha para abrir contas WhatsApp Web; não participa do backend.

1. Copie `accounts.example.json` para `accounts.json` e configure os perfis que já estão autenticados no Chrome/Safari.
2. Teste `python3 tools/whatsapp-launcher/wa.py personal` a partir da raiz.
3. Execute `tools/whatsapp-launcher/install.sh` para gerar os apps em `~/Applications`.

Os scripts resolvem seu diretório pelo próprio arquivo. Se mover o repositório, execute o instalador novamente. No Atalhos do macOS use `python3 "$HOME/useful-repos/aisha/tools/whatsapp-launcher/wa.py" personal` ou abra o app gerado. `accounts.json` e `apps/` não entram no Git.
