# THE MANAGER / Bundesliga Manager Professional EXE Editor

Release designation: **Release Candidate**

This Python tool safely edits text and embedded fonts in the supported DOS executables.

## Supported versions

- THE MANAGER – Italian version
- THE MANAGER – English version
- Bundesliga Manager Professional / BMP 2.0

Profiles are detected from verified executable structure and content. File names and extensions do not affect detection; unknown or incompatible executables remain unsupported.

## Requirements and start

- Python 3.10 or newer with Tkinter
- Internet access only when an online translation engine is used
- No third-party Python packages are required

Start from this directory with:

```text
python main.py
```

## Basic use

1. Select **Load EXE** and open a supported executable.
2. Find strings with **Search** and the Kind, Font, Change, and Status filters.
3. Edit a string and select **Apply Change**. Leading, trailing, and repeated spaces are preserved.
4. Optional: enable **Automatic translation**, choose Engine/From/To, then use **Apply Translation** or **Translate ALL**.
5. Use **Associated Font** only when a string requires another confirmed embedded CharMap. Pending text must be applied or discarded first.
6. Use the **Font Editor** tab to edit glyph pixels or safe widths, and apply font changes before saving.
7. Use **Export Strings** and **Import Strings** for deterministic UTF-8 `*.strings.json` translation files.
8. Use **Changes / Preview** to inspect logical string, block, pointer, and font changes before saving.
9. Select **Save As...** to write the executable. Saving does not happen automatically after edits or imports.

When the loaded original itself is replaced, the editor verifies that it was not changed externally and creates a byte-identical numbered backup before atomic replacement. Saving to another path is also atomic.

## Safety behavior

- Unknown or structurally incomplete executables are rejected as unsupported.
- String block overflow, fixed-string overlength, unsafe glyph width, and invalid font structures fail closed.
- Unicode that the effective embedded font/CharMap cannot encode is rejected; it is never silently replaced with `?`.
- Tokens, control bytes, whitespace, fingerprints, suffix sharing, and stable `string_id` metadata are checked during string import.
- Any failed import, text transaction, font operation, Repack, or validation leaves the live EXE state unchanged.
- Preview, search, filters, and export are read-only and always operate without reducing the complete internal string inventory.

## EXEPACK limitation

An unchanged packed EXEPACK executable can be saved byte-identically to its loaded source. Once an EXEPACK executable is actually modified, the editor saves the edited, unpacked executable image. The editor does not contain an EXEPACK compressor.

Keep the generated backup and test edited executables in an appropriate DOS environment before regular use.
