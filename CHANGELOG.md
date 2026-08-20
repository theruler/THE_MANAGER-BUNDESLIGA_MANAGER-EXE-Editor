# THE MANAGER - Bundesliga Manager String-Editor ---- Changelog

### New

- Added support for English THE MANAGER packed executables.
- Added JSON export and import for strings.
- Added Changes / Preview for reviewing pending changes before saving.
- Interface and messages are translated into 5 languages. English is used by default.
- All messages and interface text moved to lang_xx.py files.
- Added live language switching without losing the current editor state.
- Added the new String-Editor application branding and icon.
- Persistent CharMap data is stored in `data\\char-mapping.json`.
- `data\\deepl_key.txt` is provided as an empty optional DeepL API key file.
- Added "Starting Year" selector
- Added first version of MANA.DAT editor (standalone)

### Improved

- EXE profile detection now identifies supported executable versions independently of the filename or path.
- Unsupported or unknown executable variants are rejected safely.
- String inventory and pointer handling are more reliable.
- String IDs remain stable when strings are repacked.
- String repacking validates the complete result before applying changes.
- String encoding now respects the available character mapping and rejects unsupported characters instead of silently replacing them.
- Leading, trailing and repeated whitespace is preserved where required.
- Translation handling protects control tokens and relevant formatting data.
- Translate All applies changes as one safe operation and rolls back on failure.
- Font assignment can be determined automatically while still allowing manual Associated Font overrides.
- Font editing validates glyph dimensions, storage limits and aliases before applying changes.
- Font import and export use safer validation and write handling.
- CharMap editing validates byte values and protects the configuration from invalid or damaged data.
- Search and filtering now provide additional string, font and status filters.
- Saving uses safer atomic handling and protects existing files from incomplete writes.
- Unchanged packed EXEPACK executables can be preserved byte-for-byte.
- Unsaved and pending changes are protected when changing files or closing the editor.
- The GUI has been reorganized for a clearer editing workflow.
- Menu and control states now correctly reflect supported/unsupported EXE profiles and pending changes.

### Fixed

- Applying text from the translation field now applies the correct translated text.
- Unsupported Unicode characters are no longer silently replaced with `?`.
- Overlong Fixed Strings are rejected instead of being silently truncated.
- Translation operations no longer leave partial changes after a failed operation.
- Translation handling no longer unnecessarily changes protected whitespace or control data.
- BMP 2.0 MICRO4.FON now uses the correct pointer count.
- Invalid font operations can no longer write beyond the available glyph storage.
- Failed font imports no longer partially modify the current font.
- Saving no longer relies on a non-atomic direct overwrite.
- The editor no longer loses the correct packed EXEPACK state when an executable remains unchanged.
- Unsaved changes are protected when closing or loading another executable.
- Damaged CharMap configuration data is no longer silently treated as an empty configuration.

