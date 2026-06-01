import json
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from app.output.summary_builder import AnamnesisSummary


def export_summary(summary: AnamnesisSummary, output_dir: Path | None = None) -> Path:
    if output_dir is None:
        output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    unique_suffix = uuid4().hex[:8]
    filename = (
        f"anamnese_{summary.patient_id}_{summary.timestamp.replace(':', '-')}"
        f"_{unique_suffix}.json"
    )
    filepath = output_dir / filename

    data = asdict(summary)
    data["red_flags"] = [asdict(rf) for rf in summary.red_flags]
    data["hinweis"] = (
        "SYNTHETISCHE DATEN - Kein realer Patient. "
        "Dieses Dokument wurde von einem Assistenzsystem erstellt und "
        "ersetzt keine aerztliche Bewertung."
    )

    filepath.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return filepath
