# TORE Editor – User Manual

A friendly guide to building and editing scenes: moving players and the ball, drawing paths, choosing poses and controlling the camera window.

---

## 1. The big picture

A **scene** is a short film made of **frames**. Every frame stores:

- the position and pose of every figure (players, referee, ball, ball shadow, goals);
- the **window** – the 182 × 96 area of the 320 × 112 field that the player will actually see on screen.

You edit one frame at a time, or press **Play** to watch the whole film.

**Two ideas to remember**

1. **Scope** (top-left: *Changes apply to*) decides how far an edit reaches: **this frame** only, or **this + following frames**.
2. **Everything can be undone** with `Ctrl+Z` (redo: `Ctrl+Y`).

---

## 2. Quick start (5 minutes)

1. **File → Open…** (`Ctrl+O`) a scene, or **File → New scene** (`Ctrl+N`). If graphics are missing, use **File → PIC folder…** and pick the folder with your `.VGA` files.
2. Click a player to select it (yellow frame).
3. Drag it to move it. Use the arrow keys for 1‑pixel nudges (`Shift` = 5 px).
4. Press **D**, press on the player and **draw a path**. Release: the movement is written into the following frames, with running sprites chosen automatically.
5. Press **Space** to play. Press **Space** again to stop.
6. **File → Save** (`Ctrl+S`).

---

## 3. The screen

| Area | What it does |
| --- | --- |
| **Top bar** | Scope, “ball + shadow together”, ghosts, display toggles, Scroll X/Y of the window |
| **Path & animation bar** | Settings for drawn paths (speed, duration, smoothing, rope softness…) |
| **Camera / selection bar** | “Window locked to ball” and the box‑select leader rule |
| **Tool column (left)** | Select, Draw, Click path, Pan window |
| **Field (centre)** | The scene. The bright rectangle is the visible window |
| **Pose palette (right)** | Poses for the selected figure |
| **Timeline (bottom)** | One cell per frame. Click to jump, right‑click for options. Coloured bars show standing / running / special poses; triangles mark sounds |

---

## 4. The four tools

Switch with the buttons or the keys **V, D, P, H**.

### V – Select / move

- **Click** a figure to select it. **Drag** it to move it.
- **Ctrl+click** adds or removes figures from the selection.
- **Drag on empty field** to draw a selection box (see §6).
- **Drag a dot of the yellow trajectory** to reshape the path (see §5).
- **Drag the cyan window edge** to scroll the window.
- **Shift + drag the ball** changes its **height only**.

### D – Draw path (freehand)

Press on a figure and draw. On release the path is baked into the following frames. Choose how it is timed in the *Path & animation* bar:

- **speed** – pixels per frame (e.g. 3 for a player, 8 for the ball);
- **duration** – the path always takes N frames;
- **as drawn** – keeps the real speed of your hand.

Hold **Shift** for a straight line. **Esc** cancels.

### P – Click path (waypoints)

Click points one after another. Finish with **Enter**, double‑click or right‑click. **Backspace** removes the last point. Tick **smooth curves** to round the corners.

### H – Pan window

Drag anywhere to move the visible window. See §7 for the live mode during playback.

---

## 5. Editing a path like a rope

With the **Select** tool, grab any dot of the yellow trajectory and drag. Neighbouring frames follow smoothly, like a rope.

- **Rope softness** – how many frames are pulled along (higher = softer).
- **Shift** – move only that single point.
- **Pin current frame** – keeps the frame you are looking at exactly where it is.

Clean‑up helpers in **Path / Camera**: *Smooth trajectory*, *Even speed*, *Freeze here*, *Interpolate position to frame…*.

---

## 6. Groups and the leader

You can move several players together:

- **Ctrl+click** figures, **Ctrl+A** (all players), or **drag a box** on the empty field.

The **leader** is the highlighted figure (yellow frame, labelled *leader*). Its trajectory is the one shown, and paths you draw or edit are applied to the whole group.

**Choosing the leader**

- **Box‑select leader** (combo in the bar): after a box selection, the leader is the **North**, **South**, **West** or **East**‑most figure. Changing the value updates the current group immediately.
- **Click** (without dragging) on any selected figure to make it the leader.
- **Right‑click → Make leader of the selection.**

> Tip: pick the figure whose path you care about most – the others keep their relative positions.

---

## 7. The window (camera)

The window is what the player sees. There are three ways to control it.

### 7.1 Manual

Use the **Pan tool (H)**, drag the cyan edge with Select, or type **Scroll X / Y** in the top bar.

### 7.2 Live pan while playing

