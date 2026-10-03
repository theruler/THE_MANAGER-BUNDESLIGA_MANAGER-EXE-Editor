# TORE Editor – Feature List and User Manual
Visual editor for **goal scenes** (files `.T`, `.V`, `.TE`, `.TJ`, `.VE`, `.VJ`, `BM-Ed1.x-WK` format) of Bundesliga Manager. A scene is a short “film” of frames in which 22 players, the referee, ball and goals move on the field, with a scrolling camera window and up to 4 sound effects.


## PART 1 – Feature list

**Files and format**
- Open, create, save and save as scenes (`.T/.V` + `E` penalty and `J` joke variants); compatible with `BM-Ed1.0-WK` and `BM-Ed1.3-WK` signatures.
- "Save as numbered scene": saves as `N.ext` and automatically updates the `ANZAHL` file (with `.bak` backup).
- Scene properties: author (ERBAUER), file version, outcome (goal / missed chance), type (penalty / joke / none).
- Delete the scene file from disk.

**Display**
- 320×112 field using original graphics read from `.VGA` files (26 field, 27 sprites, 29 goals); colored placeholders if missing.
- Field zoom (1–6×) and area zoom (up to 12×) with scrollbar, wheel and middle-button panning.
- Camera window (182×96), sprite IDs, paths for the selected sprite or all sprites, "ghosts" of previous frames (4 modes).
- Resizable Sprite sheet window for assigning poses with one click.

**Sprite and frame editing**
- Single and multiple selection (Ctrl+click, rectangle, Ctrl+A) with a "leader"; cycle through overlapping sprites.
- Dragging, arrow keys (1 px, Shift = 5 px), ball + shadow always linked, adjustable ball height.
- Edit scope: this frame only, or this + following frames.
- Add/delete frames (max 256), delete the entire film, Undo/Redo (100 levels).
- Mirror the scene (field side + team colors) or swap colors only.

**Paths (movement)**
- Freehand path (D) or click-to-point path (P), with fixed speed, fixed duration or real-time drawing.
- "Perspective run": speed consistent with the field perspective.
- Smooth curves, straight line with Shift, quick path from the right-click menu (in N frames, or arriving at a specific frame).
- "Rope" path editing: drag one point and nearby frames follow it.
- Smoothing, uniform speed, "Freeze", interpolation between two frames, move the entire path.

**Automatic sprite animation**
- Running sprites chosen automatically from direction (8 directions, both colors, ball rotation).
- Automatic "stand" pose when a sprite stops.
- Special actions (dive, header, bicycle kick, fall, get up, celebration, moonwalk, … configurable) with automatic return to running.
- Manual run in one direction until the end of the film, "stand", programmed pose sequences, mirror pose, lock pose.

**Camera**
- Manual scrolling (by dragging the cyan border or using the X/Y fields), also during playback.
- Camera follows a sprite or the ball (from the current point or over the entire film), with smoothed movement.
- Scroll interpolation and extension to the end of the film.

**Timeline, playback, sounds**
- Timeline with colors for running / standing / special action of the selected sprite.
- Play "all" or "from here", loop, adjustable fps, playback range with two markers.
- 4 sound events (celebration, referee whistle, disapproval, disappointment) assignable to any frame.

**Export and data**
- Export animated GIF (camera or full field, scale, fps, quality preset, shared palette, dithering, etc.) with size estimate.
- Configurable data in JSON: pose sets, actions, running/standing animations, kick-off formation, through the integrated graphical editor.

---

# PART 2 – Manual

## 1. Basic concepts

### 1.1 Scene structure
- A scene has from **1 to 256 frames**.
- Each frame contains **27 sprites**: 11 red, 11 blue, 1 referee, the ball shadow, the ball, the left goal and the right goal. **Sprites cannot be added or deleted**, only moved and changed to a different pose.
- Goals cannot be selected: they follow the ball's x coordinate and are automatically realigned when saving.
- Draw order (which sprite is in front) is automatic, based on vertical position.

