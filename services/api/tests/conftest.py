import os
import sys
from pathlib import Path

os.environ.setdefault("DEMO_MODE", "true")
os.environ.setdefault("AEGISDESK_AUTH_SECRET", "test-auth-secret")
os.environ.setdefault("AEGISDESK_POLICY_MODE", "python")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
