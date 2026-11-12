# THE MANAGER / Bundesliga Manager Professional / Bundesliga Manager Hattrick String-Editor — Manual

This manual describes the program as an end user sees it. It assumes no programming knowledge.

## 1. What this program does

The editor changes texts, embedded fonts and selected game settings inside supported DOS executables.

It supports two families of games:

- **THE MANAGER / Bundesliga Manager Professional** — sections 4 to 8
- **Bundesliga Manager Hattrick (BMH)** — section 9

The editor can:

- edit game strings
- edit embedded fonts
- export and import strings as JSON
- translate strings
- change the Starting Year
- change the Region between Germany, Italy, France and England
- preview pending changes before saving
- edit the texts stored inside Bundesliga Manager Hattrick executables, together with the text files, fonts and picture folders of that game (section 9)

The Starting Year and the Region Changer are provided for the THE MANAGER profiles.

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

The Bundesliga Manager Hattrick tabs (section 9) are always shown in English, whatever interface language is selected.

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

Bundesliga Manager Hattrick executables use their own DOS extender and need no unpacking. They are loaded the same way and open the tabs described in section 9.

## 5. Starting Year

The Starting Year can be changed directly from the top area of the editor.

The feature is available for all three supported THE MANAGER executable profiles.

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
```

The line shows the kind of string, its font, the old and new length in bytes (Δ is the difference), the check result, and — for strings in a shared block — the block number and the free bytes left in that block after all pending changes.

If a change would no longer fit, the editor reports the problem and does not allow saving until it is solved.

For Bundesliga Manager Hattrick the free space works differently. See section 9.4.

## 9. Bundesliga Manager Hattrick (BMH)

### 9.1 Supported files

The following executables are supported:

| Executable | Language | Version | Text file |
|---|---|---|---|
| `BMH.EXE` | German | V2.24 | `TEXTD.BLK` |
| `BMH_1.EXE` | German | V3.7 | `TEXTD.BLK` |
| `FLTD.EXE` | English | — | `TEXTE.BLK` |

Other versions of the game are not supported: the editor stays locked for the executable-string features, exactly as for any unknown executable.

The text file (`TEXTD.BLK` or `TEXTE.BLK`) is looked for next to the executable. If it is missing, the editor asks you to locate it. If you cancel and the executable is a supported version, you can still edit the strings inside the executable.

Open the executable as described in section 4. The editor recognises it by its structure, so a renamed file is found as well.

### 9.2 The tabs

After loading, the following tabs are shown:

- **BMH EXE Strings** — the texts stored inside the executable (always the first tab on the left)
- **BMH Strings** — the texts of the `.BLK` text file
- **VGA …** — one tab for each picture folder found next to the executable
- **Fonts** — the game fonts `BMH2.FNT` and `BMH3.FNT`, loaded from the `F` folder next to the executable
- **Options** — settings, including the character mapping

The picture and font tabs are only filled when their folders and files are found next to the executable.

### 9.3 BMH EXE Strings

This tab lists the translatable texts that are stored inside the executable: labels, messages and the match commentary.

Each entry shows:

- the number (ID)
- the offset in the file
- the current text

Use **Search** to find text. The search also finds the original text of strings that were already edited.

Tick **Modified only** to see only the strings you changed.

Select a string to open it in the **editing area**:

- every space (0x20) is highlighted in blue, because spaces matter for alignment
- below the text, the editor shows how many bytes the text uses and how many bytes its place offers
- use **Apply** to keep the change and **Discard** to drop it

Nothing is written to the file until you save (section 9.9).

**What is shown**

Only real texts are offered. These are hidden on purpose, because changing them could break the game:

- file names and paths, device names, the version text
- character tables and syllable lists
- control sequences that are not text
- in the English executable also pure punctuation and layout fragments

The German executables offer 175 strings, the English executable 55.

**Special characters**

The game uses the 7-bit German character set. The editor shows its special characters as normal letters: `Ä Ö Ü ä ö ü ß §`.

Characters that the game cannot show cannot be typed. Another character can be assigned to a byte in the **Options** tab (character mapping). Remember that the font must contain that character as well.

A byte that has no letter can be written as `\xNN`, for example `\x1F`.

**Empty texts**

A text cannot be empty. Use a single space if a text must be blank.

### 9.4 Free space and the space bar

The strings in the executable have a fixed place. When a text is longer than its place, the editor writes it somewhere else and corrects the pointer to it. This is done automatically.

The **space bar** in the editing area, aligned to the right, shows the situation. It reads, for example:

`3,912 / 7,967 bytes (49%) - 4,055 free`

- the first number is the space needed by all texts
- the second number is the space available for these strings
- the bar shows how full it is: green below 85%, orange from 85%, red from 95%
- **NOT ENOUGH SPACE** (red) means the texts do not fit. Saving is not possible until you shorten some texts.

**German versions (`BMH.EXE`, `BMH_1.EXE`)**

Besides the space of the strings themselves, these versions contain 4,032 bytes of unused space that the editor uses automatically. The text of the space bar then also shows how much of it is used.

**English version (`FLTD.EXE`)**

This executable contains no unused space that can be used safely. The 55 texts together may not become longer than their original space (2,872 bytes, of which about 14 bytes are free). A text can only become longer if other texts become shorter by the same amount. Translations into longer languages must therefore be abbreviated.

> **Note:** the extra space of the German versions was checked on the structure of the files. It was not yet verified by running the game. Test every modified game before you pass it on.

### 9.5 Match commentary — the template editor

Part of the strings are not plain texts but **templates**. The game builds a different sentence each time from them. There are 22 of them in every executable, for example:

`%x10HE#%c#x %x02RUNS#RUNS#x WITH THE BALL.`

