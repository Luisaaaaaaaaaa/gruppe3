import json

from app.medical_rules.red_flag_engine import RedFlag
from app.output.export_json import export_summary
from app.output.summary_builder import AnamnesisSummary


def test_export_summary_creates_unique_filenames(tmp_path) -> None:
    summary = AnamnesisSummary(
        patient_id="demo-1",
        patient_name="Test Patient",
        scenario="A",
        timestamp="2026-06-01T10:15:30",
        answers={"symptom_dauer": "2 Tage"},
        vitals={"systolisch": 120},
        vital_sources={"systolisch": "simuliert"},
        red_flags=[
            RedFlag(
                rule_id="rf-1",
                description="Warnzeichen",
                severity="warning",
                triggered_by="symptom",
            )
        ],
    )

    first_path = export_summary(summary, output_dir=tmp_path)
    second_path = export_summary(summary, output_dir=tmp_path)

    assert first_path != second_path
    assert first_path.exists()
    assert second_path.exists()
    data = json.loads(first_path.read_text(encoding="utf-8"))
    assert data["vital_sources"] == {"systolisch": "simuliert"}
