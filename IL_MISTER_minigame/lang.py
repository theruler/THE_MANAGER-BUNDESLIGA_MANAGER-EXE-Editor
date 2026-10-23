"""Translation helpers: shared Translator, Note messages and role-label lookups."""

import i18n


T = i18n.Translator(prefix="mister_lang_")
tr = T.tr


class Note: # A translated interface message with optional formatting values.

    def __init__(self, key, warn=False, **kw): # Store a translation key, warning flag, and formatting values.
        self.key, self.warn, self.kw = key, warn, kw

    def text(self): # Translate the stored message key using its formatting values.
        return tr(self.key, **self.kw)


def init_language(code): # Choose the first available translation language from the requested preferences.
    for c in (code, "it", "en"):
        if c and T.set_language(c):
            return c
    return T.current_language()


class _RoleLabels: # Role-label lookup backed by the translation system.

    def __init__(self, prefix): # Store the translation prefix used to resolve role labels.
        self.prefix = prefix

    def get(self, role, default=""): # Translate a role key and return its fallback label if missing.
        return tr(self.prefix + role) if role in ("GK", "DEF", "MID", "FWD") else default

    def __getitem__(self, role): # Resolve a role label through dictionary-style access.
        return tr(self.prefix + role)


ROLE_TAG = _RoleLabels("role.tag.") # Translation-backed labels used to display player roles.
ROLE_LETTER = _RoleLabels("role.letter.")
