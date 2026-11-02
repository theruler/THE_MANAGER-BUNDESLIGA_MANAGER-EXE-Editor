"""Central configuration for match rules, simulation tuning, and team setup.

Edit this module to tune gameplay without hunting through the implementation files.
Rendering and window-layout constants remain in their respective modules.
"""

# ---- Match speed, teams and referee ----
SPEEDS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 15.0, 20.0, 30.0, 50.0, 75.0, 100.0] # Available simulation-speed multipliers, including test speeds.
SPEED_DEFAULT = 3 # Index of the default simulation-speed preset in SPEEDS.
SPEED_UNIT = 0.5 # Step used by interface controls when changing simulation speed.
SPEED_MAX_CHOICES = [int(v) for v in SPEEDS if v >= 10] # Values of the OPTIONS maximum-speed selector.
TEAM_NAMES = ["ROSSI", "BLU"] # Default display names for the two teams; updated by the selected team data.
TEAM_COL = [(225, 70, 70), (80, 120, 235)] # Default UI colours for the two teams.
REF_NEAR, CARRY_TOL_T, CARRY_TOL_V = 25.0, 0.35, 2.0 # Referee interaction radius and carry-time / carry-position tolerances.
FLAG_H = 9.0 # Height of the referee flag in world units.
FLAG_R = 3.0 # Radius used for the referee-flag visual or collision marker.
FLAG_FLY_SPEED = 135.0 # Movement speed used by the referee flag animation.
INJURED_SPEED_K = 0.8 # Movement-speed multiplier applied while a player is injured.
STEAL_WINDOW = 3.0 # Seconds after a tackle in which the victim can still protest with C.
STEAL_RANGE = 16.0 # Maximum distance between the protesting player and the player who took the ball.
PROTEST_FOUL_P = 0.04 # Chance that the referee punishes the thief after a protest.
PROTEST_BOOK_P = 0.12 # Chance that a protest is booked.
SIM_BOOK_P = 0.15 # Chance that a useless dive is booked.
SIM_BOOK_SPAM = 0.60 # Booking chance when C is pressed again during SIM_COOLDOWN.
SIM_COOLDOWN = 8.0 # Game seconds during which a repeated dive / protest counts as spam.

# ---- Player, ball and goalkeeper physics ----
BALL_GRAVITY = 150.0 # Gravity applied to the ball in world units per second squared.
STANDING_BALL_OFFSET = 4.5 # World units between a stationary player's anchor and the ball at his feet.
PLAYER_SPEED = 52.0 # Base maximum movement speed for outfield players.
TAKER_STALL_SECS = 1.0 # Time without progress before a restart taker switches to unstick mode.
TAKER_UNSTICK_SECS = 2.5 # Duration of the faster restart-taker unstick mode.
TAKER_UNSTICK_K = 1.3 # Speed multiplier while a restart taker is unsticking.
BOX_EXIT_SPEED = 60.0 # Speed used to walk opponents out of a protected penalty area.
DRIBBLE_OFF = 6.0 # Offset between a player position and the ball while dribbling.
REACH_FIRST = 9.0 # Initial reach distance used when evaluating ball control.
PLAYER_CATCH_RADIUS = 4.5 # Normal ground-ball control radius for outfield players.
PLAYER_INTERCEPT_RADIUS = 3.8 # Reduced control radius used by defenders intercepting a pass in flight.
PLAYER_CATCH_HEIGHT = 5.0 # Maximum ball height for normal outfield-player control.
AIR_MIN_Z = 3.0 # Minimum ball height treated as an aerial contest.
THROW_HOLD_Z = 10.0 # Ball height used while a player is holding a throw-in.
THROW_RELEASE_Z = 11.0 # Ball height at which a throw-in releases the ball.
STRIKE_REACH = { # Maximum contact distance by action type: (base, vertical offset, aerial reach).
    "kick": (11.0, -1.0, 9.5),
    "header": (11.0, 4.0, 24.0),
    "bicycle": (13.0, 7.0, 28.0),
    "header_dive": (13.0, 4.0, 18.0),
}
KEEPER_CATCH_RADIUS = 5.5 # Ground-space catch radius for goalkeeper saves.
KEEPER_CATCH_HEIGHT = 10.5 # Maximum ball height for goalkeeper catching attempts.
KEEPER_SAVE_BASE = 0.82 # Save chance for a slow, central shot at an average goalkeeper.
KEEPER_SPEED_K = 0.0017 # Save chance lost per unit of ball speed above 140.
KEEPER_REACH_K = 0.030 # Save chance lost per world unit the goalkeeper has to stretch.
KEEPER_CORNER_K = 0.22 # Extra save-chance penalty for shots near the post.
KEEPER_FAR_START, KEEPER_FAR_FULL = 55.0, 125.0 # Shot distance where goalkeeper foresight starts / is complete.
KEEPER_READ_BONUS = 0.20 # Save chance gained at full foresight.
KEEPER_FREEKICK_READ = 0.65 # Minimum foresight for free-kick shots.
KEEPER_SAVE_MIN, KEEPER_SAVE_MAX = 0.12, 0.93 # Bounds for the final goalkeeper save chance.
FAST_BALL_SPEED = 215.0 # Above this speed outfield players cannot simply take control of the ball.
BLOCK_CHANCE = 0.25 # Probability that a defender touching a hard shot deflects it.
KEEPER_READ_SKILL_RANGE = (0.70, 1.20) # Long-shot reading multiplier at Skill 10 / 99.
PENALTY_READ_BASE = 0.10 # Penalty direction-reading chance at Skill 10.
PENALTY_READ_SKILL = 0.28 # Additional penalty reading chance at Skill 99.

