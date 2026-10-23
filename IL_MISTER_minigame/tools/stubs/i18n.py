# Test-only stand-in for the project's i18n module (not shipped).
class Translator:
    def __init__(self, prefix=""): self.lang = "it"
    def tr(self, key, **kw): return key + (str(sorted(kw.items())) if kw else "")
    def set_language(self, c): return True
    def current_language(self): return "it"
    def discover_languages(self): return []
    def take_problems(self): return []
