import json
from functools import lru_cache
from pathlib import Path
from typing import Any

SUPPORTED_LANGUAGES = ("en", "ru")
DEFAULT_LANGUAGE = "en"

_LOCALES_DIR = Path(__file__).parent / "locales"


def normalize_lang(lang: str | None) -> str:
    if not lang:
        return DEFAULT_LANGUAGE
    code = lang.strip().lower().split("-")[0]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


@lru_cache(maxsize=8)
def _load_locale(lang: str) -> dict[str, Any]:
    normalized = normalize_lang(lang)
    path = _LOCALES_DIR / f"{normalized}.json"
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _lookup(data: dict[str, Any], key: str) -> Any:
    current: Any = data
    for part in key.split("."):
        if isinstance(current, dict) and part in current:
            current = current[part]
        else:
            return None
    return current


def get_localized(key: str, lang: str | None = DEFAULT_LANGUAGE) -> Any:
    """Resolve any localized value (string, list, dict) by dotted key with English fallback."""
    normalized = normalize_lang(lang)
    val = _lookup(_load_locale(normalized), key)
    if val is None and normalized != DEFAULT_LANGUAGE:
        val = _lookup(_load_locale(DEFAULT_LANGUAGE), key)
    return val


def t(key: str, lang: str | None = DEFAULT_LANGUAGE, **kwargs: Any) -> str:
    """Translate a dotted key and interpolate optional format parameters."""
    val = get_localized(key, lang)
    if not isinstance(val, str):
        return key
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val
