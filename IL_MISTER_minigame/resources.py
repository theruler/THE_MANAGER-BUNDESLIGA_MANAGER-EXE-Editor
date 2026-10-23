"""Asset discovery, fatal-error screen, picture-directory dialog and team database loading."""

import os
import sys

import pygame

from graphics_system import find_file
from lang import Note, T, tr
from replay_system import DE_TABLE
from stats_system import make_player_stats, random_team_stats, STAT_MAX, STAT_MIN


def find_subdir(parent, name): # Find a named subdirectory beneath a parent folder.
    try:
        for fn in os.listdir(parent):
            p = os.path.join(parent, fn)
            if fn.lower() == name.lower() and os.path.isdir(p):
                return p
    except OSError:
        pass
    return None


def locate_pic(app_dir, hint=None): # Locate the game's PIC asset folder using the supplied path hints.
    cand = []
    if hint:
        cand += [hint, find_subdir(hint, "pic")]
    env = os.environ.get("TORE_PIC")
    if env:
        cand += [env, find_subdir(env, "pic")]
    cwd = os.getcwd()
    for base in (app_dir, cwd, os.path.dirname(app_dir), os.path.dirname(cwd)):
        cand += [find_subdir(base, "pic"), base]
    for d in cand:
        if d and find_file(d, "27"):
            return d
    return None


def find_asset(name, dirs): # Find a named asset across the configured resource directories.
    for d in dirs:
        if d and os.path.isdir(d):
            for fn in os.listdir(d):
                if fn.lower() == name and os.path.isfile(os.path.join(d, fn)):
                    return os.path.join(d, fn)
    return None