### 1.2 Coordinates and limits
| Element | Value |
|---|---|
| Field | 320 × 112 px |
| Camera window | 182 × 96 px |
| Camera scroll | X 0–137, Y 0–15 |
| Player sprite | 12 × 11 px |
| Ball / shadow | 4 px wide |
| Maximum frames | 256 |
| Undo | 100 levels |

The coordinates shown in the status bar are `x` and `y(sprite)`; y is measured from the top of the playable field (35 px offset already subtracted).

### 1.3 Sprite numbering (ID)
| ID | Content |
|---|---|
| 0–58 | Red players (0–33 facing East, 34–58 facing West) |
| 59–117 | Blue players (= red ID + 59) |
| 118–141 | Referee (118–128 facing East, 129–141 facing West) |
| 142–144 | Ball (rotation phases) |
| 145 | Ball shadow |

Checking **View ▸ Show sprite ids** (or "Sprite IDs") displays the ID above each sprite.

### 1.4 Interface colors
- **Yellow**: selected sprite (leader). **Dashed cyan**: other sprites in the group.
- **Solid cyan**: camera window; the field outside the camera is darkened.
- **Path**: colored dots by team (yellow ball, gray referee, red, blue), customizable under *Path / Camera ▸ Paths color*.

## 2. Startup and required files

### 2.1 PIC folder (graphics)
The editor looks for the `PIC` folder (containing `26.VGA`, `27.VGA`, `29.VGA`) next to the opened scene or the executable. If it is not found, colored rectangle placeholders are used and this is reported in the status bar. You can choose it manually with **File ▸ PIC folder…**. If only one file is missing, the status bar indicates which one.

### 2.2 JSON data files (`data` folder, next to the script/executable)
- `tore_actions.json` – actions, running animations and standing animations.
- `tore_pose_sets.json` – pose categories for red/blue, referee and ball.
- `tore_kickoff.json` – kick-off formation used by *New scene*.

They are read at startup. If a file is missing or invalid, a warning appears and the related functions are unavailable (without actions and poses, automatic running and actions cannot be used; without kickoff, a new scene cannot be created). After manual edits use **Data ▸ Reload data files**.

## 3. Interface

From top to bottom:
1. **Menu**: File, Edit, Sprite, Path / Camera, View, Data, ?.
2. **Toolbar**: Select move (V), Path (D / P), Camera (H), Sprite sheet, Undo, Redo.
3. **Options panel**: changes according to the active tool.
4. **"Changes apply to" row**: scope, ball height, ghosts, display switches.
5. **Field** (with area-zoom scrollbar), playback bar, **timeline** and status bar.
6. **Right panel**: sprite list (x, y, pose) and **Poses**, **Actions**, **Sound** tabs.

### 3.1 Scope of changes ("Changes apply to")
- **this frame**: the change applies only to the current frame.
- **this + following frames**: applies from the current frame to the end. Affects movement, pose changes, scrolling and ball height.

Many path, action and running functions still operate "from the current frame onward" (the command name indicates this).

## 4. File

| Command | Shortcut | Description |
|---|---|---|
| New scene | Ctrl+N | Scene with 1 frame and all 27 sprites in kick-off formation (from `tore_kickoff.json`). |
| Open… | Ctrl+O | Opens `.t .v .te .tj .ve .vj`. Checks the signature and that the file is not truncated. |
| Save | Ctrl+S | Saves using the extension defined by the properties (see below). |
| Save As… | Ctrl+Shift+S | Saves as. |
| Save as numbered scene… | – | Saves as `N.extension` in the scene folder and updates `ANZAHL`. |
| Export animated GIF… | – | See §13. |
| PIC folder… | – | Selects the graphics folder. |
| Delete file… | – | **Permanently deletes** the opened scene file from disk. |
| Exit | – | Asks for confirmation if there are unsaved changes. |

**Extension:** determined by *Edit ▸ Scene properties*: `T` = goal, `V` = missed chance, with suffix `E` (penalty) or `J` (joke). If you change the type and save, the file is saved with the new extension (with a confirmation prompt if it already exists).

