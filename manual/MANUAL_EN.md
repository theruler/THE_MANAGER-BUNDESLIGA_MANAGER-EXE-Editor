# THE MANAGER / Bundesliga Manager Professional String-Editor — Manual

This manual describes the program as an end user sees it. It assumes no programming knowledge.

## 1. What this program does

The editor changes texts, embedded fonts and selected game settings inside supported DOS executables.

Supported game versions:

- THE MANAGER – English version
- THE MANAGER – Italian version
- Bundesliga Manager Professional / BMP 2.0

The editor can:

- edit game strings
- edit embedded fonts
- export and import strings as JSON
- translate strings
- change the Starting Year
- change the Region between Germany, Italy, France and England
- preview pending changes before saving

The editor recognises a game by its internal structure, not by its file name. Renaming an executable does not affect detection.

Unknown or incompatible executables remain unsupported and cannot be edited or saved.

The editor itself never starts the game.

## 2. Starting the program

Start:

`THE MANAGER - Bundesliga Manager String-Editor.exe`

by double-clicking it.

The standalone Windows release does not require Python.

Next to the program there is a `data` folder containing:

- `char-mapping.json` — stores character mappings and confirmed font assignments
- `deepl_key.txt` — optional file for a DeepL API key

Keep the `data` folder next to the program.

If you move the editor executable, move the `data` folder with it.

## 3. Interface language

The editor starts in English.

The interface can be switched between:

- English
- German
- Spanish
- French
- Italian

Use:

**View → Language**

The change takes effect immediately.

The currently loaded executable, selected string, search text, filters and pending editor state remain intact.

Changing the interface language does not modify the loaded game executable.

The selected interface language is not permanently stored, so the next program start uses English again.

Some technical filter values may remain in English because they are internal contract values, for example:

- `Fixed`
- `Suffix-Shared`
- `READ-ONLY`
- `Problems`

## 4. Loading a game executable

Always work with a backup of your original game executable.

Select:

**📁 Choose EXE…**

or:

**File → Open EXE…**

and choose a supported game executable.

If the executable is recognised, its profile is displayed and the editor becomes available.

If the executable is not recognised, the editor stays locked.

The editor does not guess when the executable structure does not match a supported profile.

Both packed EXEPACK files and already-unpacked supported executables can be loaded.

## 5. Starting Year

The Starting Year can be changed directly from the top area of the editor.

The feature is available for all three supported executable profiles.

Enter or select the desired year.

The editor validates the value before applying it.

The supported range is:

`1900–2099`

Changing the Starting Year only changes the editor's in-memory copy of the executable.

Nothing is written to disk until you use **Save As**.

Changing the year back to its original value removes that pending change.

## 6. Region Changer

The Region Changer is available in the top area of the editor.

The available regions are:

- Germany
- Italy
- France
- England

The editor uses the original internal country configuration used by the game executables.

Only these four valid configurations are offered. Internal technical region values are not shown to the user.

Changing the region only changes the in-memory executable.

Nothing is written to disk until you save.

Changing the region back to its original value removes that pending change.

France has been successfully tested in-game with the Region Changer.

The French game executable itself is not currently a separate supported editor profile. The Region Changer changes the country configuration of one of the three supported executable profiles.

## 7. Finding and changing text

The **Strings** area shows the editable text inventory of the loaded game.

Each entry shows information such as:

- number
- offset
- current text

Use **Search** to find text.

The search checks both the current text and the original text, so a string can still be found after it has been edited.

**Filter ▸** provides additional filters for:

- kind
- font
- change state
- status

Select a string to open it in the editing area.

Leading, trailing and repeated spaces are preserved because many game texts use spaces for alignment.

Change the text and select:

**✔ Apply change**

Nothing is written to the game executable at this point.

The modification remains pending inside the editor until you save.

## 8. Making strings longer

Normal strings are stored inside shared string blocks.

Strings in the same block share the available free space.

A short string can therefore be replaced by a longer string as long as the complete block still fits.

The editor displays information similar to:

```text
normal | FLOW.FON | bytes 14→21 (Δ +7) | PASS | Shared B3 rest after all changes: 46 bytes