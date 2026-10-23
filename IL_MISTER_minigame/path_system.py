import math

from geometry import Y_OFFSET


class PathMixin: # Player path following and path-editing selection helpers.

    def follow_path(self, p): # Advance a player along its assigned manual or tactical path.
        while p.path and math.hypot(p.wx - p.path[0][0], p.wv - p.path[0][1]) < 3.0:
            p.path.pop(0)
        if not p.path:
            p.path = None
            p.new_drift(0.5)
            return False
        p.tx, p.tv = p.path[0]
        p.tag = None
        return True

    def path_player_at(self, mx, my): # Find the eligible player nearest to the supplied path-editing coordinates.
        fx, row, _w = self.screen_to_ground(mx, my)
        best = None
        for p in self.players:
            if p.state in ("out", "leaving", "subout", "subin"):
                continue
            if self.user_team is not None and p.team != self.user_team:
                continue
            dd = math.hypot(p.sx - fx, (p.sy + Y_OFFSET + 5) - row)
            if dd < 14 and (best is None or dd < best[0]):
                best = (dd, p)
        return best[1] if best else None
