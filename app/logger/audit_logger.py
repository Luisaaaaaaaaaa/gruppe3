import logging
import sys

_logger = logging.getLogger("anamnese_agent")


def setup_logger() -> None:
    if _logger.handlers:
        return
    _logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%H:%M:%S"
    )
    handler.setFormatter(formatter)
    _logger.addHandler(handler)


def log_info(message: str) -> None:
    _logger.info(message)


def log_warning(message: str) -> None:
    _logger.warning(message)


def log_critical(message: str) -> None:
    _logger.critical(message)


def log_state_change(old_state: str, new_state: str) -> None:
    _logger.info(f"State: {old_state} -> {new_state}")


def log_red_flag(rule_id: str, description: str, severity: str) -> None:
    if severity == "critical":
        _logger.critical(f"RED FLAG [{rule_id}]: {description}")
    else:
        _logger.warning(f"RED FLAG [{rule_id}]: {description}")


def log_answer(key: str, value: str) -> None:
    _logger.debug(f"Antwort: {key} = {value}")


def log_escalation(reason: str) -> None:
    _logger.critical(f"ESKALATION: {reason}")
