"""Check that deployment inputs and Git staging exclude local/private artifacts."""
import subprocess
from pathlib import Path


def main():
    paths = subprocess.check_output(["git", "ls-files", "-z"], text=True).split("\0")
    bad = [p for p in paths if p and (
        p.startswith(("local/", "conversas_brutas/", "output/"))
        or "/projetos_extras/" in p
        or Path(p).name == ".env"
        or p == "tools/whatsapp-launcher/accounts.json"
    )]
    if bad:
        raise SystemExit("Private paths tracked: " + ", ".join(bad))
    for p in Path("packages/chat-analysis/src").rglob("*.py"):
        if "from aisha." in p.read_text() or "import aisha." in p.read_text():
            raise SystemExit("Shared core imports production agent: " + str(p))
    print("Repository boundaries: OK")

if __name__ == "__main__":
    main()
