#!/bin/bash
set -e
cd "$(dirname "$0")"
for eve_python in "/Library/Frameworks/Python.framework/Versions/3.15/bin/python3" "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" "/opt/homebrew/bin/python3" "/usr/local/bin/python3" "$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3" "/usr/bin/python3"; do
  if [ -x "$eve_python" ] && "$eve_python" -c 'import sys; assert sys.version_info >= (3,9)' >/dev/null 2>&1; then
    if "$eve_python" launch.py "$@"; then exit 0; else
      echo "Az indítás nem sikerült. A Hasznalat.md útmutató segít."
      read -r -p "Az ablak bezárásához nyomj Entert. "
      exit 1
    fi
  fi
done
echo "Python 3 telepítése szükséges: https://www.python.org/downloads/macos/"
read -r -p "Az ablak bezárásához nyomj Entert. "