For these strings the **Template editor** replaces the plain text box. It is the same editor that is used for newspaper texts in THE MANAGER.

The check box **Template editor** next to the buttons switches it on (default) or off. When it is off, the template is shown as plain text.

**How a template is built**

- The text is split into **components**. **ROOT** is the whole sentence.
- A **selector** is a place where the game chooses between alternatives. Each alternative is a **branch**. Every branch has its own text box.
- A branch can contain further selectors and **tags**.
- A tag is a placeholder that the game fills in, for example a player name.

**Tags**

| Tag | Badge | Meaning |
|---|---|---|
| `%a` | TEAM A | name of team A |
| `%b` | TEAM B | name of team B |
| `%c` | PLAYER | the player the event is about |
| `%d` | 2ND PLAYER | the second player, for example the one who receives the pass |
| `%f` | DEFENDER | a player of the other team who touches or blocks the ball |
| `%z` | OPPONENT | the opponent in a duel (tackle, foul, dribbling) |
| `%s` | REFEREE | the name of the referee |
| `%0` | METERS | a number, the distance from the goal in meters |
| `%e` | END | ends the text |

**Selectors**

*Random selectors* choose a branch by chance:

| Badge | Branches |
|---|---|
| RANDOM2 … RANDOM5 | 2 to 5 |

*Context selectors* choose according to the situation of the game. They show which alternative belongs to which situation:

| Badge | What it decides | Branches |
|---|---|---|
| SUBJECT | how the player is named | 1 pronoun, 2 name |
| VOLLEY | volley or not | 1 volley, 2 normal |
| PASS TYPE | kind of pass | 1 long or high ball, 2 short pass |
| CARD | kind of card | 1 yellow, 2 red and yellow, 3 red |
| FLIGHT | how the ball travels | 1 and 2 long, 3 high, 4 to the other side |
| CROSS | kind of long pass | 1 cross into the box, 2 long pass |
| BACKWARDS | direction | 1 backwards, 2 nothing |
| DESTINATION | where the ball goes | 1 into, 2 towards or across |
| SHOT SIDE | shot passes the goal | 1 over, 2 past |
| SHOT END | result of the shot | 1 near the goal, 2 out |

> **Note:** the names of the tags and context selectors were derived from the game code and from the texts. Where a meaning is not certain, the badge names what the branch texts say.

**Working with the template editor**

- Click into a text box and change the text of that branch.
- A tag appears in a text box as a coloured badge. Drag a badge from the pool into a text box to insert it.
- Drag a selector badge from the pool into a text box to add a selector with its branches.
- **Ctrl+Z** undoes the last change in a text box.
- Do not type `#` or `%` in a text. They are reserved for the structure.
- Avoid starting a branch (other than the first) with the letter `x`: the editor then adds a space in front to keep the structure valid.

The editor shows the size of the finished template and the space bar updates with every change.

Use **Apply** to accept the template and **Discard** to drop the changes. When you select another string with unapplied changes, the editor asks first.

A template that no longer has a valid structure cannot be applied or saved. The editor shows the reason.

### 9.6 Translation

The translation bar (engine, source language, target language and the translate button) is part of the editing area. Switch on the automatic translation option in the **Tools** menu to show it. It works as in the other parts of the editor.

- Control codes are never sent to the translation engine. `\xNN` sequences and, in the executable, the tags and structure marks of templates stay untouched.
- Templates are translated branch by branch and put together again. The structure cannot be damaged by the translation.
- A text that contains characters the game cannot show, or that the engine returned in a damaged form, is skipped and kept as it was. The result message lists how many strings were skipped.

The **Translate all** entry of the **Tools** menu translates the strings of the tab that is currently shown. A window asks for the range: enter the first and the last ID and select **Start**. Check the result: machine translation of short fragments often needs correction.

### 9.7 Changes preview

The first entry of the **Tools** menu opens the preview of the pending changes. For the executable strings it shows:

- **Summary** — number of changed strings, how many are written to another place, space used, and whether saving is possible
- **Strings** — every changed text with its old and new place, its length in bytes and the old and new text
- **Pointers** — the pointers inside the game that are corrected

The preview is only available when no edit is still waiting for **Apply**.

### 9.8 Text file, fonts and pictures

**BMH Strings** edits the `.BLK` text file with the same tools: search, **Modified only**, **Apply**, **Discard**, translation. The strings of this file are stored one after another, and the editor rebuilds the file when you save. Test the game after you made texts clearly longer.

The **Fonts** tab edits `BMH2.FNT` and `BMH3.FNT`. The **VGA** tabs show the picture folders.

### 9.9 Saving

Select **File → Save As**. The editor saves what has changed, one file after the other, and asks for the file name each time: first fonts, then the text file, then the executable.

- If you choose the original file, the editor asks for confirmation and keeps a backup copy of the original. The confirmation message shows where the backup is.
- If the file was changed by another program since it was loaded, the editor refuses to overwrite it.
- Before the executable is written, the editor checks its own result: the file size is unchanged, reading it back gives exactly your texts, no other pointer is touched, and nothing outside the string space was changed. If the check fails, nothing is written and the message begins with *Self-check failed*.

A saved executable can be loaded again. The editor recognises it as before, and the free space is shown correctly.

### 9.10 Limits at a glance

- Only the three executables of section 9.1 are supported.
- In the English executable the texts must not become longer overall.
- Empty texts are not allowed.
- Characters that the game cannot show cannot be used, unless a mapping and a font character are provided.
- The editor does not start the game. Always test a modified game before using or distributing it.
