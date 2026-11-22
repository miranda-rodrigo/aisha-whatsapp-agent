#!/bin/zsh
set -e
cd "${0:A:h}"
chmod +x wa.py
python3 create_apps.py
mkdir -p "$HOME/Applications"
for app in apps/*.app; do
  ditto "$app" "$HOME/Applications/${app:t}"
done
echo "Installed to ~/Applications. Drag apps to Dock from Finder."
