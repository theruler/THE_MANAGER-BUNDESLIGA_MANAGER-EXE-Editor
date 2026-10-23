import os
import time

from lang import tr
from match_config import TEAM_COL, TEAM_NAMES


LOG_DIR = None # Directory for persistent match logs; set once at startup via set_match_log_dir().


def set_match_log_dir(path): # Set the persistent directory used to save match logs.
    global LOG_DIR
    LOG_DIR = path


class MatchLogMixin: # Temporary match messages and persistent event logs.
    def say(self, text, col=(255, 255, 255), secs=4.0): # Display a temporary match-log message.
        self.msgs.append([text, col, secs])
        del self.msgs[:-4]

    def log_event(self, text, col=None, secs=4.0, show=False, team=None): # Record a match event and optionally show it in the on-screen log.
        if col is None:
            col = TEAM_COL[team] if team in (0, 1) else (255, 255, 255)
        try:
            stamp = "%dT %02d'" % (self.half, int(self.minute()))
        except Exception:
            stamp = "--"
        self.mlog.append(("[%s] %s" % (stamp, text), col))
        if show:
            self.msgs.append([text, col, secs])
            del self.msgs[:-4]

    def save_log(self, reason="finale"): # Write the current match log to persistent storage.
        if self.log_saved or not self.mlog or LOG_DIR is None:
            return None
        self.log_saved = True
        bad = '<>:"/\\|?*'
        nm = "%s(%d)-%s(%d)-[%s].log" % (TEAM_NAMES[0], self.score[0], TEAM_NAMES[1], self.score[1], time.strftime("%Y-%m-%d_%H-%M-%S"))
        nm = "".join("_" if c in bad else c for c in nm)
        try:
            os.makedirs(LOG_DIR, exist_ok=True)
            path = os.path.join(LOG_DIR, nm)
            with open(path, "w", encoding="utf-8") as f:
                f.write(tr("log.header", reason=tr("log.reason." + reason)) + "\n")
                f.write("%s %d - %d %s\n" % (TEAM_NAMES[0], self.score[0], self.score[1], TEAM_NAMES[1]))
                f.write(tr("log.forms", fa=self.form_names[0], fb=self.form_names[1], sa=self.subs_used[0], sb=self.subs_used[1]) + "\n")
                f.write("-" * 60 + "\n")
                for k, v in self.stats.items():
                    f.write("%-8s %s / %s\n" % (k, ("%.0f" % v[0]) if k == "poss" else v[0], ("%.0f" % v[1]) if k == "poss" else v[1]))
                f.write("-" * 60 + "\n")
                f.write("\n".join(entry[0] if isinstance(entry, tuple) else entry for entry in self.mlog) + "\n")
            return path
        except OSError:
            return None

    def log_missed(self): # Record a missed or unsuccessful attempt in the match log.
        b = self.ball
        if b.shot_team is not None and b.last is not None and b.last.team == b.shot_team:
            self.log_event(tr("ev.missed", p=b.last.label(), team=TEAM_NAMES[b.last.team]), secs=3, team=b.last.team)

    def log_restart_taker(self, p, kind): # Log which player takes a specified restart.
        if kind in ("throw", "corner", "free", "penalty", "no_gol"):
            self.log_event(tr("ev.taker." + kind, p=p.label(), team=TEAM_NAMES[p.team]), team=p.team)

    def log_move(self, kind, p): # Record a player movement or action event.
        txt = {"volley": lambda: tr("ev.volley"),
               "bicycle": lambda: tr("ev.bicycle"),
               "header_dive": lambda: tr("ev.header_dive"),
               "dive": lambda: tr("ev.dive_of")}[kind]()
        if kind == "header_dive" and (not txt or "ev.header_dive" in txt):
            return
        try:
            txt = txt.format(p=p.label())
        except (KeyError, IndexError, ValueError):
            txt = "%s %s" % (txt, p.label())
        self.log_event(txt, secs=2.5, team=p.team)