Start playback, then drag with the Pan tool. The window **does not jump**: it starts from where you see it and follows your mouse in real time. Every frame that plays takes your window position – like recording the camera live.

- Scope *this frame*: each frame is recorded as it passes.
- Scope *this + following*: all following frames take your position at once.
- When you release, frames not yet played keep their original window.
- Undo restores the previous camera.

### 7.3 Window locked to ball

Tick **window locked to ball** (bar, or *Path / Camera* menu). The window stays centred on the ball in **every frame** and updates as you move the ball or press Play. Vertical tracking uses the ball’s shadow (its position on the ground), so the camera doesn’t bob when the ball flies.

- **Pan (H)** or **Scroll X/Y** now shifts the window **relative to the ball** (an offset), also during playback.
- Untick it to release: the window keeps the positions it had.

### 7.4 One‑shot camera tools (Path / Camera menu)

- **Camera follows ball/figure** (from this frame / whole film) – generates smoothed scroll keyframes (max 6 px per frame) for the selected figure or the ball.
- **Interpolate scroll to frame…** – smooth glide between two window positions.
- **Continue current scroll to end of film** – freezes the window.

---

## 8. Poses, actions and running

- **Pose palette** – choose a category, click a pose to apply it (scope applies).
- **Keys `[` and `]`** – previous / next pose.
- **Actions** (right‑click a player, or *Figure → Action here*): Dive, Header, Bicycle kick, Collision fall, Get up – each facing **E** or **W**; team colour is automatic.
- **Run** – sets running sprites for a direction (8 directions) until the end of the film.
- **Auto‑sprites along trajectory** – picks running sprites from the direction of travel. Enabled by default (*auto run sprites*); *diagonal sprites* allows the 4 diagonals.
- **Mirror pose (E ↔ W)** and **Lock pose** (clears animation from here).
- **Program pose sequence…** – type pose IDs separated by commas; they repeat cyclically to the end of the film.

Poses marked **(?)** are still unverified.

---

## 9. Playing and navigating

| Action | How |
| --- | --- |
| Play all / from here | Buttons under the field, or **Space** |
| Speed | *fps* box, *loop* checkbox |
| Next / previous frame | `.` `,` or PgDn / PgUp or mouse wheel |
| First / last frame | `Home` / `End` |
| Insert (copy) / delete frame | `Ins` / `Del` |
| Sounds | Pick a sound for the current frame (marker on the timeline) |

**Ghosts** (top bar) show earlier positions faintly: none, selected figure previous frame, selected figure all previous, or all sprites all previous – great for checking smooth motion.

---

## 10. Menus at a glance

- **File** – New, Open, Save, Save As, *Save as numbered scene (update ANZAHL)*, Export pose sets (JSON), PIC folder, Delete file, Exit.
- **Edit** – Undo/Redo, Select all players, Insert/Delete frame, Delete entire film, **Mirror scene** (field side + team colours), **Swap team colours**, **Scene properties** (author, file version).
- **Figure** – Actions, Run, Auto‑sprites, Mirror/Lock pose, Program sequence.
- **Path / Camera** – drawing tools, path clean‑up, camera helpers, *Window locked to ball*.
- **View** – Show trajectory, Show visible window, Show sprite ids, Zoom (`Ctrl +` / `Ctrl −`).
- **?** – Quick help.

---

## 11. Keyboard shortcuts

| Key | Action | Key | Action |
| --- | --- | --- | --- |
| **V / D / P / H** | Tools | **Space** | Play / stop |
| **Arrows** | Nudge 1 px (Shift = 5) | **\[ \]** | Previous / next pose |
| **Ctrl+Z / Y** | Undo / redo | **Ctrl+S** | Save |
| **Ctrl+Shift+S** | Save As | **Ctrl+O / N** | Open / New |
| **Ctrl+A** | Select all players | **Ctrl +/−** | Zoom |
| **Ins / Del** | Insert / delete frame | **Esc** | Cancel / deselect |
| **Enter** | Finish click path | **Backspace** | Remove last point |

---

## 12. Tips and troubleshooting

- **A move changed too many (or too few) frames** → check the *Changes apply to* setting.
- **The ball moved but its shadow didn’t** → enable *ball + shadow together*. (Shift‑drag moves the ball height only, on purpose.)
- **I can’t move the window by typing Scroll X/Y** → *window locked to ball* is on; the values now set an offset. Untick it for absolute control.
- **The window jumps back after I release during play** → expected: only frames you passed over were recorded. Use scope *this + following* or *Continue current scroll to end of film*.
- **Something went wrong** → `Ctrl+Z`. Edits are undoable, including camera changes.
- **Save often**, and use *Save as numbered scene* when you want a new numbered file.