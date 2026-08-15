import re
import json
import urllib.parse
import urllib.request

PLACEHOLDER_PATTERN = re.compile(r"%x[0-9A-Fa-f]{1,2}|%\d+|#|%")

LINGVA_INSTANCES = [
    "https://lingva.lunar.icu",
    "https://translate.dr460nf1r3.org",
    "https://lingva.garudalinux.org",
]


def protect_placeholders(text: str) -> tuple:
    tokens = []
    def _sub(match):
        start, end = match.span()
        tokens.append((match.group(0),
                        " " if start > 0 and text[start - 1] == " " else "",
                        " " if end < len(text) and text[end] == " " else ""))
        return f" Zx{len(tokens) - 1}q "
    protected = re.sub(r" {2,}", " ", PLACEHOLDER_PATTERN.sub(_sub, text)).strip()
    return protected, tokens


def restore_placeholders(text: str, tokens: list) -> str:
    def _sub(match):
        idx = int(match.group(1))
        if 0 <= idx < len(tokens):
            token, sb, sa = tokens[idx]
            return f"{sb}{token}{sa}"
        return match.group(0)
    text     = re.sub(r"\s*Zx(\d+)q\s*", lambda m: f"\u0001{m.group(1)}\u0001", text)
    restored = re.sub(r"\u0001(\d+)\u0001", _sub, text)
    restored = re.sub(r" {2,}", " ", restored)
    restored = re.sub(r"\s+([,.;:!?])", r"\1", restored)
    return restored.strip()

def google_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text.strip():
        return ""
    params = {"client": "gtx", "sl": source_lang, "tl": target_lang, "dt": "t", "q": text}
    url = "https://translate.googleapis.com/translate_a/single?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    return "".join(seg[0] for seg in (data[0] or []) if seg and seg[0])

def lingva_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text.strip():
        return ""
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
        raise RuntimeError(
            "All servers are inaccessible (403/503). "
            "Try Google Translate or MyMemory."
        ) from last_error
    return ""

def mymemory_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text.strip():
        return ""
    sl = "en" if source_lang == "auto" else source_lang   # MyMemory non supporta "auto"
    params = {"q": text, "langpair": f"{sl}|{target_lang}"}
    url = "https://api.mymemory.translated.net/get?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))
    if data.get("responseStatus") == 200:
        return data["responseData"]["translatedText"]
    raise RuntimeError(f"MyMemory error {data.get('responseStatus')}: {data.get('responseDetails', '')}")


import os as _os

def deepl_translate(text: str, source_lang: str = "auto", target_lang: str = "it") -> str:
    if not text.strip():
        return ""

    api_key = _os.environ.get("DEEPL_API_KEY", "").strip()
    if not api_key:
        key_file = _os.path.join(_os.path.dirname(__file__), "deepl_key.txt")
        if _os.path.isfile(key_file):
            with open(key_file, encoding="utf-8") as f:
                api_key = f.read().strip()
    if not api_key:
        raise RuntimeError(
            "DeepL key not found.\n"
            "Register for free at https://www.deepl.com/pro#developer\n"
            "Then save the key in deepl_key.txt."
        )

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
    if not text.strip():
        return ""
    try:
        from argostranslate import translate as _at
    except ImportError:
        raise RuntimeError(
            "Argos Translate not installed.\n"
            "Execute: pip install argostranslate\n"
            "and download the language packs."
        )
    sl = "en" if source_lang == "auto" else source_lang
    installed = _at.get_installed_languages()
    src_lang_obj = next((l for l in installed if l.code == sl), None)
    tgt_lang_obj = next((l for l in installed if l.code == target_lang), None)
    if not src_lang_obj or not tgt_lang_obj:
        raise RuntimeError(
            f"Argos package '{sl}→{target_lang}' not installed.\n"
            "Download it with argostranslate.package."
        )
    translation = src_lang_obj.get_translation(tgt_lang_obj)
    if not translation:
        raise RuntimeError(f"No Argos translation available for {sl}→{target_lang}.")
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
    protected, tokens = protect_placeholders(original_text)
    translated = TRANSLATION_ENGINES.get(engine, google_translate)(
        protected, source_lang=source_lang, target_lang=target_lang
    )
    return restore_placeholders(translated, tokens)


__all__ = [
    "translate_string", "TRANSLATION_ENGINES",
    "protect_placeholders", "restore_placeholders",
]
