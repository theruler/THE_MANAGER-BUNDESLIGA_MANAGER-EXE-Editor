# -*- coding: utf-8 -*-
"""English UI texts for the TORE Editor.

This file is loaded at runtime from ``data/lang/`` next to the program and may
be replaced without rebuilding the editor.  All language files must carry the
identical key space (370 keys) and the identical ``{placeholder}`` names; the
editor falls back to English, and then to the raw key, so a mistake here is
visible rather than silent.  Technical values (file names, extensions, key
names such as ANZAHL/ERBAUER, tool shortcuts, numbers) are deliberately kept.
"""

LANG_NAME = "Deutsch"

TEXTS_DE = {
"m.file": "Datei", "m.edit": "Bearbeiten", "m.sprite": "Sprite", "m.path": "Pfad / Kamera",
"m.view": "Ansicht", "m.data": "Daten", "m.help": "?",
"f.new": "Neue Szene", "f.open": "Öffnen...", "f.save": "Speichern", "f.saveas": "Speichern unter...",
"f.numbered": "Als nummerierte Szene speichern (ANZAHL aktualisieren)...",
"f.gif": "Animiertes GIF exportieren...", "f.pic": "PIC-Ordner...", "f.delete": "Datei löschen...", "f.exit": "Beenden",
"e.selall": "Alle Spieler auswählen", "e.insframe": "Frame einfügen (Kopie)",
"e.delframe": "Aktuellen Frame löschen", "e.clearfilm": "Gesamten Film löschen...",
"e.mirror": "Szene spiegeln (Spielfeldseite + Teamfarben)", "e.swap": "Nur Teamfarben tauschen",
"e.props": "Szeneneigenschaften...",
"s.action": "Aktion hier", "s.run": "Laufen (nur Sprites, bis Filmende)",
"s.auto_here": "Auto-Sprites entlang des Pfads (ab diesem Frame)",
"s.auto_all": "Auto-Sprites entlang des Pfads (ganzer Film)", "s.mirrorpose": "Pose spiegeln (O <-> W)",
"s.lock": "Pose sperren (Animation ab hier löschen)", "s.program": "Posenfolge programmieren...",
"run.dir": "Laufen {d} ({name})",
"p.draw": "Pfad zeichnen (Freihand)", "p.way": "Pfad klicken (Wegpunkte)",
"p.smooth": "Pfad glätten (ab diesem Frame)", "p.even": "Gleichmäßige Geschwindigkeit (ab diesem Frame)",
"p.freeze": "Hier anhalten (Sprite stoppen)", "p.tween": "Position bis Frame interpolieren...",
"p.cam_from": "Kamera folgt gewähltem Sprite (ab diesem Frame)",
"p.cam_all": "Kamera folgt gewähltem Sprite (ganzer Film)",
"p.tween_scroll": "Scrollen bis Frame interpolieren...",
"p.scroll_end": "Aktuelles Scrollen bis Filmende fortsetzen",
"p.colors": "Pfadfarben", "p.colors_reset": "Farben zurücksetzen",
"p.color_title": "Pfadfarbe - {name}",
"col.ball": "Ball", "col.ref": "Schiedsrichter", "col.red": "Rotes Team", "col.blue": "Blaues Team",
"v.path": "Pfad anzeigen", "v.allpaths": "Alle Pfade anzeigen", "v.cam": "Kameraansicht anzeigen (182x96)",
"v.ids": "Sprite-IDs anzeigen", "v.zoom_in": "Spielfeldgröße +", "v.zoom_out": "Spielfeldgröße -",
"v.area_in": "Bereich vergrößern (im Fenster)", "v.area_out": "Bereich verkleinern",
"v.area_reset": "Bereichszoom zurücksetzen (ganzes Feld)",
"d.edit": "Posensätze, Aktionen & Pfadanimation bearbeiten...", "d.reload": "Datendateien neu laden",
"d.kickoff": "Aktuellen Frame als Anstoßaufstellung speichern",
"h.quick": "Kurzhilfe", "h.language": "Sprache",
"tb.select": "Auswahl/Bewegen (V)", "tb.path": "Pfad (D / P)", "tb.pan": "Kamera (H)", "tb.sheet": "Sprite-Tafel",
"undo": "Rückgängig", "redo": "Wiederholen",
"o.rope": "Seilweichheit", "o.pin": "Gewählten Sprite fixieren", "o.movepath": "Ganzen Pfad mit Sprite verschieben",
"o.draw": "Zeichnen", "o.click": "Klicken", "o.persp": "Lauf mit Perspektive", "o.realtime": "Zeichnen in Echtzeit",
"o.speed": "Tempo", "o.pxframe": "px/Frame", "o.duration": "Dauer", "o.frames": "Frames",
"o.smooth": "Kurven glätten", "o.autorun": "Lauf-Sprites automatisch", "o.diag": "Diagonal-Sprites",
"o.follow": "Folgeframes folgen", "o.scrollx": "Scroll X", "o.scrolly": "Y",
"o.camfollow": "Kamera folgt gewähltem Sprite", "o.wholefilm": "ganzer Film",
"sc.label": "Änderungen gelten für:", "sc.frame": "diesen Frame", "sc.end": "diesen + folgende Frames",
"ball.h": "Ballhöhe (px)", "ghost.label": "Geister:",
"chk.path": "Pfad", "chk.allpaths": "Alle Pfade", "chk.cam": "Kamera", "chk.ids": "Sprite-IDs",
"fr.add": "+ Frame", "fr.del": "- Frame", "loop": "Schleife", "fps": "fps",
"fieldsize": "Feldgröße", "zoomarea": "Bereichszoom",
"sel.multi": "STRG+Klick = Mehrfachauswahl von Sprites",
"ot.select": "Optionen Auswahl/Bewegen", "ot.path": "Pfadoptionen", "ot.pan": "Kameraoptionen",
"ghost.none": "Keine", "ghost.prev": "Gewählter: vorheriger Frame",
"ghost.allsel": "Gewählter: alle vorherigen Frames", "ghost.allspr": "Alle Sprites: alle vorherigen Frames",
"tab.poses": "Posen", "tab.actions": "Aktionen", "tab.sound": "Sound",
"tab.poses_sets": "Posensätze", "tab.anim": "Pfadanimation", "tree.sprite": "Sprite",
"tl.legend": "Zeitleiste: grün = läuft, grau = steht, orange = Spezialaktion (gewählter Sprite) | die beiden unteren Marker ziehen, um den Wiedergabe-/Schleifenbereich festzulegen",
"play.all": "Alles abspielen", "play.here": "Ab hier abspielen", "play.stop": "Stopp",
"tl.frame": "Frame {n}", "tl.loop_start": "Schleifenanfang hier setzen", "tl.loop_end": "Schleifenende hier setzen",
"tl.loop_reset": "Schleifenbereich zurücksetzen", "tl.delete": "Frame löschen", "tl.sound": "Sound bei diesem Frame",
"sel.first": "Zuerst einen Sprite auswählen.",
"act.intro": "Wird im aktuellen Frame auf den\ngewählten Spieler angewendet (Teamfarbe automatisch).",
"act.resume": "danach automatisch weiterlaufen",
"act.rundir": "Laufrichtung (Sprites, bis Filmende):",
"act.stand": "stehen", "snd.none": "keiner", "act.go": "Los",
"name.ball_shadow": "Ballschatten", "name.ball": "Ball", "name.goal_l": "Linkes Tor", "name.goal_r": "Rechtes Tor",
"name.red": "Rot", "name.blue": "Blau", "name.ref": "Schiedsrichter", "name.sprite": "Sprite",
"dir.E": "Osten", "dir.NE": "Nordosten", "dir.N": "Norden", "dir.NW": "Nordwesten",
"dir.W": "Westen", "dir.SW": "Südwesten", "dir.S": "Süden", "dir.SE": "Südosten",
"dir.abbr.E": "O", "dir.abbr.NE": "NO", "dir.abbr.N": "N", "dir.abbr.NW": "NW",
"dir.abbr.W": "W", "dir.abbr.SW": "SW", "dir.abbr.S": "S", "dir.abbr.SE": "SO",
"snd.goal": "Torjubel", "snd.whistle": "Schiedsrichterpfiff", "snd.disapproval": "Pfeifkonzert",
"snd.missed": "Enttäuschung nach vergebener Chance",
"pose.select": "Spieler, Schiedsrichter oder Ball auswählen", "pose.current": "Aktuelle Pose: ID {sid}  ({cat})",
"pal.title": "Sprite-Tafel (zum Zuweisen klicken) - Größe änderbar", "pal.hover": "Sprite={sid}  |  Palettenzelle x={x} y={y}",
"pick.title": "Sprite wählen - Klick zum Auswählen, Esc zum Abbrechen",
"pick.info": "Wählbare IDs: {lo}-{hi} (abgedunkelte Zellen sind hier nicht gültig)",
"pick.hover": "Sprite {sid} - zum Auswählen klicken",
"pose.seq_title": "Posenfolge",
"pose.seq_prompt": "Pose-IDs, durch Kommas getrennt.\nSie wiederholen sich zyklisch von diesem Frame bis zum Filmende:",
"cx.sprite_item": "{name}  (Sprite {sid})", "cx.select_under": "Unter dem Cursor auswählen ({n} Sprites)",
"cx.leader": "Zum Leader der Auswahl machen", "cx.remove": "Sprite aus der Gruppe entfernen",
"cx.run": "Laufen (Sprites, bis Filmende)", "cx.auto": "Auto-Sprites entlang des Pfads",
"cx.smooth_here": "Pfad glätten (ab hier)", "cx.even_here": "Gleichmäßige Geschwindigkeit (ab hier)",
"cx.cam_ball": "Kamera folgt diesem Ball", "cx.cam_sprite": "Kamera folgt diesem Sprite",
"cx.tip": "Tipp: Pfad mit Werkzeug D zeichnen oder auf das Feld rechtsklicken",
"cx.pt_title": "Pfadpunkt - Frame {n}", "cx.goto": "Zu Frame {n} gehen",
"cx.straighten": "Begradigen: bis Frame {n} interpolieren...",
"cx.path_to": "Pfad für '{name}' bis hierher (gerade)", "cx.path_n": "Pfad bis hierher in N Frames...",
"cx.path_arrive": "Pfad bis hierher, Ankunft bei Frame...",
"cx.move_here": "Hierher bewegen (nur im gewählten Bereich)",
"cx.draw": "Pfad zeichnen (D)", "cx.way": "Pfad klicken (P)",
"cx.select_first": "Zuerst einen Sprite auswählen (Linksklick)",
"title.frame": "Frame {i}/{n}", "title.new": "(neu)",
"st.overlap": "Überlappende Sprites: {name} ({i}/{n}) - erneut klicken zum Durchschalten",
"st.hover_sprite": "x={x}  y(Sprite)={y}  Sprite={sid}  |  Frame {f}/{n}{extra}",
"st.hover_extra": "  |  {n} Sprites hier: erneut klicken zum Durchschalten, Rechtsklick zum Auswählen",
"st.hover_path": "Pfad-Frame {n} - ziehen, um den Pfad wie ein Seil zu verformen (Umschalt = nur diesen Punkt bewegen, Weichheit in der oberen Leiste)",
"st.hover_idle": "x={x}  y(Sprite)={y}  |  Frame {f}/{n}  |  {hint}",
"st.drag": "x={x}  y(Sprite)={y}  |  Mitte x={cx}  |  Sprite={sid}  |  Frame {f}/{n}",
"st.leader": "Leader der Auswahl: {name}",
"st.draw_first": "Auf einen Sprite drücken, um seinen Pfad zu zeichnen (oder ihn zuerst auswählen).",
"st.way_first": "Zuerst einen Sprite auswählen, dann die Pfadpunkte anklicken.",
"st.mirrored": "Szene gespiegelt (Spielfeldseite + Farben).", "st.swapped": "Szene mit getauschten Teamfarben.",
"st.dest_close": "Das Ziel ist zu nah.", "st.no_next": "Nach diesem Frame ist kein Frame verfügbar.",
"st.baked": "Pfad eingebrannt{persp}: {n} Frames ({a} -> {b}), Länge {length} px{blocked}",
"st.persp": " (Perspektive)", "st.blocked": "; {n} Sprite(s) am Spielfeldrand belassen",
"st.autospr": "Sprites aus der Bewegung neu abgeleitet (Spezialposen bleiben erhalten).",
"st.players_only": "Aktionen gibt es nur für Spieler (rot/blau).",
"st.action_done": "{label}: {frames} Frames ab Frame {f} ({n} Sprite(s))",
"st.even": "Pfad mit konstanter Geschwindigkeit neu verteilt.", "st.cam_focus": "Fokus: {name}",
"st.cam_from": "Kamera-Keyframes erzeugt (ab diesem Frame, geglättet, max. 6 px/Frame).",
"st.cam_all": "Kamera-Keyframes erzeugt (ganzer Film, geglättet, max. 6 px/Frame).",
"st.pic_missing": "Fehlt: {files}", "st.pic_dir": "PIC: {dir}",
"st.no_gfx": "Grafiken nicht gefunden (Datei > PIC-Ordner...)",
"st.assign_first": "Zuerst einen Sprite auswählen, um eine Sprite-ID zuzuweisen.",
"st.data_reloaded": "Datendateien neu geladen", "st.data_reloaded_warn": "Datendateien neu geladen - mit Warnungen",
"st.kick_saved": "Anstoßaufstellung gespeichert in {file}",
"ok": "OK", "close": "Schließen", "save": "Speichern",
"mb.sprite": "Sprite", "mb.error": "Fehler", "mb.limit": "Limit", "mb.delete": "Löschen",
"mb.delete_film": "Film löschen", "mb.unsaved": "Nicht gespeicherte Änderungen", "mb.existing": "Datei existiert bereits",
"mb.kickoff": "Anstoßaufstellung", "mb.datafiles": "Datendateien", "mb.gifexport": "GIF-Export",
"mb.delete_file": "Datei löschen",
"mb.invalid": "Ungültige Werte.", "mb.max_frames": "Maximal {n} Frames.",
"mb.min_frame": "Mindestens ein Frame ist erforderlich.",
"mb.delete_all": "ALLE Frames löschen (nur den aktuellen behalten)?",
"mb.discard": "Änderungen verwerfen?", "mb.new_fail": "Neue Szene kann nicht erstellt werden: {err}",
"mb.save_fail": "Speichern nicht möglich: {err}", "mb.overwrite": "{name} existiert bereits. Überschreiben?",
"mb.perm_delete": "{path} endgültig löschen?",
"mb.kick_confirm": "Sprites, Positionen und Fenster des AKTUELLEN Frames als Anstoßaufstellung\nspeichern, die von 'Neue Szene' verwendet wird?\n\n{file}",
"mb.kick_fail": "Dieser Frame kann nicht gespeichert werden: {err}",
"path.title": "Pfad", "path.n_prompt": "Anzahl der Frames bis zum Ziel:",
"path.arrive_prompt": "Ankunfts-Framenummer (aktuell {n}):",
"tween.title": "Interpolieren", "tween.scroll_title": "Scrollen interpolieren", "tween.prompt": "Letzter Frame (1-{n}):",
"pic.select": "PIC-Ordner wählen (mit 26.VGA, 27.VGA, 29.VGA)",
"open.title": "Szene öffnen", "ft.scene": "Szene", "ft.all": "Alle Dateien",
"pr.author": "Autor (ERBAUER):", "pr.version": "Dateiversion:", "pr.result": "Ergebnis",
"pr.scored": "Tor (T)", "pr.failure": "Fehlschlag (V)", "pr.type": "Art",
"pr.penalty": "Elfmeter (E)", "pr.joke": "Scherz (J)", "pr.none": "Keine",
"num.type": "Art:", "num.variant": "Variante:", "num.number": "Szenennummer:",
"pr.title": "Szeneneigenschaften", "pr.ext": "Dateiendung:  .{ext}",
"num.title": "Als nummerierte Szene speichern", "num.anzahl": "ANZAHL: {an} -> max {vals}",
"num.anzahl_none": "ANZAHL nicht gefunden (wird nicht aktualisiert)",
"kind.T": "Tor (erzielt)", "kind.V": "Vergebene Chance",
"var.none": "Keine", "var.E": "Elfmeter", "var.J": "Scherz",
"gif.content": "Inhalt", "gif.frames": "Frames:", "gif.area": "Bereich:",
"gif.cam": "Kamerafenster (182x96, folgt dem Scrollen)", "gif.full": "ganzes Spielfeld (320x112)",
"gif.size": "Größe und Tempo", "gif.scale": "Skalierung:", "gif.smooth": "weiche Skalierung (verwischt Pixel)",
"gif.fps": "Tempo (fps):", "gif.hold": "Letzten Frame halten (ms):",
"gif.loopforever": "endlos wiederholen (sonst einmal abspielen)",
"gif.quality": "Qualität und Kompression", "gif.preset": "Voreinstellung:",
"gif.colors": "Farben (2-256):", "gif.step": "Nur jeden N-ten Frame verwenden:",
"gif.shared": "gemeinsame Palette (kleinere Datei, stabile Farben)",
"gif.dither": "Dithering (weichere Verläufe, viel größere Datei)", "gif.optimize": "Kodierung optimieren",
"gif.tip": "Tipp: Mit gemeinsamer Palette und ohne Dithering wird von jedem\nFrame nur der geänderte Bereich gespeichert - das ergibt mit Abstand die kleinsten Dateien.",
"gif.calc": "Größe berechnen", "gif.export": "Exportieren...",
"gif.title": "Animiertes GIF exportieren", "gif.type": "GIF-Animation",
"gif.all": "ganzer Film", "gif.loop": "Wiedergabebereich (Schleifenmarker)", "gif.here": "vom aktuellen Frame bis zum Ende",
"gif.p.smallest": "Kleinste Datei", "gif.p.small": "Klein", "gif.p.balanced": "Ausgewogen",
"gif.p.high": "Hohe Qualität", "gif.p.max": "Maximale Qualität", "gif.p.custom": "Benutzerdefiniert",
"gif.cancel": "Abbrechen", "gif.cancelled": "Abgebrochen.",
"gif.info": "{n} Frames (von {total})  |  {w} x {h} px  |  {s} s",
"gif.rendering": "Rendere Frame {i}/{n}", "gif.encoding": "Kodiere Frame {i}/{n}",
"gif.saved": "{name} gespeichert - {n} Frames, {w}x{h}, {size}",
"gif.estimate": "Geschätzte Größe: {size} ({n} Frames, {w}x{h})",
"gif.fail": "Das GIF konnte nicht erstellt werden:\n{err}",
"de.group": "Gruppe:", "de.group_hint": "rot: IDs 0-58 (blau = +59 automatisch) | Schiedsrichter: 118-141 | Ball: 142-145",
"de.name": "Name", "de.ids": "IDs", "de.ids_hint": "z. B.  3,4,5   oder   15-20   oder   43-38 (absteigend möglich)",
"de.sprites": "Sprites",
"de.sprites_hint": "Auf einen Sprite klicken, um einen anderen aus der Sprite-Tafel zu wählen; + zum Hinzufügen; Rechtsklick auf einen Sprite zum Entfernen.\nDas ID-Feld und die Sprites bleiben immer synchron.",
"de.add": "Neu", "de.del": "Löschen", "de.up": "Nach oben", "de.down": "Nach unten",
"de.key": "Schlüssel", "de.label": "Bezeichnung", "de.seq_e": "Folge O", "de.seq_w": "Folge W",
"de.act_hint": "Rote IDs 0-58 (blau +59 automatisch). Sprite anklicken zum Ändern, + zum Hinzufügen, Rechtsklick zum Entfernen. IDs wiederholen, um eine Pose zu halten.\nLeeres W = automatische Spiegelung von O (k -> 58-k), abgedunkelt dargestellt; Bearbeiten macht es zu Ihrer eigenen Folge.\nSteh-/Ruheposen werden hier nicht gesetzt: siehe Reiter 'Pfadanimation' (erster Sprite jeder Richtung).",
"de.single": "Keine Richtung (ein Eintrag, W = O)",
"de.travel": "O/W ist die Fortbewegungsrichtung (z. B. Moonwalk)",
"de.anim_info": "Posen, die ein Sprite selbstständig einnimmt, während er einem Pfad folgt (Pfad zeichnen, Pfad klicken, Auto-Sprites, Menü Laufen). Jede Richtung hat einen RUHE-Sprite (kleines Feld links), gefolgt vom Rest des Laufzyklus: Der Ruhe-Sprite ist der erste Frame des Zyklus und zugleich die Standpose, wenn der Sprite pausiert oder bei 'stehen', mit Blick in die letzte Fortbewegungsrichtung. Das sind weder die durchsuchbaren Listen der 'Posensätze' noch die einmaligen Bewegungen der 'Aktionen'.",
"de.rotation": "Rotation", "de.idle_hint": "linkes Feld = Ruhe\n(erster Sprite des Zyklus)",
"de.footer": "Änderungen bleiben beim Tippen im Speicher; 'In Dateien speichern' schreibt die JSON-Dateien und wendet sie sofort an.",
"de.save": "In Dateien speichern", "de.title": "Posensätze, Aktionen & Pfadanimation bearbeiten",
"de.err_name": "Einen Namen eingeben", "de.err_exists": "'{name}' existiert bereits",
"de.new_set": "Neuer Satz", "de.new_set_n": "Neuer Satz {n}", "de.del_confirm": "'{name}' löschen?",
"de.err_key": "Schlüssel: nur Kleinbuchstaben, Ziffern und _", "de.err_key_exists": "Schlüssel '{key}' existiert bereits",
"de.new_action": "Neue Aktion", "de.del_action": "Aktion '{key}' löschen?",
"de.hint_red": "rote IDs 0-58 angezeigt (blau = +59 automatisch)",
"de.hint_ref": "Schiedsrichter-IDs 118-141 (118-128 nach O, 129-141 nach W)",
"de.hint_ball": "Ball-IDs 142-145", "de.rot_cycle": "Rotationszyklus",
"de.err_idle": "benötigt genau eine Ruhe-ID",
"de.pose_err": "Posensatz '{name}': {err}", "de.action_err": "Aktion '{key}': {err}",
"de.fix": "\n\nBitte korrigieren (oder anderes Element wählen), bevor gespeichert wird.", "de.invalid": "Ungültiger Eintrag",
"de.saved": "{a} und {b} gespeichert",
"de.unsaved": "Posensätze / Aktionen / Pfadanimation wurden geändert, aber nicht in die Dateien gespeichert.\n\nVor dem Schließen speichern?  (Nein = Änderungen verwerfen)",
"save.title": "Szene speichern",
"help.text": """WERKZEUGE (obere Leiste oder Tasten)
 V Auswahl/Bewegen | Pfad: D Freihand zeichnen, P Wegpunkte klicken | H Kamera. Jedes Werkzeug zeigt nur seine eigenen Optionen.

PFAD ZEICHNEN
 D: auf einen Sprite drücken und zeichnen; beim Loslassen wird der Pfad in die folgenden Frames eingebrannt.
   Pfadoptionen: Tempo / feste Dauer / 'wie gezeichnet' (Ihre echte Zeichengeschwindigkeit). Umschalt = gerade Linie.
 P: Punkte anklicken (Enter, Doppelklick oder Rechtsklick beendet). 'Kurven glätten' rundet die Ecken ab.
   'Lauf mit Perspektive' (Klickmodus): Das Tempo folgt der Spielfeldperspektive, sodass ein Sprite für die ferne
   (kurze) und die nahe (lange) Seite gleich lange braucht. 'Tempo' ist dann px/Frame auf der Linie, in der das Spielfeld das Bild ausfüllt (y=39).
 Lauf-Sprites werden automatisch aus der Bewegungsrichtung gewählt (8 Richtungen, beide Farben).

PFAD WIE EIN SEIL BEARBEITEN
 Auswahlwerkzeug: einen beliebigen Punkt des gelben Pfads ziehen; benachbarte Frames folgen sanft
 (Seilweichheit = wie viele Frames mitgezogen werden). Umschalt = nur diesen Punkt bewegen.
 'Gewählten Sprite fixieren' hält den aktuellen Sprite an seinem Platz. 'Ganzen Pfad mit Sprite verschieben': Beim Ziehen des
 Sprites wird der gesamte Pfad unverändert mitverschoben. Menü Pfad: glätten / gleichmäßige Geschwindigkeit / anhalten / Pfadfarben.
 Bei mehreren gewählten Sprites (Pfadwerkzeug) zeigt das Feld 'Pfad' die Pfade aller; nur der Pfad des Leaders (gestrichelt) ist bearbeitbar.

AKTIONEN (Rechtsklick auf einen Spieler, Menü Sprite oder Reiter Aktionen)
 Hechtsprung, Kopfball, Fallrückzieher, Kollisionssturz, Aufstehen, Jubel, Moonwalk - Farbe automatisch.
 O/W = Richtung der Aktion (beim Moonwalk: Fortbewegungsrichtung, die Sprites schauen in die andere Richtung).

KAMERA
 Kamerawerkzeug > 'Kamera folgt gewähltem Sprite' ankreuzen (oder Rechtsklick auf einen Sprite), um die Scroll-Keyframes zu erzeugen;
das Feld ist ausgegraut, wenn kein Sprite gewählt ist, und das Kamerawerkzeug wählt den verfolgten Sprite erneut aus.
 Kameragrenzen: X 0-137, Y 0-15.

MAUS
 Sprite ziehen: bewegen (Strg+Klick oder Rahmenauswahl für Gruppen). Ball und Schatten bewegen sich immer zusammen;
 das Feld 'Ballhöhe' legt ihren Abstand fest. Überlappende Sprites: dieselbe Stelle erneut anklicken zum Durchschalten,
 oder Rechtsklick > 'Unter dem Cursor auswählen'. Kamerawerkzeug: Linksklick wählt ebenfalls einen Sprite.
 Bereichszoom (Leiste 'Bereichszoom', Strg+Mausrad am Zeiger, Bildlaufleisten, Mittelklick-Ziehen): vergrößert innerhalb des Fensters.
 Den cyanfarbenen Kamerarand ziehen: scrollen (auch live während der Wiedergabe). Rahmenauswahl: einen gewählten Sprite anklicken, um ihn zum Leader zu machen.
 Mausrad / Bild auf / Bild ab: Frame wechseln. Zeitleiste: Klick, Rechtsklick; die beiden unteren Marker legen den Wiedergabe-/Schleifenbereich fest.

TASTEN
 Pfeile: 1 px bewegen (Umschalt = 5) | [ ]: vorherige/nächste Pose | Leertaste: ab hier abspielen | Einfg/Entf: Frame
 Strg+Z/Y rückgängig/wiederholen | Strg+S speichern | Strg+A alle Spieler wählen | Strg +/-: Zoom | Esc: abbrechen/abwählen

Eine neue Szene enthält ALLE 27 Sprites in Anstoßaufstellung; Sprites können nie gelöscht werden.

DATENDATEIEN (im Ordner .\\data neben dem Skript, beim Start gelesen)
 tore_pose_sets.json / tore_actions.json / tore_kickoff.json - von Hand oder über das Menü Daten bearbeiten:
 Posensätze, Aktionen & Pfadanimation bearbeiten (Sprite anklicken, um ihn aus der Tafel zu wählen, + zum Hinzufügen) und Aktuellen Frame als Anstoßaufstellung speichern.
 Mit (?) markierte Posensätze sind noch nicht verifiziert.""",
"hint.select": """
Klick: auswählen | Strg+Klick: hinzufügen | Sprite ziehen: bewegen | Pfadpunkt ziehen: Seil ziehen | Leere Fläche ziehen: Rahmenauswahl
Gewählten Sprite anklicken: zum Leader machen | Cyanfarbenen Kamerarand ziehen: scrollen | Rechtsklick: Menü (listet jeden Sprite unter dem Cursor)
Überlappende Sprites: dieselbe Stelle erneut anklicken, um sie durchzuschalten""",
"hint.draw": "\nAuf einen Sprite drücken und seinen Pfad zeichnen; beim Loslassen wird er in die Frames eingebrannt | Umschalt: gerade Linie | Esc: abbrechen",
"hint.way": "\nPunkte anklicken, um einen Pfad anzulegen | Enter / Doppelklick / Rechtsklick: beenden | Rücktaste: Punkt rückgängig | Esc: abbrechen",
"hint.pan": "\nZiehen, um die Kamera zu bewegen (wirkt live während der Wiedergabe) | Sprite anklicken zum Auswählen (erneut klicken zum Durchschalten, falls überlappend)",
}
