#!/usr/bin/env python3
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
URL = 'https://web.whatsapp.com/'

def main():
    accounts = json.loads((ROOT / 'accounts.json').read_text())['accounts']
    if len(sys.argv) != 2 or sys.argv[1] not in accounts:
        print('Usage: wa.py <' + '|'.join(accounts) + '>')
        return 2
    alias = sys.argv[1]
    cfg = accounts[alias]
    browser = cfg['browser'].lower()
    if browser == 'safari':
        cmd = ['open', '-a', 'Safari', URL]
    elif browser == 'chrome':
        profile = cfg['profile']
        if '/' in profile or profile in ('.', '..'):
            raise ValueError('Invalid Chrome profile directory')
        # Launch the Chrome binary directly so --profile-directory is respected
        # even when another Chrome window is already running.
        chrome = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'
        if not Path(chrome).exists():
            raise FileNotFoundError(chrome)
        cmd = [chrome, f'--profile-directory={profile}', URL]
    else:
        raise ValueError(f'Unsupported browser: {browser}')
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    print(f'Opened {alias} ({browser})')
    return 0

if __name__ == '__main__':
    sys.exit(main())