**Save as numbered scene:** choose type, variant and number. The proposed number is the last known value in `ANZAHL` + 1. If the number exceeds the maximum recorded for that variant, `ANZAHL` (line `MAXSZENE:a|b|c`) is updated and an `ANZAHL.bak` copy is created (only the first time). If `ANZAHL` is not found, the scene is saved but the file is not modified.

The window title shows the file name, an asterisk `*` if there are changes, and the current frame number.

## 5. Edit

| Command | Shortcut | Description |
|---|---|---|
| Undo / Redo | Ctrl+Z / Ctrl+Y | Undo/redo (frames, sounds, author). Does not undo changes to data files. |
| Select all players | Ctrl+A | Selects all players (not referee/ball). |
| Insert frame (copy) | Ins | Duplicates the current frame immediately after it; later sounds are shifted. |
| Delete current frame | Del | Deletes the frame (at least one is required). |
| Delete entire film… | – | Deletes all frames except the current one. |
| Mirror scene | – | Mirrors positions and poses from left to right **and** swaps team colors; swaps the goals; mirrors the camera. |
| Swap team colors only | – | Red ↔ blue without mirroring the field. |
| Scene properties… | – | Author, file version (`BM-Ed1.3-WK` / `1.0`), outcome (T/V) and type (E/J/none). |

## 6. Tools and mouse

Change tools from the toolbar or with **V**, **D**, **P**, **H**. Each tool shows only its own options.

### 6.1 Select move (V)
- **Click** a sprite: selects it. **Ctrl+click**: adds/removes it from the group.
- **Drag a sprite**: moves it (with the entire selected group). Ball and shadow always move together.
- **Drag in empty space**: rectangle selection (Ctrl adds to the selection).
- **Click empty space**: deselects.
- **Overlapping sprites**: click the same spot repeatedly to cycle through them, or right-click ▸ *Select under cursor*.
- **Leader**: in a group, click an already selected sprite (or right-click ▸ *Make leader*) to make it the leader. By default it is the topmost sprite. The leader determines which ID/path is displayed and which pose set appears in the panel.
- **Drag a path point** (yellow/colored): edits the path using the "rope" method (§7.4).
- **Drag the cyan border** of the camera window: moves the scroll.
- **Arrow keys**: move the selected sprite by 1 px (**Shift** = 5 px); the canvas must have focus.

Tool options: *Rope softness* (how many nearby frames are dragged), *Pin selected sprite*, *Move whole path with sprite*.

### 6.2 Path (D / P)
See §7.

### 6.3 Camera (H)
Drag the field to move the scroll (also during playback). Clicking a sprite selects it. Options: Scroll X/Y fields, *Camera follows selected sprite*, *whole film*.

### 6.4 Other mouse commands
- **Wheel**: changes frame. **Ctrl+wheel**: area zoom at the cursor position.
- **Middle button + drag**: pans the zoomed area (Windows/Linux).
- **Right button**: context menu (§6.5).
- **Double-click** (P tool): ends the path.

### 6.5 Context menu (right-click on the field)
- **On a sprite**: list of sprites under the cursor, leader/remove from group, *Action here*, *Run*, mirror/lock pose, auto-sprite, smooth, even speed, freeze, "Camera follows this sprite/ball".
- **On a path point**: go to frame, smooth, even speed, "Straighten: interpolate to frame N…".
- **On an empty point** (with a sprite selected): straight path to here, *Path to here in N frames…*, *Path to here, arriving at frame…*, *Move here* (teleport within the active scope), switch to Draw/Click path.
- In P tool, with a path in progress, right-click completes it.

## 7. Paths: moving sprites

A **path** converts movement in the field into a sequence of positions, one per frame, starting from the current frame. Missing frames are created automatically (up to the 256 limit). Movement applies to the entire selected group (and ball + shadow together), preserving relative offsets.

