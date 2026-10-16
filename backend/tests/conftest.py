import os
import sys
from pathlib import Path

os.environ.setdefault("AUTH_SECRET_KEY", "test-only-auth-secret-key-with-more-than-32-bytes")
os.environ.setdefault("ADMIN_TOKEN", "test-only-admin-service-token-with-more-than-32-bytes")
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
