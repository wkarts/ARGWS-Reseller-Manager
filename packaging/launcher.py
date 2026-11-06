"""One executable: GUI by default, service mode with --server."""
import sys
from pathlib import Path
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if __name__ == "__main__":
    if "--server" in sys.argv:
        sys.argv.remove("--server")
        from app.runtime import main
        main()
    else:
        from app.desktop import main
        main()