# ---- AI behaviour ----
SAVE_HORIZON = 1.5 # Seconds ahead scanned for a loose ball leaving over a touchline.
SAVE_REACTION = 0.12 # Reaction time before a player starts running for an out ball.
SAVE_SLACK = 0.10 # Maximum lateness still considered reachable.
SAVE_MAX_RUN = 55.0 # Longest run (world units) an AI player attempts for a loose ball.
SAVE_MAX_HEIGHT = 9.0 # Maximum ball height considered reachable at the touchline.
SELECT_LOOKAHEAD = 0.35 # Seconds of ball travel considered when auto-selecting a player.
IDLE_AI = 2.5 # Seconds without manual input before automatic player selection resumes.
MARK_R, MARK_DIST, MAX_MARK = 45.0, 9.0, 2 # Marking search radius, marking offset, maximum defenders per target.
LEASH_U, LEASH_W = 0.08, 0.11 # Maximum extra longitudinal / lateral movement beyond a player's tactical zone.
MARK_MOVE_THRESHOLD = 1.5 # Target movement required before a man-marker updates its destination.
MARK_STICKY_MARGIN = 12.0 # Extra distance allowed to keep an existing marking assignment stable.
GK_DRIBBLE_CHALLENGE_DISTANCE = 28.0 # Maximum goal depth at which the goalkeeper challenges a dribbler.
GK_DRIBBLE_CHALLENGE_RADIUS = 23.0 # Maximum goalkeeper-to-carrier distance for a challenge.
GK_DRIBBLE_CHALLENGE_CHANCE = 0.84 # Base probability that a goalkeeper wins a dribble challenge.
LONG_SHOT_FROM, LONG_SHOT_TO = 105.0, 185.0 # Distance band for long shots.
LONG_SHOT_PROB = 0.14 # Chance per decision of a long shot at Skill 10.
BICYCLE_MIN_Z = 9.0 # Ball height from which a bicycle kick is an option.
DIVE_HEADER_MIN, DIVE_HEADER_MAX = 10.0, 22.0 # Distance band for diving headers.
DIVE_HEADER_REACH = 17.0 # Ball must pass within this distance of the diver.
AERIAL_BACK_MAX = 0.35 # Maximum cosine for a headed pass directed back toward its origin.
AERIAL_CLEAR_DIST = 70.0 # Fallback clearance distance when no teammate is usable.
AERIAL_EDGE = 25.0 # Distance from a touchline inside which headers are not aimed out.
LONG_PASS_FROM, LONG_PASS_FULL = 110.0, 170.0 # Distance range over which long passes gain weighting.
LONG_PASS_BIAS = 40.0 # Skill-scaled bonus / penalty for long passes.
FWD_RUN_BASE, FWD_RUN_SKILL = 0.35, 0.60 # Forward-run chance by player skill.
FWD_LEAD_MIN, FWD_LEAD_MAX = 40.0, 75.0 # Forward run distance ahead of the ball carrier.
FWD_GOAL_MARGIN = 24.0 # Minimum distance forwards keep from the goal line.
FWD_SIDE = 0.22 # Lateral offsets tried when a forward searches for free space.
GK_DRIBBLE_RETRY_SECS = 0.38 # Simulated seconds between failed goalkeeper challenge attempts.

