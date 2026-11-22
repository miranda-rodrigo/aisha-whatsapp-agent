#!/usr/bin/env python3
import json, subprocess
from pathlib import Path
root = Path(__file__).resolve().parent
accounts = json.loads((root / 'accounts.json').read_text())['accounts']
apps = root / 'apps'
apps.mkdir(exist_ok=True)
for alias in accounts:
    name = 'WA ' + alias.title()
    app = apps / (name + '.app')
    if app.exists() and not any(app.iterdir()):
        app.rmdir()
    script = f'''on run
    do shell script "/usr/bin/python3 " & quoted form of {str(root / 'wa.py')!r} & " " & quoted form of {alias!r}
end run'''
    # AppleScript literal strings use double quotes, not Python repr
    import json as js
    script = 'on run\n    do shell script "/usr/bin/python3 " & quoted form of ' + js.dumps(str(root / 'wa.py')) + ' & " " & quoted form of ' + js.dumps(alias) + '\nend run\n'
    subprocess.run(['osacompile', '-o', str(app), '-e', script], check=True)
    print(app)
