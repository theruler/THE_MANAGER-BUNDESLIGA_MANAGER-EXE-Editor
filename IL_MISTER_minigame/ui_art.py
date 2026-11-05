"""Button pictures cut from 3.VGA (inclusive pixel coordinates x1, y1, x2, y2 of the original sheet).

Each name maps to a list of rectangles: the three tab pictures have one per division (SERIE A, B, C).
"""

ART_SHEET = "3" # Stem of the picture file (3.VGA).

ART_RECTS = {
    "tab_table": ((0, 48, 31, 70), (33, 48, 64, 70), (66, 48, 97, 70)), # CLASSIFICA, serie A / B / C
    "tab_cal": ((99, 48, 130, 70), (132, 48, 163, 70), (165, 48, 196, 70)), # CALENDARIO
    "tab_squad": ((0, 72, 31, 94), (33, 72, 64, 94), (66, 72, 97, 94)), # SQUADRA
    "play": ((99, 24, 130, 46),), # GIOCA
    "sim": ((33, 144, 64, 166),), # SIMULA
    "fast": ((66, 96, 97, 118),), # SIMULA VELOCE
    "now": ((0, 24, 31, 46),), # SIMULA SUBITO
    "save": ((66, 120, 97, 142),), # SALVA
    "slot": ((33, 120, 64, 142),), # SLOT
    "back": ((168, 120, 193, 142),), # INDIETRO
    "menu_champ": ((33, 0, 64, 22),), # Main menu: CAMPIONATO
    "menu_quick": ((99, 72, 130, 94),), # PARTITA VELOCE
    "menu_options": ((132, 120, 163, 142),), # OPZIONI
    "menu_exit": ((165, 0, 196, 22),), # USCITA
    "menu_exit_sure": ((0, 31, 31, 53),), # USCITA while "Sei sicuro?" is asked (37.VGA)
}
ART_SHEET_OF = {"menu_exit_sure": "37"} # Pictures that live in another file than ART_SHEET.


def art_size(name): # (width, height) in original pixels.
    x1, y1, x2, y2 = ART_RECTS[name][0]
    return x2 - x1 + 1, y2 - y1 + 1