# ---- Player ratings and attribute effects ----
STAT_MIN, STAT_MAX = 10, 99 # Legal range for Fitness, Skill and Form ratings.
DEFAULT_STATS = (55, 55, 55) # Fallback ratings when a player has no database entry.
SPEED_RANGE = (0.88, 1.12) # Running-speed multiplier at Fitness 10 / 99.
POWER_RANGE = (215.0, 320.0) # Maximum kick power at Fitness 10 / 99.
INJURY_RANGE = (1.5, 0.5) # Injury-probability multiplier at Fitness 10 / 99.
SHOT_ERR_MAX, SHOT_ERR_MIN = 0.15, 0.01 # Shot angular error at Skill 10 / 99.
SKILL_RANGE = (0.65, 1.30) # Multiplier applied to base skill for saves, headers and challenges.
TOUCH_RATE = (10.0, 16.0) # Ball-follow rate while dribbling at Skill 10 / 99.
TURN_RATE_MIN, TURN_RATE_FULL = 3.0, 9.0 # Dribble turn-rate thresholds for loose-touch risk.
LOSE_BALL_RATE = 1.4 # Loose-touch probability per second at maximum turn rate and Skill 10.
INTERCEPT_RANGE = (0.80, 1.25) # Interception-radius multiplier at Form 10 / 99.
FLAIR_RANGE = (0.08, 0.60) # Weight for spectacular moves at Skill 10 / 99.
AERIAL_ERR_RANGE = (0.22, 0.03) # Angular error for headed passes at Skill 10 / 99.
KICK_FATIGUE_MAX = 0.40 # Fraction of kick power lost at full fatigue.
ERR_FATIGUE_K = 0.9 # Shot / header angular-error increase at full fatigue.
TOUCH_FATIGUE_K = 0.35 # Dribble ball-follow rate lost at full fatigue.
LOSE_BALL_FATIGUE_K = 1.5 # Loose-touch risk increase at full fatigue.
INTERCEPT_FATIGUE_K = 0.40 # Interception radius lost at full fatigue.
BLOCK_FATIGUE_K = 0.60 # Hard-shot blocking chance lost at full fatigue.
KEEPER_TECH_RANGE = (0.70, 1.30) # Goalkeeper save multiplier at Skill 10 / 99.

# ---- Team behaviour, aggression and fatigue ----
AGON_DEFAULT = 0.5 # Starting aggression level for both teams.
AGON_AI_SWING = 0.15 # Maximum AI-driven aggression movement around the default.
AGON_AI_RATE = 0.04 # AI aggression adjustment per second.
AGON_STEP = 0.05 # Step used by manual aggression controls.
AGON_INJURY_RANGE = (0.35, 1.70) # Injury-probability multiplier at 0 % / 100 % aggression.
AGON_RECOVERY_BONUS = 0.10 # Recovery bonus for a team that has just regained possession.
AGON_CHASE_BONUS = 0.06 # Aggression bonus for chasing a loose ball.
AGON_LINE_PUSH = {"GK": 0.0, "DEF": 0.10, "MID": 0.22, "FWD": 0.16} # Longitudinal shift of the home position as aggression changes.
AGON_INTERCEPT_RANGE = (0.94, 1.08) # Interception multiplier at 0 % / 100 % aggression.
AGON_PACE_RANGE = (0.92, 1.08) # Movement-pace multiplier at 0 % / 100 % aggression.
FAT_RATE_UP = 0.024 # Base fatigue increase rate when aggression is above 50 %.
FAT_RATE_DOWN = 0.030 # Base recovery rate when aggression is below 50 %.
FAT_WORK_REF = 0.5 # Reference player workload used to normalize fatigue.
FAT_GK_WORK = 0.15 # Goalkeeper workload multiplier.
FAT_DEAD = 0.02 # Fatigue threshold below which recovery is complete.
FAT_SHOW = 0.01 # Fatigue threshold below which fatigue is hidden.
FAT_SPEED_MAX = 0.40 # Maximum movement-speed reduction caused by fatigue.
FAT_EXHAUST_FROM = 0.65 # Fatigue level at which the exhausted state begins.
FAT_WALK_K = 0.45 # Minimum walking-speed factor when exhausted.
FAT_INJURY_K = 0.5 # Injury probability increase at full fatigue.
FAT_HALF_RECOVER = (0.15, 0.25) # Fraction of fatigue recovered during half-time.
FAT_BENCH_K = 0.6 # Recovery rate multiplier for benched players.
FAT_FITNESS_RANGE = (1.30, 0.70) # Fatigue-rate multiplier at Fitness 10 / 99.
FAT_FORM_RANGE = (1.15, 0.85) # Fatigue-rate multiplier at Form 10 / 99.
FAT_OFF_STATES = ("out", "leaving", "subin", "subout", "tunnel") # States excluded from fatigue updates.
FAT_SWEAT_ON, FAT_SWEAT_OFF = 0.25, 0.10 # Fatigue levels at which sweat drops appear / disappear.

