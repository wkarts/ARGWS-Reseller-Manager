"""Frozen bundles always use their embedded browser, never a machine-wide cache."""
import os

# A stale environment variable must not redirect the bundled executable to a cache.
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "0"
