"""Runtime hook included only in the optional Chromium Windows bundle."""
import os

os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", "0")
os.environ.setdefault("RESMAN_BROWSER_ENABLED", "1")