### 7.1 Common options (Path tool)
| Option | Effect |
|---|---|
| **speed** (px/frame) | The number of frames is derived from the path length. |
| **duration** (frames) | The path occupies exactly N frames. |
| **Realtime drawing** (Draw only) | The real time used to draw becomes the movement timing (uses the current fps). |
| **Perspective run** (Click only) | Compensates for perspective: the sprite takes the same time to cover the far side (short) and near side (long). Here *speed* refers to the y=39 line. |
| **smooth curves** | Rounds corners (Chaikin for Draw, Catmull-Rom for Click). |
| **auto run sprites** | Automatically sets running/standing poses along the path. |
| **diagonal sprites** | Uses 8 directions; if disabled, only 4 (N/S/E/W). |
| **later frames follow** | After the path ends, existing later frames are translated by the same offset to preserve continuity. |

The recommended default speed is 3 px/frame (8 for the ball).

### 7.2 Drawing a path (D – Draw)
1. Press **D**.
2. Select the sprite (or click directly on it).
3. Hold the mouse button and draw; release to "bake" the path into subsequent frames.
4. **Shift** while drawing = straight line. **Esc** = cancel.

### 7.3 Click path (P – Click)
1. Press **P** and select the sprite.
2. Click the transit points. **Backspace** removes the last point, **Esc** cancels.
3. Finish with **Enter**, double-click or right-click.

### 7.4 Editing a path with the "rope" method
With the Select tool, drag any path point: nearby frames are pulled along using a Gaussian curve. *Rope softness* controls how many frames are involved; **Shift** moves only that point. *Pin selected sprite* keeps the current frame fixed, while *Move whole path with sprite* makes dragging the sprite move the entire path. At the end of the drag, poses are recalculated (if *auto run sprites* is enabled) and the camera is realigned.

### 7.5 *Path / Camera* menu commands
| Command | Description |
|---|---|
| Smooth path (from this frame) | Moving average of the moving section. |
| Even speed (from this frame) | Redistributes points at constant speed. |
| Freeze here (stop sprite) | Stops the sprite from here to the end. |
| Interpolate position to frame… | Linear interpolation up to a chosen final frame. |
| Paths color | Changes path colors (ball, referee, red, blue) or restores defaults. |

## 8. Poses, running and actions

### 8.1 Poses tab
Choose a **category** from the drop-down menu and click a thumbnail to assign the pose. It applies to the whole group (poses are automatically converted between red and blue). The scope follows *Changes apply to*. Keys **[** and **]** move to the previous/next pose in the category. Categories come from `tore_pose_sets.json`.

### 8.2 Sprite sheet
The **Sprite sheet** button opens a resizable window with the complete sprite sheet; one click assigns that sprite (by ID) to the selected sprite.

### 8.3 Actions tab
Apply an action from the current frame to the selected player (or the whole group). Team color is automatic. Every action has direction **E** or **W** (arrows `E >` / `< W`); some are "directionless" (*Go*). For the *moonwalk*, the direction indicates the direction of travel, while the sprite faces the other way.

The **then resume running automatically** option resumes running/standing immediately after the action, based on the movement of subsequent frames. If there are not enough frames, they are added.

Available actions are those defined in `tore_actions.json` (by default: dive, header, bicycle kick, collision fall, get up, celebration, moonwalk).

### 8.4 Running directions (compass rose in Actions tab)
Each button (NW, N, NE, W, E, SW, S, SE) applies the running cycle in that direction from the current frame to the end of the film. **stand** sets the standing pose facing the last movement direction. The corresponding cycles apply to the referee and ball.

### 8.5 *Sprite* menu
| Command | Description |
|---|---|
| Action here | Same as the Actions tab (submenu). |
| Run (sprites only, to end of film) | Running cycle in one direction. |
| Auto-sprites along path (from this frame / whole film) | Recalculates poses from actual movement, **preserving special poses** (actions). |
| Mirror pose (E ↔ W) | Mirrors the selected sprite's pose. |
| Lock pose (clear animation from here) | Keeps the current pose fixed until the end. |
| Program pose sequence… | Asks for a list of comma-separated IDs, repeated cyclically from the current frame to the end. |

### 8.6 Ball and shadow
Ball and shadow are always moved together. **Ball height (px)** controls the vertical distance between ball and shadow (positive = ball higher); it applies within the active scope. Ball rotations while running follow the cycle defined in the data.

## 9. Camera

