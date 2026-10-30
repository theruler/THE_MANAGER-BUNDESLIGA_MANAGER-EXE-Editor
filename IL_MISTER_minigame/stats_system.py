"""Fitness / Skill / Form: per-player ratings (10-99, 10 = worst) and their effect on play.

Ratings come from MANA.DAT (team averages spread over the 20 players, see resources.py) or are random.
Everything here reads the live rating of the player through p.sq (index in the team roster), so a
substituted player automatically plays with his own values.

    Fitness -> running speed, injury proneness, maximum ball range on long kicks
    Skill   -> shooting accuracy, ball keeping on direction changes (p.skill is also rescaled, see apply_skill)
    Form    -> intercepting balls, endurance (tires slower, with Fitness; fatigue itself comes from agonism_system)
"""

import math
import random

from game_utils import clamp

STAT_MIN, STAT_MAX = 10, 99
DEFAULT_STATS = (55, 55, 55) # Used when a player has no rating (should not happen).

SPEED_RANGE = (0.88, 1.12) # Running speed multiplier at Fitness 10 / 99.
POWER_RANGE = (215.0, 320.0) # Maximum kick power (ball range) at Fitness 10 / 99.
INJURY_RANGE = (1.5, 0.5) # Injury probability multiplier at Fitness 10 / 99.
SHOT_ERR_MAX = 0.15 # Angular error (rad, std dev) of a shot at Skill 10; Skill 99 keeps only SHOT_ERR_MIN.
SHOT_ERR_MIN = 0.01
SKILL_RANGE = (0.65, 1.30) # Multiplier applied to the base p.skill (keeper saves, headers, challenges) at Skill 10 / 99.
TOUCH_RATE = (10.0, 16.0) # How tightly the ball follows the dribbler (1/s) at Skill 10 / 99.
TURN_RATE_MIN = 3.0 # Direction change (rad/s) above which a dribbler can lose the ball...
TURN_RATE_FULL = 9.0 # ...and at which the risk is maximal.
LOSE_BALL_RATE = 1.4 # Probability per second of a loose touch at maximum turn rate and Skill 10.
INTERCEPT_RANGE = (0.80, 1.25) # Interception radius multiplier at Form 10 / 99.
FLAIR_RANGE = (0.08, 0.60) # Weight of attempting spectacular moves (bicycle, volley, diving header) at Skill 10 / 99.
AERIAL_ERR_RANGE = (0.22, 0.03) # Angular error (rad, std dev) of a header that is a pass / clearance at Skill 10 / 99.


def lerp(rng, t): # Linear interpolation inside a (low, high) pair.
    return rng[0] + (rng[1] - rng[0]) * t


def norm(v): # 10..99 -> 0..1
    return (clamp(float(v), STAT_MIN, STAT_MAX) - STAT_MIN) / float(STAT_MAX - STAT_MIN)


def clamp_stat(v): # Force a rating into the legal 10..99 range.
    return int(max(STAT_MIN, min(STAT_MAX, round(v))))


def random_team_stats(rng=random): # Random (Fitness, Skill, Form) team average.
    return tuple(rng.randint(STAT_MIN, STAT_MAX) for _ in range(3))


def spread_player_stats(avg, n=20, spread=12.0, rng=random): # n ratings whose mean is exactly the team average.
    avg = clamp_stat(avg)
    vals = [avg + rng.uniform(-spread, spread) for _ in range(n)]
    shift = avg - sum(vals) / n
    vals = [clamp_stat(v + shift) for v in vals]
    diff = avg * n - sum(vals) # Clamping and rounding move the mean: walk it back one point at a time.
    i = 0
    while diff and i < 20 * n:
        j = i % n
        step = 1 if diff > 0 else -1
        if STAT_MIN <= vals[j] + step <= STAT_MAX:
            vals[j] += step
            diff -= step
        i += 1
    return vals


def make_player_stats(avg, n=20, rng=random): # [(fit, skl, frm)] for n players from a team average triple.
    per = [spread_player_stats(a, n, rng=rng) for a in avg]
    return [(per[0][j], per[1][j], per[2][j]) for j in range(n)]


