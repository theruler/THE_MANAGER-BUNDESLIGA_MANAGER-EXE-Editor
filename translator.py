import re
import json
import urllib.parse
import urllib.request
from i18n import tr

CONTROL_TOKEN_PATTERN = re.compile(
    r"%x[0-9A-Fa-f]{1,2}|%[A-Za-z0-9]|#|\$|\^|%"
)
PROTECTED_SPAN_PATTERN = re.compile(
    rf"(?:{CONTROL_TOKEN_PATTERN.pattern})|[ \t]{{2,}}|€|£|°"
)
MARKER_PATTERN = re.compile(r"\uE100([0-9A-F]{4})\uE101")


class TranslationIntegrityError(RuntimeError):
    pass


LINGVA_INSTANCES = [
    "https://lingva.lunar.icu",
    "https://translate.dr460nf1r3.org",
    "https://lingva.garudalinux.org",
]


def protect_placeholders(text: str) -> tuple:
    tokens = []

    def _sub(match):
        marker = f"\uE100{len(tokens):04X}\uE101"
        tokens.append((marker, match.group(0)))
        return marker

    protected = PROTECTED_SPAN_PATTERN.sub(_sub, text)
    return protected, tokens


def restore_placeholders(text: str, tokens: list) -> str:
    restored = text
    expected_markers = {marker for marker, _original in tokens}
    found_markers = {match.group(0) for match in MARKER_PATTERN.finditer(restored)}
    if found_markers != expected_markers:
        missing = len(expected_markers - found_markers)
        unexpected = len(found_markers - expected_markers)
        raise TranslationIntegrityError(
            tr("tr.err.markers_changed", missing=missing, unexpected=unexpected)
        )
    for marker, original in tokens:
        if restored.count(marker) != 1:
            raise TranslationIntegrityError(tr("tr.err.marker_count", marker=marker))
        restored = restored.replace(marker, original)
    if MARKER_PATTERN.search(restored):
        raise TranslationIntegrityError(tr("tr.err.marker_unrestored"))
    return restored


def google_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text or text.isspace():
        return text
    params = {"client": "gtx", "sl": source_lang, "tl": target_lang, "dt": "t", "q": text}
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(seg[0] for seg in (data[0] or []) if seg and seg[0])


def lingva_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text or text.isspace():
        return text
    quoted = urllib.parse.quote(text, safe="")
    last_error = None
    for base in LINGVA_INSTANCES:
        url = f"{base}/api/v1/{source_lang}/{target_lang}/{quoted}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        try:
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                if "translation" in data:
                    return data["translation"]
        except Exception as exc:
            last_error = exc
    if last_error:
        raise RuntimeError(tr("tr.err.lingva_unreachable")) from last_error
    return ""


def mymemory_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text or text.isspace():
        return text
    sl = "en" if source_lang == "auto" else source_lang
    params = {"q": text, "langpair": f"{sl}|{target_lang}"}
    url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("responseStatus") == 200:
        return data["responseData"]["translatedText"]
    raise RuntimeError(tr("tr.err.mymemory", status=data.get('responseStatus'), detail=data.get('responseDetails', '')))


import os as _os
from utils import DEEPL_KEY_FILE


def deepl_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text or text.isspace():
        return text

    api_key = _os.environ.get("DEEPL_API_KEY", "").strip()
    if not api_key:
        key_file = DEEPL_KEY_FILE
        if _os.path.isfile(key_file):
            with open(key_file, encoding="utf-8") as f:
                api_key = f.read().strip()
    if not api_key:
        raise RuntimeError(tr("tr.err.deepl_no_key"))

    host = "api-free.deepl.com" if api_key.endswith(":fx") else "api.deepl.com"
    sl   = None if source_lang == "auto" else source_lang.upper()
    tl   = target_lang.upper()
    if tl == "EN":
        tl = "EN-GB"

    body = urllib.parse.urlencode({
        "text": text,
        "target_lang": tl,
        **({"source_lang": sl} if sl else {}),
    }).encode()
    req = urllib.request.Request(
        f"https://{host}/v2/translate",
        data=body,
        headers={
            "Authorization": f"DeepL-Auth-Key {api_key}",
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "DOSTranslationEditor/1.0",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return data["translations"][0]["text"]


def argos_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text or text.isspace():
        return text
    try:
        from argostranslate import translate as _at
    except ImportError:
        raise RuntimeError(tr("tr.err.argos_not_installed"))
    sl = "en" if source_lang == "auto" else source_lang
    installed = _at.get_installed_languages()
    src_lang_obj = next((l for l in installed if l.code == sl), None)
    tgt_lang_obj = next((l for l in installed if l.code == target_lang), None)
    if not src_lang_obj or not tgt_lang_obj:
        raise RuntimeError(tr("tr.err.argos_no_package", src=sl, tgt=target_lang))
    translation = src_lang_obj.get_translation(tgt_lang_obj)
    if not translation:
        raise RuntimeError(tr("tr.err.argos_no_translation", src=sl, tgt=target_lang))
    return translation.translate(text)


TRANSLATION_ENGINES = {
    "Google Translate": google_translate,
    "MyMemory (free)":  mymemory_translate,
    "DeepL (API key)":  deepl_translate,
    "Argos (offline)":  argos_translate,
    "Lingva":           lingva_translate,
}


def translate_string(original_text: str, target_lang: str = "it", source_lang: str = "auto",
                     engine: str = "Google Translate") -> str:
    if not original_text or original_text.isspace():
        return original_text

    leading_match = re.match(r"\s*", original_text)
    trailing_match = re.search(r"\s*$", original_text)
    leading = leading_match.group(0)
    trailing = trailing_match.group(0)
    core_end = len(original_text) - len(trailing) if trailing else len(original_text)
    core = original_text[len(leading):core_end]

    protected, tokens = protect_placeholders(core)
    translated = TRANSLATION_ENGINES.get(engine, google_translate)(
        protected, source_lang=source_lang, target_lang=target_lang
    )
    if not isinstance(translated, str) or not translated:
        raise TranslationIntegrityError(tr("tr.err.no_text"))
    return leading + restore_placeholders(translated, tokens) + trailing


__all__ = [
    "translate_string", "TRANSLATION_ENGINES",
    "CONTROL_TOKEN_PATTERN", "TranslationIntegrityError",
    "protect_placeholders", "restore_placeholders",
]