The camera is the 182×96 window shown by the game during the scene.

- **Manual**: *Scroll X/Y* fields (Camera tool), or drag the cyan border / field with the H tool, even during playback.
- **Camera follows selected sprite** (checkbox, or *Path / Camera* menu, or right-click ▸ *Camera follows this sprite*): generates scroll keyframes that follow the sprite with smoothed movement (max 6 px/frame in X, 2 in Y). With **whole film** enabled it starts at frame 1; otherwise from the current frame.
- A **new scene** already starts with the camera following the ball.
- When paths or positions are edited, the following camera is recalculated automatically; if you manually move the scroll, following is disabled.
- **Interpolate scroll to frame…**: linear interpolation of the scroll up to a frame.
- **Continue current scroll to end of film**: copies the current scroll to subsequent frames.

## 10. Timeline, playback and sounds

### 10.1 Playback bar
`|<` first frame · `<` back · **Play all** (from the start of the interval) · **Play from here** (space bar) · `>` forward · `>|` last · **+ Frame** / **– Frame** · **Loop** · **fps** (1–60).

### 10.2 Timeline
- Click or drag on the upper band: goes to the frame.
- Colored band below the numbers (for the selected sprite): **green** = running, **gray** = standing, **orange** = special pose.
- **Range markers** (arrows at the bottom, red = start, purple = end): drag them to define the Play interval and the GIF "play range". Right-click offers *Set loop start/end here* and *Reset loop range*.
- **Colored triangles**: sound events.
- Right-click: menu with playback, range, insert/delete frame and sound.

### 10.3 Sounds
**Sound** tab: choose *none* or one of the four sounds and it will be assigned to the current frame. Each sound can be on only one frame; assigning it elsewhere moves it.

| Sound | Color |
|---|---|
| Goal celebration | green |
| Referee whistle | yellow |
| Disapproval whistles | orange |
| Missed-goal disappointment | blue |

## 11. View

| Item | Effect |
|---|---|
| Show path / Show all paths | Path of the selected sprite / all (except the ball). |
| Show camera view | Camera window and dimmed outside area. |
| Show sprite ids | ID above each sprite. |
| Field size +/– (Ctrl +/–) | Field magnification 1–6×. |
| Zoom area in/out/reset | Zooms a portion of the field (up to 12×). You can also use the *Zoom area* field, the **1:1** button and the scrollbars. |

**Ghosts** (drop-down): *None*, *Selected: previous frame*, *Selected: all previous frames*, *All sprites: all previous frames* – shows transparencies of previous frames to judge smoothness.

## 12. Data

| Command | Description |
|---|---|
| Edit pose sets, actions & path animation… | Graphical data editor (§12.1). |
| Reload data files | Reloads the JSON files after manual edits. |
| Save current frame as kick-off formation | Saves sprites, positions and scroll of the current frame to `tore_kickoff.json`, used by *New scene*. Requires exactly 11 red, 11 blue, referee, shadow, ball and 2 goals. |

### 12.1 Data editor
Three tabs; changes remain in memory until you press **Save to files** (which writes the JSON files and immediately applies the changes). When closing with pending changes, you are asked whether to save.

**Pose sets** – Pose categories for the *red* group (IDs 0–58, blue = +59 automatically), *referee* (118–141) or *ball* (142–145). Select a set on the left, edit *Name* and *IDs* (accepts `3,4,5`, `15-20`, `43-38` descending). The sprite strip is synchronized with the field IDs: click a sprite = choose from the sheet, **+** = add, right-click = remove. Buttons *Add new*, *Delete*, *Up*, *Down*.

**Actions** – List of actions (lowercase key/digits/underscore, label, **E** sequence and **W** sequence). If W is empty it is calculated as the mirror of E (`k → 58−k`). IDs can be repeated to keep a pose for more frames. Options: *No direction (single entry)* and *E/W is the direction of travel*.

**Path animation** – For each direction (and red / referee / ball group), define the **IDLE** pose (left box, before the cycle) and the rest of the running cycle. For the ball there is the *Rotation* cycle. Standing poses are not defined in Actions but here.

