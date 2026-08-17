#!/usr/bin/env bash
# LTC Watch nightly refresh. Quiet on success (cron contract); logs to file.
set -euo pipefail
cd /home/jigar/dev/ltc-watch
LOG=state/refresh.log
mkdir -p state
{
  echo "=== $(date -Is)"
  python3 ltc.py --city Toronto
  python3 briefs.py
  cp site/* dist/
  python3 render.py
  npx -y netlify-cli deploy --prod --dir dist
} >> "$LOG" 2>&1 || { echo "LTC WATCH REFRESH FAILED — see $LOG"; exit 1; }
