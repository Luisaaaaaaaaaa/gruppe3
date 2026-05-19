from pathlib import Path
import sys


if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.ui.main_window import run_app


if __name__ == "__main__":
    run_app()
