"""Configure and deploy the API on Render through its REST API (https://api-docs.render.com).

    python deploy/render.py env      # set the secret env vars from deploy/.env.production, then redeploy
    python deploy/render.py deploy   # trigger a deploy of the latest commit
    python deploy/render.py status   # the service URL and the latest deploys

Values are sent straight to Render; only their names are printed.
"""

import json
import sys
import urllib.error
import urllib.request

from prodenv import production_env, read_env_file

API = "https://api.render.com/v1"
SECRETS = ("DATABASE_URL", "SUPABASE_URL", "SUPABASE_SECRET_KEY", "LLM_API_KEY", "FRONTEND_ORIGIN", "GOOGLE_CLIENT_ID")


def call(token: str, method: str, path: str, body=None):
    request = urllib.request.Request(f"{API}{path}", method=method,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Authorization": f"Bearer {token}", "Accept": "application/json",
                                              "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            text = response.read().decode()
            return json.loads(text) if text else None
    except urllib.error.HTTPError as exc:
        sys.exit(f"Render API {method} {path}: {exc.code} {exc.read().decode()[:300]}")


def service(token: str, name: str) -> dict:
    found = [item["service"] for item in call(token, "GET", f"/services?name={name}&limit=20")]
    if not found:
        sys.exit(f"No Render service named {name!r}. Create it first (README, Deployment).")
    return found[0]


def main(action: str) -> None:
    values = read_env_file()
    token, name = values.get("RENDER_API_KEY"), values.get("RENDER_SERVICE_NAME", "taxora-api")
    if not token:
        sys.exit("Fill in RENDER_API_KEY in deploy/.env.production.")
    target = service(token, name)
    sid = target["id"]
    if action == "env":
        env = production_env(values)
        for key in SECRETS:
            if env.get(key):
                call(token, "PUT", f"/services/{sid}/env-vars/{key}", {"value": env[key]})
                print(f"  set {key}")
        action = "deploy"
    if action == "deploy":
        deploy = call(token, "POST", f"/services/{sid}/deploys", {"clearCache": "do_not_clear"})
        print(f"deploy {deploy['id']} started ({deploy['status']})")
    elif action == "status":
        print(target["serviceDetails"].get("url"), "| suspended:", target.get("suspended"))
        for item in call(token, "GET", f"/services/{sid}/deploys?limit=3"):
            deploy = item["deploy"]
            message = ((deploy.get("commit") or {}).get("message") or "").splitlines()
            print(f"  {deploy['createdAt'][:19]}  {deploy['status']:<22} {message[0][:60] if message else ''}")


if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ("env", "deploy", "status"):
        sys.exit(__doc__)
    main(sys.argv[1])
