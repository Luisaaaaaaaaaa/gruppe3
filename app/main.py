from pathlib import Path
import sys


if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.logger.audit_logger import setup_logger
from app.ui.main_window import run_app


if __name__ == "__main__":
    setup_logger()
    run_app()