# ---- Formation and tactical-positioning setup ----
DEFAULT_FORMATION = "4-4-2" # Formation assigned when a team has no explicit choice.
FORMATION_LAYOUTS = (("4-4-2", (4, 4, 2)), ("5-3-2", (5, 3, 2)), ("3-5-2", (3, 5, 2)),
                     ("4-3-3", (4, 3, 3)), ("4-5-1", (4, 5, 1)), ("3-4-3", (3, 4, 3))) # Available outfield line counts.
ROLE_ORDER = ("GK", "DEF", "MID", "FWD") # Order used when sorting or assigning tactical roles.
ROLE_POOLS = {"GK": (0, 2), "DEF": (2, 7), "MID": (7, 15), "FWD": (15, 20)} # Player-index ranges eligible for each tactical role.
ROLE_K = {"GK": 0.0, "DEF": 0.55, "MID": 0.70, "FWD": 0.80} # Longitudinal home-position factors by role.
KEEP_OFF = 22.0 # Minimum distance an outfield player's home position keeps from the ball.
LAT_K = 0.28 # Lateral correction factor used when positioning players relative to the ball.
DEF_LINE_U, FWD_LINE_U = 0.13, 0.45 # Normalized longitudinal positions of the defensive and forward lines.
ZONE_U = {"GK": (0.0, 0.12), "DEF": (0.10, 0.58), "MID": (0.10, 0.92), "FWD": (0.22, 1.0)} # Allowed normalized longitudinal zone by role.
DEF_MIN_U = 0.10 # Minimum normalized forward coordinate allowed for defenders.
WIDE_BONUS = 0.10 # Extra longitudinal zone width given to wide players in broad lines.
LANE_MARGIN = {1: 0.5, 2: 0.30, 3: 0.20, 4: 0.12, 5: 0.09, 6: 0.07} # Normalized lateral spacing margin for each line size.

# ---- Restart positioning and set-piece shape ----
FOOT_PX = {"E": (0.0, -2.0), "W": (0.0, -2.0)} # Screen-pixel offset from the kicker's stand point to the ball ground point.
GK_ADVANCE_U = {"MID": (0.45, 0.70), "FWD": (0.62, 0.90)} # Goal-kick attacking depth by role.
GK_DEF_LINE_U = 0.24 # Goal-kick defensive line depth when nobody needs marking.
GK_THREAT_U = 0.50 # Normalized depth threshold used to identify goal-kick marking threats.
GK_MARK_GOALSIDE = 6.0 # Distance a goal-kick marker keeps on the goal side of his opponent.
GK_TARGET_DIST = 140.0 # Preferred distance to an AI goal-kick receiver.
RESTART_SHIFT_X = 0.55 # Fraction of longitudinal ball offset followed by the team block.
RESTART_SHIFT_V = 0.25 # Fraction of lateral ball offset followed by the team block.
RESTART_SPREAD_W = 1.06 # Lateral widening of the restart formation.
RESTART_JIT_U = 0.035 # Fixed longitudinal jitter per player during a restart.
RESTART_JIT_W = 0.05 # Fixed lateral jitter per player during a restart.
RESTART_MIN_GAP = 15.0 # Minimum teammate distance between restart positions.
RESTART_RELAX_ITERS = 6 # Overlap-relaxation passes for restart positioning.
KICKOFF_WALK_MAX = 30.0 # Maximum wait before a walking kickoff starts anyway.
THROW_PX = {"N": 0.0, "S": 4.0} # Vertical pixel offset of a throw-in taker outside the touchline.

# ---- Goal sequence ----
CELE_KINDS = (("huddle", 2), ("slide", 2), ("lift", 2), ("brawl", 2), ("train", 2), ("dance", 2)) # Celebration types and participant counts.
T_CELE, T_AFTER = 5.6, 2.6 # Celebration duration and post-celebration delay.
GOAL_RETURN_DELAY = 1.5 # Delay before the conceding team starts returning to the centre.
GOAL_FETCH_MAX = 25.0 # Safety limit before kickoff is forced if the ball is not returned.

# Injury probability is split by tackle type and scaled by Fitness, fatigue and aggression.
INJURY_SLIDE_P = 0.035
INJURY_TACKLE_P = 0.012
