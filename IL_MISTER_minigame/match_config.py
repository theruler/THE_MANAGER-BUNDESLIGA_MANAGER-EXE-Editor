"""Static match configuration: speed presets, team defaults and referee/flag/injury tuning."""


SPEEDS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 15.0, 20.0, 30.0, 50.0, 75.0, 100.0] # Available simulation-speed multipliers, including test speeds.
SPEED_DEFAULT = 3 # Index of the default simulation-speed preset in SPEEDS.
SPEED_UNIT = 0.5 # Step used by interface controls when changing simulation speed.
TEAM_NAMES = ["ROSSI", "BLU"] # Default display names for the two teams.
TEAM_COL = [(225, 70, 70), (80, 120, 235)] # Default UI colours for the two teams.
REF_NEAR, CARRY_TOL_T, CARRY_TOL_V = 25.0, 0.35, 2.0 # REF_NEAR: interaction radius; CARRY_TOL_T: carry-time tolerance; CARRY_TOL_V: carry-position tolerance.
FLAG_H = 9.0 # Height of the referee flag in world units.
FLAG_R = 3.0 # Radius used for the referee-flag visual or collision marker.
FLAG_FLY_SPEED = 135.0 # Movement speed used by the referee flag animation.
INJURY_RATE = 0.0042 # Base probability parameter for injuries caused by eligible contacts.
INJURED_SPEED_K = 0.8 # Movement-speed multiplier applied while a player is injured.
