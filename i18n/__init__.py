import os
from i18n.translations import TRANSLATIONS

_current_lang = "en"

def set_language(lang: str):
    global _current_lang
    if lang in ["en", "pt"]:
        _current_lang = lang

def get_language() -> str:
    return _current_lang

def t(key: str, **kwargs) -> str:
    global _current_lang
    # Fallback path if key doesn't exist
    lang_dict = TRANSLATIONS.get(_current_lang, TRANSLATIONS["en"])
    val = lang_dict.get(key, TRANSLATIONS["en"].get(key, key))
    if kwargs:
        try:
            return val.format(**kwargs)
        except Exception:
            return val
    return val
