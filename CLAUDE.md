# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project overview

KI-gestützter Anamnese-Agent: a prototype primary-care pre-anamnesis assistant for teaching. It runs a structured pre-consultation interview on **synthetic** patient data, detects scenario-specific red flags, captures vital parameters via device simulators, and produces a structured summary for clinical staff. It is an assistance/demonstration system only — it makes no diagnosis and gives no therapy recommendation. All user-facing text and most code identifiers are in German; preserve this.

## Commands

```bash
# Run patient mode (self-login + scenario selection) → http://127.0.0.1:8080
python app/main.py

# Run staff mode (day list, patient selection, prepared scenarios) → http://127.0.0.1:8081
python app/main_personal.py

# Tests (260+ tests, no pytest config file — run from repo root)
python -m pytest                                   # all
python -m pytest app/tests/unit                    # unit only
python -m pytest app/tests/unit/test_cough_scenario.py            # single file
python -m pytest app/tests/unit/test_dialogue_controller.py::test_question_progress_counts_only_displayed_questions  # single test

# Standalone LLM connectivity check (not a pytest test)
python -m app.tests.integration.test_llm_endpoint
```

Dependencies (`requirements.txt`): `nicegui`, `openai`, `reportlab`. README suggests a conda env named `SET` on Python 3.12. There is no linter or build step configured.

## Architecture

The flow is **UI → DialogueController → (scenarios, red-flag engine, summary builder, export)**. The two `main*.py` entry points differ only in the `entry_mode` / port / title passed to `run_app` in `app/ui/web_app.py`.

### Dialogue state machine (`app/dialogue/`)
`state_machine.py` defines `DialogueState` and a fixed forward transition table: `EXPLAIN_ROLE → REQUEST_CONSENT → ANAMNESIS → VITAL_PARAMETERS → RED_FLAG_CHECK → SUMMARY → HANDOVER → END`, with `ESCALATION → END`. `jump_to()` is used for consent decline and **critical escalation** (jumps straight to `ESCALATION`).

`dialogue_controller.py` is the orchestration core. One `DialogueController` exists **per active scenario**; the UI holds a list (`session.controllers`) and runs them together. Key behaviors:
- It receives `display_message` and `request_input` callbacks from the UI — the controller never touches NiceGUI directly. `request_input(callback)` stores a one-shot callback the UI invokes with the next answer.
- `_load_questions()` assembles the question list dynamically: first scenario question, then **record-derived** questions about existing diagnoses/risk factors/medications (`_conditions_questions`, `_medication_questions`), then the rest of the scenario questions (skipping the static ones now covered by record data). This means the question set depends on the patient's data, not just the scenario.
- `is_question_visible()` holds **all conditional follow-up logic** (per-scenario branches + medication adherence chains). `_should_ask_question` delegates to it. Question progress counts only visible questions.
- `defer_anamnesis=True` (set by the web UI): on entering `ANAMNESIS` the controller does **not** auto-ask. The UI runs an AI symptom pre-chat first, then calls `begin_anamnesis(prefilled=...)` to seed AI-extracted answers and start the step-by-step dialogue.
- Escalation is checked **incrementally** after each answer and after device measurements via `check_partial_answers_for_escalation` / `preview_partial_red_flags` — a `critical` flag stops the interview immediately. `preview_partial_red_flags` must not mutate state.
- Two answer-submission paths: step-by-step (`_on_anamnesis_answer`) and the whole-form `submit_mass_anamnesis`. `update_answers_and_regenerate` re-runs red flags and rebuilds the summary after edits.

### Scenarios (`app/scenarios/`)
Four scenarios keyed `A/B/C/D` (UI) ↔ `cough/chest_pain/hypertension/diabetes` (internal); the mapping lives in `SCENARIO_MAP` in `dialogue_controller.py`. Each module exports `QUESTIONS: list[AnamnesisQuestion]`. **`AnamnesisQuestion` is defined in `hypertension_scenario.py`** and imported by the others (fields: `key`, `text`, `required`, `input_type` ∈ `freitext`/`ja_nein`/`zahl`, optional slider bounds). Some scenarios add helpers used at summary time, e.g. `berechne_marburger_herzscore` (chest pain), `berechne_diabetes_verlaufsuebersicht` + `should_ask_follow_up` (diabetes).