def rating(st): # Single number used to rank players (automatic line-up).
    return sum(st) / 3.0


class StatsMixin: # Effects of Fitness / Skill / Form on the simulation.

    def pstats(self, p): # (fitness, skill, form) of the player currently wearing this shirt.
        try:
            st = self.team_data[p.team]["stats"]
            return st[p.sq] if 0 <= p.sq < len(st) else DEFAULT_STATS
        except (AttributeError, KeyError, IndexError, TypeError):
            return DEFAULT_STATS

    def fatigue(self, p): # 0..~0.28: fraction of speed / kick power lost to fatigue (driven by the agonism bar and the player's own running).
        fn = getattr(self, "agon_fatigue", None)
        return fn(p) if fn else 0.0

    def speed_mod(self, p): # Running speed multiplier.
        return lerp(SPEED_RANGE, norm(self.pstats(p)[0])) * (1.0 - self.fatigue(p))\
            * (self.agon_pace_k(p) * self.agon_exhaust_k(p) if hasattr(self, "agon_pace_k") else 1.0) # Agonism pace and exhaustion (agonism_system).

    def power_cap(self, p): # Maximum kick power (ball range) for this player.
        return lerp(POWER_RANGE, norm(self.pstats(p)[0])) * (1.0 - self.fatigue(p))

    def injury_k(self, p): # Injury probability multiplier: multiply the base chance of an injury to p by this.
        k = lerp(INJURY_RANGE, norm(self.pstats(p)[0]))
        ag = getattr(self, "agon_injury_k", None)
        return k * ag(p) if ag else k # Agonism of both teams (giving and taking).

    def shot_err(self, p): # Angular error (rad) added to every shot.
        return SHOT_ERR_MIN + (SHOT_ERR_MAX - SHOT_ERR_MIN) * (1.0 - norm(self.pstats(p)[1]))

    def touch_rate(self, p): # How tightly the ball follows a dribbler.
        return lerp(TOUCH_RATE, norm(self.pstats(p)[1]))

    def long_k(self, p): # 0 (Skill 99) .. 1 (Skill 10): how much the AI is tempted by long shots and long passes.
        return 1.0 - norm(self.pstats(p)[1])

    def flair_k(self, p): # 0.08 (Skill 10) .. 0.60 (Skill 99): how readily the player tries spectacular moves.
        return lerp(FLAIR_RANGE, norm(self.pstats(p)[1]))

    def aerial_err(self, p): # Angular error (rad) of a header that is not a shot: how precisely he redirects the ball.
        return lerp(AERIAL_ERR_RANGE, norm(self.pstats(p)[1]))

    def intercept_k(self, p): # Interception radius multiplier.
        return lerp(INTERCEPT_RANGE, norm(self.pstats(p)[2]))

    def apply_skill(self, p, st): # Rescale the base p.skill (0..1) used by keepers, headers and challenges.
        base = getattr(p, "skill0", None)
        if base is None:
            base = p.skill0 = p.skill
        p.skill = clamp(base * lerp(SKILL_RANGE, norm(st[1])), 0.05, 0.98)

    def lose_ball_on_turn(self, o, h): # Called every dribble step: a sharp turn can cost a poor dribbler a loose touch.
        pd = getattr(o, "_turn_d", None)
        o._turn_d = (o.dx, o.dv)
        if pd is None or h <= 0.0:
            return False
        sp = math.hypot(o.vx, o.vv)
        if sp < 25.0:
            return False
        dot = clamp(pd[0] * o.dx + pd[1] * o.dv, -1.0, 1.0)
        rate = math.acos(dot) / h
        if rate <= TURN_RATE_MIN:
            return False
        risk = LOSE_BALL_RATE * clamp((rate - TURN_RATE_MIN) / (TURN_RATE_FULL - TURN_RATE_MIN), 0.0, 1.0)
        return random.random() < risk * (1.0 - norm(self.pstats(o)[1])) * h