def fatal(missing, searched): # Show a startup error in Pygame and print the full details to the console.
    msg = tr("fatal.missing") + "\n  " + "\n  ".join(missing)
    if searched:
        msg += "\n\n" + tr("fatal.searched") + "\n  " + "\n  ".join(searched)
    print(msg, file=sys.stderr)
    try:
        pygame.display.init()
        pygame.font.init()
        screen = pygame.display.set_mode((720, 420))
        pygame.display.set_caption(tr("fatal.title"))
        font = pygame.font.Font(None, 23)
        screen.fill((18, 22, 32))
        screen.blit(font.render(tr("fatal.title"), True, (255, 220, 110)), (20, 18))
        lines = msg.splitlines()
        for i, line in enumerate(lines[:13]):
            screen.blit(font.render(line[:82], True, (230, 235, 242)), (20, 58 + i * 25))
        hint = "Premi un tasto per chiudere" if str(T.current_language()).lower().startswith("it") else "Press any key to close"
        screen.blit(font.render(hint, True, (150, 170, 190)), (20, 380))
        pygame.display.flip()
        while True:
            event = pygame.event.wait()
            if event.type in (pygame.QUIT, pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                break
    except Exception:
        pass
    sys.exit(1)


def ask_pic_dir(start_dir=None): # Show the minimal Pygame folder picker for the directory containing 27.VGA.
    try:
        pygame.display.init()
        pygame.font.init()
        current = os.path.abspath(start_dir if start_dir and os.path.isdir(start_dir) else os.getcwd())
        screen = pygame.display.set_mode((760, 500))
        pygame.display.set_caption(tr("dlg.pick_pic"))
        font = pygame.font.Font(None, 23)
        small = pygame.font.Font(None, 19)
        italian = str(T.current_language()).lower().startswith("it")
        parent_label = ".. (cartella superiore)" if italian else ".. (parent folder)"
        use_label = "Usa cartella" if italian else "Use folder"
        cancel_label = "Annulla" if italian else "Cancel"
        clock = pygame.time.Clock()
        scroll = 0

        while True:
            parent = os.path.dirname(current.rstrip(os.sep))
            entries = []
            if parent and os.path.normcase(parent) != os.path.normcase(current):
                entries.append((parent_label, parent))
            try:
                entries += sorted(
                    [(e.name, e.path) for e in os.scandir(current) if e.is_dir(follow_symlinks=False)],
                    key=lambda item: item[0].casefold())
            except OSError:
                pass
            top, row_h = 122, 25
            visible = 12
            scroll = max(0, min(scroll, len(entries) - visible))
            valid = find_file(current, "27") is not None
            use_rect = pygame.Rect(420, 450, 150, 32)
            cancel_rect = pygame.Rect(585, 450, 150, 32)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return None
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return None
                    if event.key == pygame.K_BACKSPACE:
                        if parent and os.path.normcase(parent) != os.path.normcase(current):
                            current, scroll = parent, 0
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and valid:
                        return current
                    elif event.key in (pygame.K_UP, pygame.K_PAGEUP):
                        scroll = max(0, scroll - (6 if event.key == pygame.K_PAGEUP else 1))
                    elif event.key in (pygame.K_DOWN, pygame.K_PAGEDOWN):
                        scroll = min(max(0, len(entries) - visible), scroll + (6 if event.key == pygame.K_PAGEDOWN else 1))
                elif event.type == pygame.MOUSEWHEEL:
                    scroll = max(0, min(max(0, len(entries) - visible), scroll - event.y * 3))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if use_rect.collidepoint(event.pos) and valid:
                        return current
                    if cancel_rect.collidepoint(event.pos):
                        return None
                    if top <= event.pos[1] < top + visible * row_h:
                        idx = scroll + (event.pos[1] - top) // row_h
                        if idx < len(entries):
                            current, scroll = entries[idx][1], 0

            valid = find_file(current, "27") is not None
            screen.fill((18, 22, 32))
            screen.blit(font.render(tr("dlg.pick_pic"), True, (255, 220, 110)), (18, 14))
            screen.blit(small.render(current[-86:], True, (210, 220, 235)), (18, 52))
            status = "27.VGA trovato" if valid else "27.VGA non trovato: entra nella cartella PIC" 
            if not italian:
                status = "27.VGA found" if valid else "27.VGA not found: open the PIC folder"
            screen.blit(small.render(status, True, (70, 220, 150) if valid else (255, 175, 95)), (18, 82))
            pygame.draw.rect(screen, (32, 38, 52), (12, 112, 736, 324))
            for row, (name, path) in enumerate(entries[scroll:scroll + visible]):
                y = top + row * row_h
                if row % 2 == 0:
                    pygame.draw.rect(screen, (24, 29, 41), (16, y, 728, row_h))
                screen.blit(small.render(name[:95], True, (232, 238, 247)), (22, y + 3))
            pygame.draw.rect(screen, (0, 175, 150) if valid else (58, 63, 72), use_rect)
            pygame.draw.rect(screen, (95, 55, 58), cancel_rect)
            screen.blit(small.render(use_label, True, (12, 20, 26) if valid else (155, 160, 170)), (use_rect.x + 32, use_rect.y + 8))
            screen.blit(small.render(cancel_label, True, (250, 235, 235)), (cancel_rect.x + 48, cancel_rect.y + 8))
            pygame.display.flip()
            clock.tick(30)
    except Exception:
        return None


MANA_HDR = 0x03D8 # Header offset in the MANA binary team database.
MANA_N_TEAMS = 64 # Number of team records in the MANA database layout.
MANA_TEAM_LEN = 543 # Byte length of one MANA team record.
MANA_NAME_LEN = 23 # Byte length reserved for a team name in MANA data.
MANA_PLAYER_LEN = 26 # Byte length reserved for a player record in MANA data.
MANA_N_PLAYERS = 20 # Number of player records stored per team in MANA data.
MANA_STATS = 0x0040 # 64 x 3 bytes: team averages (Fitness, Skill, Form), 10 = worst, 99 = best.


def _mana_str(raw): # Decode a fixed-width team or player name from the MANA data.
    raw = bytes(raw).split(b"\0", 1)[0]
    txt = raw.decode("cp850", "replace")
    return "".join(ch for ch in txt if ch.isprintable()).strip().translate(DE_TABLE)


def team_stats_from(data, i): # Team average (Fitness, Skill, Form) of team i; random for anything missing or outside 10..99.
    a = MANA_STATS + i * 3
    raw = tuple(data[a:a + 3]) if a + 3 <= len(data) else ()
    rnd = random_team_stats()
    return tuple(raw[k] if k < len(raw) and STAT_MIN <= raw[k] <= STAT_MAX else rnd[k] for k in range(3))


def load_mana(path): # Read the MANA binary database and decode its team records.
    with open(path, "rb") as fh:
        data = fh.read()
    teams = []
    for i in range(MANA_N_TEAMS):
        a = MANA_HDR + i * MANA_TEAM_LEN
        if a + MANA_TEAM_LEN > len(data):
            break
        rec = data[a:a + MANA_TEAM_LEN]
        name = _mana_str(rec[:MANA_NAME_LEN])
        if not name:
            continue
        players = [_mana_str(rec[MANA_NAME_LEN + j * MANA_PLAYER_LEN: MANA_NAME_LEN + (j + 1) * MANA_PLAYER_LEN])
                   for j in range(MANA_N_PLAYERS)]
        avg = team_stats_from(data, i)
        teams.append(dict(index=i, name=name, logo=data[i], players=players, avg=avg, stats=make_player_stats(avg, MANA_N_PLAYERS)))
    if not teams:
        raise ValueError(tr("err.no_teams"))
    return teams


def find_mana(dirs, explicit=None): # Locate the MANA data file in the available resource directories.
    if explicit:
        return explicit if os.path.isfile(explicit) else None
    for d in dirs:
        try:
            for fn in os.listdir(d):
                if fn.lower() == "mana.dat" and os.path.isfile(os.path.join(d, fn)):
                    return os.path.join(d, fn)
        except OSError:
            pass
    return None


def default_teams(): # Build the fallback teams used when no external team database is available.
    mk = lambda n: [tr("player.default", n=i + 1) for i in range(MANA_N_PLAYERS)]
    out = []
    for k, key in enumerate(("team.default_home", "team.default_away")):
        avg = random_team_stats()
        out.append(dict(index=k, name=tr(key), logo=-1, players=mk(k), avg=avg, stats=make_player_stats(avg, MANA_N_PLAYERS)))
    return out


def load_teams(dirs, explicit=None): # Load team and player data from the selected database or fallback source.
    path = find_mana(dirs, explicit)
    if path is None:
        return default_teams(), Note("note.mana_missing", True)
    try:
        teams = load_mana(path)
        return teams, Note("note.mana_ok", path=path, n=len(teams))
    except (OSError, ValueError) as ex:
        return default_teams(), Note("note.mana_bad", True, reason=ex)