### Red-flag engine (`app/medical_rules/`)
`red_flag_engine.py` — `check(scenario, answers, vitals, patient_medications)` dispatches to `check_cough/check_hypertension/check_chest_pain/check_diabetes`, each returning `list[RedFlag]` (frozen dataclass: `rule_id`, `description`, `severity` ∈ `warning`/`critical`, `triggered_by`). Rules are plain keyword/threshold checks. `severity == "critical"` drives escalation everywhere — preserve this contract when adding rules. `scenario_recommendation.py` maps a patient's `conditions` string to a recommended scenario by keyword (priority diabetes > hypertension > chest_pain > cough).

### Patient data (`app/patient_import/`)
`patientenTagesliste.json` is a rich nested PVS-style export. `PatientListClient` flattens it into the flat dataclasses in `patient_schema.py` (`PatientRecord`, `PatientDetails`, both frozen). The client is **bidirectional**: `append_patient` / `update_prepared_scenarios` serialize records back to the nested JSON (`_record_to_entry` and the `_parse_*` helpers). `web_app.py` loads `PATIENTS` once at import and reassigns the module global after edits. When changing `PatientDetails` fields, update both the `_extract_*` (read) and `_parse_*` (write) sides.

### Devices (`app/devices/`)
`simulators.py` `Simulator` generates randomized but plausible weight/BMI, blood pressure, and pulse-oximeter values from gender/height/age. There is deliberately **no blood-glucose simulator** (diabetes glucose values are patient-reported only). Adapters in the same package wrap the simulator behind a device interface.

### AI / LLM (`app/ai/`)
Two independent uses of an **OpenAI-compatible** endpoint:
- `symptom_extractor.extract_answers(text, questions)` — pre-chat free text → `{question_key: answer}` JSON, used to prefill the form.
- `assistant_chat.answer_question(...)` — in-form help chatbot.

Both read config from env vars **`LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL`** (each with its own `_load_env()` reading the repo-root `.env`), defaulting to a self-hosted DeepSeek server. Note the `.env` currently holds `GEMINI_API_KEY`, which the code does not read. Both functions are defensive: missing `openai`, unreachable endpoint, or bad JSON all degrade gracefully (empty dict / fallback reply) and log via the audit logger — keep new LLM code non-fatal.

### Output (`app/output/`)
`summary_builder.build_summary(...)` produces `AnamnesisSummary` and, crucially, `build_grouped_sections(scenario, ...)` which maps raw answer keys to human-readable, scenario-specific grouped sections (this is the large per-scenario display logic). `export_json.export_summary` writes JSON to `output/`; `export_pdf` renders a PDF via reportlab. Every export is stamped as synthetic data.

### UI (`app/ui/web_app.py`)
Single large NiceGUI module (~4300 lines). All state is in the per-browser `BrowserSession` dataclass; `refresh_ui()` calls `.refresh()` on the `@ui.refreshable` header/main/sidebar render functions. The owl avatar is inline SVG + CSS animations in `STYLE_BLOCK`; speaking animation is driven from the browser `speechSynthesis` API toggling a `body.avatar-is-speaking` class. Logic helpers in this module (form field wrappers, escalation checks, notification dismissal) are covered by `test_web_app_form_helpers.py` and `test_web_app_notifications.py` — prefer extracting testable module-level functions over inlining logic in render closures.

### Logging (`app/logger/audit_logger.py`)
Module-level logger `anamnese_agent`; call `setup_logger()` once at startup (both entry points do). Use the `log_*` helpers (`log_info`, `log_red_flag`, `log_escalation`, `log_state_change`, `log_answer`) rather than `print`.

## Conventions

- Tests import via the `app.` package path and run from the repo root (the `main*.py` files add the repo root to `sys.path` for direct execution). There is no `conftest.py`.
- Dataclasses are the data-modeling primitive; `PatientRecord`/`PatientDetails`/`RedFlag`/`AnamnesisQuestion` are frozen — construct new instances instead of mutating.
- `ja_nein` answers are normalized loosely (`ja/j/yes/y` ↔ `nein/n/no`); `unbekannt` is a valid sentinel for numeric/vital answers meaning "not known", distinct from empty.
- Keep the controller UI-agnostic (callbacks only) and keep `critical` severity as the single escalation trigger.
