# Gemeinsame Hilfsfunktionen der Betriebsskripte
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
if docker compose version >/dev/null 2>&1; then DC="docker compose"; else DC="docker-compose"; fi
[ -f .env ] || { echo "Hinweis: .env fehlt – kopiere .env.example nach .env"; cp .env.example .env; }
