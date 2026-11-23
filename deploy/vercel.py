"""Deploy the frontend (frontend/) to Vercel production with the token from deploy/.env.production.

The token goes to the Vercel CLI through its environment, so it never appears in a command line or log.
The first run links frontend/ to a Vercel project (created if needed); frontend/vercel.json holds the
build settings and the /api rewrite to the Render API.
"""

import os
import subprocess
import sys
from pathlib import Path

from prodenv import read_env_file

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"

if __name__ == "__main__":
    token = read_env_file().get("VERCEL_TOKEN")
    if not token:
        sys.exit("Fill in VERCEL_TOKEN in deploy/.env.production.")
    env = {**os.environ, "VERCEL_TOKEN": token}
    vercel = ["npx", "--yes", "vercel@latest"]
    if not (FRONTEND / ".vercel" / "project.json").exists():
        project = read_env_file().get("VERCEL_PROJECT", "taxora")
        if subprocess.call([*vercel, "link", "--yes", "--project", project], cwd=FRONTEND, env=env):
            sys.exit("vercel link failed")
    sys.exit(subprocess.call([*vercel, "deploy", "--prod", "--yes", *sys.argv[1:]], cwd=FRONTEND, env=env))
