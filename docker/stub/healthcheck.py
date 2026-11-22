import os
import sys
import urllib.request

try:
    urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:{os.environ.get('PORT', '8000')}/healthz", headers={"X-Healthcheck": "1"}), timeout=2)
except Exception:
    sys.exit(1)
