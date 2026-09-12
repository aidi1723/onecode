import re


RUN_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z")


def validate_run_id(value: str, *, field_name: str = "run_id") -> str:
    if not isinstance(value, str) or RUN_ID_PATTERN.fullmatch(value) is None:
        raise ValueError(f"invalid {field_name}")
    return value


def validate_optional_run_id(value: str | None, *, field_name: str = "run_id") -> str | None:
    if value is None:
        return None
    return validate_run_id(value, field_name=field_name)