## 13. Export animated GIF (File ▸ Export animated GIF…)

| Section | Options |
|---|---|
| **Content** | Frames: entire film / play range / from here onward. Area: camera window (follows the scroll) or full field. |
| **Size and speed** | Scale 1–8×, smooth scaling, fps 1–50, hold last frame (ms), infinite loop. |
| **Quality** | Preset (*Smallest file*, *Small*, *Balanced*, *High quality*, *Maximum quality*, *Custom*), 2–256 colors, every Nth frame, shared palette, dithering, optimization. |

*Calculate size* estimates file size, dimensions and duration without saving; *Export…* asks for the output path. The operation has a progress bar and can be cancelled. Shared palette and no dithering produce the smallest files. Settings are remembered while the editor remains open.

## 14. Keyboard shortcuts

| Key | Action |
|---|---|
| **V / D / P / H** | Select / Draw / Click path / Camera |
| **Space** | Play from here / stop |
| **Arrow keys** | Move 1 px (Shift = 5 px) |
| **PgUp / PgDn**, **, / .**, wheel | Previous / next frame |
| **Home / End** | First / last frame |
| **[ / ]** | Previous / next pose |
| **Ins / Del** | Insert / delete frame |
| **Enter / Backspace / Esc** | Finish path / remove point / cancel or deselect |
| **Ctrl+Z / Ctrl+Y** | Undo / redo |
| **Ctrl+A** | Select all players |
| **Ctrl+N / O / S / Shift+S** | New / open / save / save as |
| **Ctrl + / Ctrl –** | Field zoom |
| **Ctrl+wheel** | Area zoom |

Tool keys and space are ignored while typing in a text field.

## 15. Recommended workflows

**Create a scene from scratch**
1. *File ▸ New scene*. Frame 1 shows the kick-off formation.
2. Set *Scene properties* (outcome, type, author).
3. Select a player, press **D** or **P** and draw the movement: frames are created and running poses are assigned automatically.
4. Repeat for the other sprites; for the ball, select the ball or shadow.
5. Add actions (shot, dive, celebration) from the *Actions* tab on the appropriate frame.
6. Check with *Ghosts* and *Play all*; correct rope paths and use *Smooth* / *Even speed*.
7. Set the camera (*Camera follows…*) and assign sounds to the desired frames.
8. *Save as numbered scene…*

**Reuse a scene for the other team**: open it, *Edit ▸ Mirror scene*, save with another number.

**Shareable preview**: *Export animated GIF…* with *Balanced* preset, *camera window* area.

## 16. Notes and troubleshooting

- **"Graphics not found"** → use *File ▸ PIC folder…* and choose the folder containing `26.VGA`, `27.VGA`, `29.VGA`.
- **"Data files" warning at startup** → check that the `data` folder next to the executable contains the three valid JSON files. With a PyInstaller `--onefile` build, the path must be derived from `sys.executable`, not `__file__`.
- **New scene does not work** → `tore_kickoff.json` is missing or incomplete: use *Save current frame as kick-off formation* on a valid frame.
- **The path stops early** → you reached 256 frames or the edge of the field (sprites are constrained to the field).
- **Arrow keys do not move the sprite** → click the field first to give it focus.
- **ANZAHL not updated** → the file must be in the scene folder or its parent folder; the number must exceed the maximum already registered.
- **Poses do not change** → check that the selected sprite is not a goal and that the scope (*frame* / *this + following*) is the one intended.
- Pose categories marked **(?)** in the data still need verification.
- Changes to the data (JSON) **cannot** be undone with Undo.

## Appendix – Scene file format (summary)
- 12-byte signature: `BM-Ed1.0-WK\0` or `BM-Ed1.3-WK\0`.
- 4 bytes: frame of sound events (255 = none).
- 1 byte: number of frames − 1.
- For each frame, 164 bytes: scroll (X low, Y high) + 27 records of 3 words (x, y, sprite ID) in draw order.
- At the end: length byte + author name in codepage 437, terminated by `\0`.
- Goals have special IDs (1000 left, above 1000 right) and x equal to the ball's x.
