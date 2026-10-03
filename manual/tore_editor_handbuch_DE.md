# TORE Editor – Funktionsübersicht und Benutzerhandbuch
Grafischer Editor für **Torszenen** (Dateien `.T`, `.V`, `.TE`, `.TJ`, `.VE`, `.VJ`, Format `BM-Ed1.x-WK`) von Bundesliga Manager. Eine Szene ist ein kurzer „Film“ aus Frames, in denen 22 Spieler, Schiedsrichter, Ball und Tore auf dem Feld bewegt werden, mit einem scrollenden Kamerafenster und bis zu 4 Soundeffekten.


## TEIL 1 – Feature-Liste

**Dateien und Format**
- Szenen (`.T/.V` + Varianten `E` Elfmeter und `J` Scherz) öffnen, erstellen, speichern und mit „Speichern unter“ speichern; kompatibel mit den Signaturen `BM-Ed1.0-WK` und `BM-Ed1.3-WK`.
- „Save as numbered scene“: speichert als `N.ext` und aktualisiert automatisch die Datei `ANZAHL` (mit `.bak`-Sicherung).
- Szeneneigenschaften: Autor (ERBAUER), Dateiversion, Ausgang (Tor / vergebene Chance), Typ (Elfmeter / Scherz / keiner).
- Die Szenendatei von der Festplatte löschen.

**Darstellung**
- Feld 320×112 mit Originalgrafik aus den `.VGA`-Dateien (26 Feld, 27 Sprites, 29 Tore); farbige Platzhalter, wenn Dateien fehlen.
- Feld-Zoom (1–6×) und Bereichs-Zoom (bis 12×) mit Scrollbar, Mausrad und Verschieben mit der mittleren Maustaste.
- Kamerafenster (182×96), Sprite-IDs, Pfade des ausgewählten oder aller Sprites, „Ghosts“ vorheriger Frames (4 Modi).
- Größenveränderbares Sprite-Sheet-Fenster zum Zuweisen von Posen per Mausklick.

**Bearbeitung von Sprites und Frames**
- Einzel- und Mehrfachauswahl (Ctrl+Klick, Rechteck, Ctrl+A) mit einem „Leader“; Durchschalten über überlappende Sprites.
- Ziehen, Pfeiltasten (1 px, Shift = 5 px), Ball + Schatten bleiben immer verbunden, verstellbare Ballhöhe.
- Änderungsbereich: nur dieser Frame oder dieser + folgende Frames.
- Frames hinzufügen/löschen (max. 256), gesamten Film löschen, Undo/Redo (100 Ebenen).
- Szene spiegeln (Feldseite + Teamfarben) oder nur die Farben tauschen.

**Pfade (Bewegung)**
- Freihandpfad (D) oder Pfad über angeklickte Punkte (P), mit fester Geschwindigkeit, fester Dauer oder Echtzeit des Zeichnens.
- „Perspective run“: Geschwindigkeit passend zur Perspektive des Feldes.
- Weiche Kurven, gerade Linie mit Shift, schneller Pfad über das Rechtsklickmenü (in N Frames oder mit Ankunft in einem bestimmten Frame).
- Pfadbearbeitung nach dem „Seil“-Prinzip: einen Punkt ziehen, nahegelegene Frames folgen.
- Glätten, gleichmäßige Geschwindigkeit, „Freeze“, Interpolation zwischen zwei Frames, gesamten Pfad verschieben.

**Automatische Sprite-Animation**
- Lauf-Sprites werden automatisch aus der Richtung gewählt (8 Richtungen, beide Farben, Ballrotation).
- Automatische „Stand“-Pose, wenn ein Sprite anhält.
- Spezialaktionen (Hechtsprung, Kopfball, Fallrückzieher, Sturz, Aufstehen, Jubel, Moonwalk, … konfigurierbar) mit automatischer Rückkehr zum Laufen.
- Manuelles Laufen in eine Richtung bis zum Filmende, „Stand“, programmierte Posenfolgen, Pose spiegeln, Pose sperren.

**Kamera**
- Manuelles Scrollen (durch Ziehen des cyanfarbenen Randes oder über die X/Y-Felder), auch während der Wiedergabe.
- Kamera folgt einem Sprite oder dem Ball (ab hier oder über den gesamten Film) mit weich abgefangener Bewegung.
- Scroll-Interpolation und Fortsetzung bis zum Filmende.

**Timeline, Wiedergabe, Sounds**
- Timeline mit Farben für Laufen / Stehen / Spezialaktion des ausgewählten Sprites.
- Wiedergabe „alles“ oder „ab hier“, Loop, einstellbare fps, Wiedergabebereich mit zwei Markern.
- 4 Soundereignisse (Jubel, Schiedsrichterpfiff, Missbilligung, Enttäuschung) auf jedem Frame platzierbar.

**Export und Daten**
- Animiertes GIF exportieren (Kamera oder gesamtes Feld, Skalierung, fps, Qualitäts-Preset, gemeinsame Palette, Dithering usw.) mit Größenabschätzung.
- Konfigurierbare Daten in JSON: Posen-Sets, Aktionen, Lauf-/Standanimationen, Anstoßaufstellung über den integrierten grafischen Editor.

---

# TEIL 2 – Handbuch

## 1. Grundbegriffe

### 1.1 Aufbau einer Szene
- Eine Szene hat **1 bis 256 Frames**.
- Jeder Frame enthält **27 Sprites**: 11 rote, 11 blaue, 1 Schiedsrichter, den Ballschatten, den Ball, das linke Tor und das rechte Tor. **Sprites können weder hinzugefügt noch gelöscht** werden, sondern nur verschoben und in der Pose geändert.
- Die Tore sind nicht auswählbar: Sie folgen der x-Koordinate des Balls und werden beim Speichern automatisch neu ausgerichtet.
- Die Zeichenreihenfolge (wer vorne liegt) wird automatisch anhand der vertikalen Position bestimmt.

### 1.2 Koordinaten und Grenzen
| Element | Wert |
|---|---|
| Feld | 320 × 112 px |
| Kamerafenster | 182 × 96 px |
| Kamerascroll | X 0–137, Y 0–15 |
| Spieler-Sprite | 12 × 11 px |
| Ball / Schatten | 4 px breit |
| Maximale Frames | 256 |
| Rückgängig | 100 Ebenen |

Die in der Statusleiste angezeigten Koordinaten sind `x` und `y(sprite)`; y wird vom oberen Rand des bespielbaren Feldes aus gemessen (35-px-Offset bereits abgezogen).

### 1.3 Sprite-Nummerierung (ID)
| ID | Inhalt |
|---|---|
| 0–58 | Rote Spieler (0–33 blicken nach Osten, 34–58 nach Westen) |
| 59–117 | Blaue Spieler (= rote ID + 59) |
| 118–141 | Schiedsrichter (118–128 nach Osten, 129–141 nach Westen) |
| 142–144 | Ball (Rotationsphasen) |
| 145 | Ballschatten |

Mit **View ▸ Show sprite ids** (oder „Sprite IDs“) wird die ID über jedem Sprite angezeigt.

### 1.4 Farben der Benutzeroberfläche
- **Gelb**: ausgewähltes Sprite (Leader). **Gestricheltes Cyan**: weitere Sprites der Gruppe.
- **Volles Cyan**: Kamerarahmen; außerhalb der Kamera wird das Feld abgedunkelt.
- **Pfad**: farbige Punkte je Gruppe (gelber Ball, grauer Schiedsrichter, rote, blaue Sprites), anpassbar unter *Path / Camera ▸ Paths color*.

## 2. Start und benötigte Dateien

### 2.1 PIC-Ordner (Grafik)
Der Editor sucht den Ordner `PIC` (mit `26.VGA`, `27.VGA`, `29.VGA`) neben der geöffneten Szene oder der ausführbaren Datei. Wird er nicht gefunden, werden farbige Rechteck-Platzhalter verwendet und dies in der Statusleiste angezeigt. Mit **File ▸ PIC folder…** kann der Ordner manuell ausgewählt werden. Fehlt nur eine Datei, zeigt die Statusleiste an, welche.

### 2.2 JSON-Datendateien (Ordner `data` neben Skript/Executable)
- `tore_actions.json` – Aktionen, Laufanimationen und Standanimationen.
- `tore_pose_sets.json` – Posen-Kategorien für Rot/Blau, Schiedsrichter und Ball.
- `tore_kickoff.json` – Anstoßaufstellung für *New scene*.

Sie werden beim Start eingelesen. Fehlt eine Datei oder ist sie ungültig, erscheint eine Warnung und die entsprechenden Funktionen stehen nicht zur Verfügung (ohne Aktionen und Posen können automatisches Laufen und Aktionen nicht verwendet werden; ohne Kick-off kann keine neue Szene erstellt werden). Nach manuellen Änderungen **Data ▸ Reload data files** verwenden.

## 3. Die Benutzeroberfläche

Von oben nach unten:
1. **Menü**: File, Edit, Sprite, Path / Camera, View, Data, ?.
2. **Symbolleiste**: Select move (V), Path (D / P), Camera (H), Sprite sheet, Undo, Redo.
3. **Options-Bereich**: ändert sich abhängig vom aktiven Werkzeug.
4. **Zeile „Changes apply to“**: Bereich, Ballhöhe, Ghosts, Anzeige-Schalter.
5. **Feld** (mit Scrollbar für den Bereichs-Zoom), Wiedergabeleiste, **Timeline** und Statusleiste.
6. **Rechtes Panel**: Sprite-Liste (x, y, Pose) und die Registerkarten **Poses**, **Actions**, **Sound**.

### 3.1 Änderungsbereich („Changes apply to“)
- **this frame**: Die Änderung gilt nur für den aktuellen Frame.
- **this + following frames**: Gilt vom aktuellen Frame bis zum Ende. Betrifft Verschiebungen, Posenänderungen, Scrollen und Ballhöhe.

Viele Pfad-, Aktions- und Laufbefehle wirken trotzdem „ab dem aktuellen Frame weiter“ (der Name des Befehls weist darauf hin).

## 4. File

| Befehl | Tastenkürzel | Beschreibung |
|---|---|---|
| New scene | Ctrl+N | Szene mit 1 Frame und allen 27 Sprites in der Anstoßaufstellung (aus `tore_kickoff.json`). |
| Open… | Ctrl+O | Öffnet `.t .v .te .tj .ve .vj`. Prüft die Signatur und ob die Datei abgeschnitten ist. |
| Save | Ctrl+S | Speichert mit der durch die Eigenschaften festgelegten Erweiterung (siehe unten). |
| Save As… | Ctrl+Shift+S | Speichert unter neuem Namen. |
| Save as numbered scene… | – | Speichert als `N.extension` im Szenenordner und aktualisiert `ANZAHL`. |
| Export animated GIF… | – | Siehe §13. |
| PIC folder… | – | Wählt den Grafikordner. |
| Delete file… | – | **Löscht** die geöffnete Szenendatei **dauerhaft** von der Festplatte. |
| Exit | – | Fragt nach Bestätigung, wenn ungespeicherte Änderungen vorhanden sind. |

**Erweiterung:** Sie wird durch *Edit ▸ Scene properties* bestimmt: `T` = Tor, `V` = vergebene Chance, mit Suffix `E` (Elfmeter) oder `J` (Scherz). Wenn du den Typ änderst und speicherst, wird die Datei mit der neuen Erweiterung gespeichert (mit Bestätigungsabfrage, falls sie bereits existiert).

**Save as numbered scene:** Typ, Variante und Nummer auswählen. Die vorgeschlagene Nummer ist der letzte bekannte Wert in `ANZAHL` + 1. Wenn die Nummer das für diese Variante bereits registrierte Maximum überschreitet, wird `ANZAHL` (Zeile `MAXSZENE:a|b|c`) aktualisiert und eine Kopie `ANZAHL.bak` erstellt (nur beim ersten Mal). Wird `ANZAHL` nicht gefunden, wird die Szene gespeichert, aber die Datei nicht verändert.

Der Fenstertitel zeigt den Dateinamen, ein Sternchen `*` bei Änderungen und die Nummer des aktuellen Frames.

## 5. Edit

| Befehl | Tastenkürzel | Beschreibung |
|---|---|---|
| Undo / Redo | Ctrl+Z / Ctrl+Y | Rückgängig / wiederholen (Frames, Sounds, Autor). Änderungen an Datendateien werden nicht rückgängig gemacht. |
| Select all players | Ctrl+A | Wählt alle Spieler aus (nicht Schiedsrichter/Ball). |
| Insert frame (copy) | Ins | Dupliziert den aktuellen Frame direkt danach; nachfolgende Sounds werden verschoben. |
| Delete current frame | Del | Löscht den Frame (mindestens einer muss vorhanden sein). |
| Delete entire film… | – | Löscht alle Frames außer dem aktuellen. |
| Mirror scene | – | Spiegelt Positionen und Posen von links nach rechts **und** tauscht die Teamfarben; tauscht die Tore; spiegelt die Kamera. |
| Swap team colors only | – | Rot ↔ Blau, ohne das Feld zu spiegeln. |
| Scene properties… | – | Autor, Dateiversion (`BM-Ed1.3-WK` / `1.0`), Ausgang (T/V) und Typ (E/J/keiner). |

## 6. Werkzeuge und Maus

Werkzeuge über die Symbolleiste oder mit **V**, **D**, **P**, **H** wechseln. Jedes Werkzeug zeigt nur seine eigenen Optionen.

### 6.1 Select move (V)
- **Klick** auf ein Sprite: wählt es aus. **Ctrl+Klick**: fügt es zur Gruppe hinzu / entfernt es.
- **Sprite ziehen**: verschiebt es (mit der gesamten ausgewählten Gruppe). Ball und Schatten bewegen sich immer gemeinsam.
- **In leeren Bereich ziehen**: Rechteckauswahl (Ctrl fügt der Auswahl hinzu).
- **Klick in leeren Bereich**: hebt die Auswahl auf.
- **Überlappende Sprites**: mehrmals an derselben Stelle klicken, um zyklisch durch sie zu wechseln, oder Rechtsklick ▸ *Select under cursor*.
- **Leader**: In einer Gruppe auf ein bereits ausgewähltes Sprite klicken (oder Rechtsklick ▸ *Make leader*), um es zum Leader zu machen. Standardmäßig ist es das oberste Sprite. Der Leader bestimmt, welche ID/welcher Pfad angezeigt wird und welches Pose-Set im Panel erscheint.
- **Pfadpunkt ziehen** (gelb/farbig): bearbeitet den Pfad nach dem „Seil“-Prinzip (§7.4).
- **Cyanfarbenen Kamerarahmen ziehen**: verschiebt den Scroll.
- **Pfeiltasten**: verschieben das ausgewählte Sprite um 1 px (**Shift** = 5 px); das Canvas muss den Fokus haben.

Werkzeugoptionen: *Rope softness* (wie viele nahe Frames mitgezogen werden), *Pin selected sprite*, *Move whole path with sprite*.

### 6.2 Path (D / P)
Siehe §7.

### 6.3 Camera (H)
Feld ziehen, um den Scroll zu verschieben (auch während der Wiedergabe). Ein Klick auf ein Sprite wählt es aus. Optionen: Scroll-X/Y-Felder, *Camera follows selected sprite*, *whole film*.

### 6.4 Weitere Mausbefehle
- **Mausrad**: wechselt den Frame. **Ctrl+Mausrad**: Bereichs-Zoom an der Cursorposition.
- **Mittlere Taste + Ziehen**: verschiebt den vergrößerten Bereich (Windows/Linux).
- **Rechte Maustaste**: Kontextmenü (§6.5).
- **Doppelklick** (Werkzeug P): beendet den Pfad.

### 6.5 Kontextmenü (Rechtsklick auf das Feld)
- **Auf einem Sprite**: Liste der Sprites unter dem Cursor, Leader/aus Gruppe entfernen, *Action here*, *Run*, Pose spiegeln/sperren, Auto-Sprite, Smooth, Even speed, Freeze, „Camera follows this sprite/ball“.
- **Auf einem Pfadpunkt**: zu Frame gehen, Smooth, Even speed, „Straighten: interpolate to frame N…“.
- **Auf einem freien Punkt** (mit ausgewähltem Sprite): gerader Pfad bis hier, *Path to here in N frames…*, *Path to here, arriving at frame…*, *Move here* (Teleport innerhalb des aktiven Bereichs), zu Draw/Click path wechseln.
- Im Werkzeug P beendet ein Rechtsklick bei laufendem Pfad den Pfad.

## 7. Pfade: Sprites bewegen

Ein **Pfad** wandelt eine Bewegung im Feld in eine Folge von Positionen um, eine pro Frame, beginnend mit dem aktuellen Frame. Fehlende Frames werden automatisch erzeugt (bis zum Limit von 256). Die Bewegung gilt für die gesamte ausgewählte Gruppe (sowie Ball + Schatten zusammen), wobei die relativen Abstände erhalten bleiben.

### 7.1 Gemeinsame Optionen (Werkzeug Path)
| Option | Wirkung |
|---|---|
| **speed** (px/frame) | Die Anzahl der Frames wird aus der Pfadlänge abgeleitet. |
| **duration** (frames) | Der Pfad belegt genau N Frames. |
| **Realtime drawing** (nur Draw) | Die reale Zeit des Zeichnens bestimmt das Bewegungstempo (verwendet die aktuellen fps). |
| **Perspective run** (nur Click) | Gleicht die Perspektive aus: Für die ferne Seite (kurz) und die nahe Seite (lang) wird dieselbe Zeit benötigt. Hier bezieht sich *speed* auf die Linie y=39. |
| **smooth curves** | Rundet Ecken ab (Chaikin bei Draw, Catmull-Rom bei Click). |
| **auto run sprites** | Setzt automatisch Lauf-/Standposen entlang des Pfades. |
| **diagonal sprites** | Verwendet 8 Richtungen; deaktiviert nur 4 (N/S/E/W). |
| **later frames follow** | Nach Ende des Pfades werden bereits vorhandene spätere Frames um denselben Offset verschoben, um die Kontinuität zu erhalten. |

Die empfohlene Standardgeschwindigkeit beträgt 3 px/frame (8 für den Ball).

### 7.2 Einen Pfad zeichnen (D – Draw)
1. **D** drücken.
2. Sprite auswählen (oder direkt darauf klicken).
3. Maustaste gedrückt halten und zeichnen; loslassen, um den Pfad in die folgenden Frames zu „backen“.
4. **Shift** beim Zeichnen = gerade Linie. **Esc** = abbrechen.

### 7.3 Pfad über Punkte (P – Click)
1. **P** drücken und Sprite auswählen.
2. Übergangspunkte anklicken. **Backspace** entfernt den letzten Punkt, **Esc** bricht ab.
3. Mit **Enter**, Doppelklick oder Rechtsklick beenden.

### 7.4 Einen Pfad nach dem „Seil“-Prinzip bearbeiten
Mit dem Select-Werkzeug einen beliebigen Pfadpunkt ziehen: Nahe Frames werden entlang einer Gaußkurve mitgezogen. *Rope softness* bestimmt, wie viele Frames einbezogen werden; **Shift** verschiebt nur diesen Punkt. *Pin selected sprite* hält den aktuellen Frame fest, während *Move whole path with sprite* dafür sorgt, dass das Ziehen des Sprites den gesamten Pfad verschiebt. Am Ende des Ziehens werden die Posen neu berechnet (wenn *auto run sprites* aktiviert ist) und die Kamera neu ausgerichtet.

### 7.5 Befehle des Menüs *Path / Camera*
| Befehl | Beschreibung |
|---|---|
| Smooth path (from this frame) | Gleitender Mittelwert des bewegten Abschnitts. |
| Even speed (from this frame) | Verteilt die Punkte auf eine konstante Geschwindigkeit neu. |
| Freeze here (stop sprite) | Stoppt das Sprite von hier bis zum Ende. |
| Interpolate position to frame… | Lineare Interpolation bis zu einem gewählten End-Frame. |
| Paths color | Ändert die Pfadfarben (Ball, Schiedsrichter, Rot, Blau) oder stellt die Standardwerte wieder her. |

## 8. Posen, Laufen und Aktionen

### 8.1 Registerkarte Poses
Wähle eine **Kategorie** aus dem Dropdown-Menü und klicke auf eine Miniatur, um die Pose zuzuweisen. Sie gilt für die gesamte Gruppe (Posen werden automatisch zwischen Rot und Blau umgerechnet). Der Bereich richtet sich nach *Changes apply to*. Mit **[** und **]** wechselst du zur vorherigen/nächsten Pose der Kategorie. Die Kategorien stammen aus `tore_pose_sets.json`.

### 8.2 Sprite sheet
Die Schaltfläche **Sprite sheet** öffnet ein größenveränderbares Fenster mit der gesamten Sprite-Tafel; ein Klick weist dem ausgewählten Sprite dieses Sprite (nach ID) zu.

### 8.3 Registerkarte Actions
Wende ab dem aktuellen Frame eine Aktion auf den ausgewählten Spieler (oder die gesamte Gruppe) an. Die Teamfarbe wird automatisch berücksichtigt. Jede Aktion hat die Richtung **E** oder **W** (Pfeile `E >` / `< W`); manche sind „ohne Richtung“ (*Go*). Beim *Moonwalk* bezeichnet die Richtung die Bewegungsrichtung, während das Sprite in die entgegengesetzte Richtung blickt.

Die Option **then resume running automatically** setzt das Laufen/die Standpose direkt nach der Aktion automatisch fort, basierend auf der Bewegung der folgenden Frames. Wenn nicht genügend Frames vorhanden sind, werden weitere hinzugefügt.

Die verfügbaren Aktionen sind in `tore_actions.json` definiert (standardmäßig: Hechtsprung, Kopfball, Fallrückzieher, Sturz nach Zusammenstoß, Aufstehen, Jubel, Moonwalk).

### 8.4 Laufrichtungen (Kompassrose in der Registerkarte Actions)
Jeder Button (NW, N, NE, W, E, SW, S, SE) wendet ab dem aktuellen Frame bis zum Filmende den Laufzyklus dieser Richtung an. **stand** setzt die Standpose in Richtung der letzten Bewegungsrichtung. Für Schiedsrichter und Ball gelten die jeweiligen Zyklen.

### 8.5 Menü *Sprite*
| Befehl | Beschreibung |
|---|---|
| Action here | Wie in der Registerkarte Actions (Untermenü). |
| Run (sprites only, to end of film) | Laufzyklus in einer Richtung. |
| Auto-sprites along path (from this frame / whole film) | Berechnet die Posen aus der tatsächlichen Bewegung neu und **erhält Spezialposen** (Aktionen). |
| Mirror pose (E ↔ W) | Spiegelt die Pose des ausgewählten Sprites. |
| Lock pose (clear animation from here) | Hält die aktuelle Pose bis zum Ende fest. |
| Program pose sequence… | Fragt eine durch Kommas getrennte ID-Liste ab, die ab dem aktuellen Frame bis zum Ende zyklisch wiederholt wird. |

### 8.6 Ball und Schatten
Ball und Schatten werden immer gemeinsam bewegt. **Ball height (px)** regelt den vertikalen Abstand zwischen Ball und Schatten (positiv = Ball höher); die Einstellung gilt für den aktiven Bereich. Die Ballrotationen beim Laufen folgen dem im Datensatz definierten Zyklus.

## 9. Kamera

Die Kamera ist das 182×96 große Fenster, das das Spiel während der Szene zeigt.

- **Manuell**: *Scroll X/Y* (Werkzeug Camera) oder den cyanfarbenen Rand / das Feld mit dem H-Werkzeug ziehen, auch während der Wiedergabe.
- **Camera follows selected sprite** (Checkbox, Menü *Path / Camera* oder Rechtsklick ▸ *Camera follows this sprite*): erzeugt Scroll-Keyframes, die dem Sprite mit weich geglätteter Bewegung folgen (max. 6 px/frame in X, 2 in Y). Bei aktiviertem **whole film** beginnt es bei Frame 1, sonst beim aktuellen Frame.
- Eine **neue Szene** startet bereits mit der Kamera, die dem Ball folgt.
- Wenn Pfade oder Positionen geändert werden, wird die verfolgende Kamera automatisch neu berechnet; bei manuellem Verschieben des Scrolls wird die Verfolgung deaktiviert.
- **Interpolate scroll to frame…**: lineare Interpolation des Scrolls bis zu einem Frame.
- **Continue current scroll to end of film**: kopiert den aktuellen Scroll auf die folgenden Frames.

## 10. Timeline, Wiedergabe und Sounds

### 10.1 Wiedergabeleiste
`|<` erster Frame · `<` zurück · **Play all** (ab Beginn des Intervalls) · **Play from here** (Leertaste) · `>` vor · `>|` letzter Frame · **+ Frame** / **– Frame** · **Loop** · **fps** (1–60).

### 10.2 Timeline
- Klick oder Ziehen auf dem oberen Bereich: springt zum Frame.
- Farbiger Bereich unter den Zahlen (für das ausgewählte Sprite): **grün** = Laufen, **grau** = Stehen, **orange** = Spezialpose.
- **Bereichsmarker** (Pfeile unten, rot = Anfang, violett = Ende): Ziehen, um das Play-Intervall und den GIF-„play range“ festzulegen. Rechtsklick bietet *Set loop start/end here* und *Reset loop range*.
- **Farbige Dreiecke**: Soundereignisse.
- Rechtsklick: Menü für Wiedergabe, Bereich, Frame einfügen/löschen und Sound.

### 10.3 Sounds
Registerkarte **Sound**: *none* oder einen der vier Sounds auswählen; er wird dem aktuellen Frame zugewiesen. Jeder Sound kann nur auf einem Frame liegen; durch Zuweisen an einer anderen Stelle wird er verschoben.

| Sound | Farbe |
|---|---|
| Goal celebration | grün |
| Referee whistle | gelb |
| Disapproval whistles | orange |
| Missed-goal disappointment | blau |

## 11. View

| Eintrag | Wirkung |
|---|---|
| Show path / Show all paths | Pfad des ausgewählten Sprites / aller (außer Ball). |
| Show camera view | Kamerarahmen und Abdunklung außerhalb der Kamera. |
| Show sprite ids | ID über jedem Sprite. |
| Field size +/– (Ctrl +/–) | Feldvergrößerung 1–6×. |
| Zoom area in/out/reset | Vergrößert einen Feldbereich (bis 12×). Alternativ das Feld *Zoom area*, die Schaltfläche **1:1** und die Scrollbars verwenden. |

**Ghosts** (Dropdown): *None*, *Selected: previous frame*, *Selected: all previous frames*, *All sprites: all previous frames* – zeigt Transparenzen vorheriger Frames an, um die flüssige Bewegung zu beurteilen.

## 12. Data

| Befehl | Beschreibung |
|---|---|
| Edit pose sets, actions & path animation… | Grafischer Dateneditor (§12.1). |
| Reload data files | Lädt die JSON-Dateien nach manuellen Änderungen erneut. |
| Save current frame as kick-off formation | Speichert Sprites, Positionen und Scroll des aktuellen Frames in `tore_kickoff.json`, verwendet von *New scene*. Erfordert genau 11 rote, 11 blaue, Schiedsrichter, Schatten, Ball und 2 Tore. |

### 12.1 Dateneditor
Drei Registerkarten; Änderungen bleiben im Speicher, bis **Save to files** gedrückt wird (dadurch werden die JSON-Dateien geschrieben und die Änderungen sofort übernommen). Beim Schließen mit ausstehenden Änderungen wird gefragt, ob gespeichert werden soll.

**Pose sets** – Posenkategorien für die Gruppe *red* (IDs 0–58, blau = +59 automatisch), *referee* (118–141) oder *ball* (142–145). Links ein Set auswählen und *Name* sowie *IDs* bearbeiten (akzeptiert `3,4,5`, `15-20`, `43-38` absteigend). Die Sprite-Leiste ist mit den Feld-IDs synchronisiert: Klick auf ein Sprite = Auswahl aus der Tafel, **+** = hinzufügen, Rechtsklick = entfernen. Schaltflächen *Add new*, *Delete*, *Up*, *Down*.

**Actions** – Aktionsliste (Kleinbuchstaben/Ziffern/Unterstrich als Schlüssel, Bezeichnung, **E**-Sequenz und **W**-Sequenz). Ist W leer, wird es als Spiegelung von E berechnet (`k → 58−k`). IDs können wiederholt werden, um eine Pose über mehrere Frames beizubehalten. Optionen: *No direction (single entry)* und *E/W is the direction of travel*.

**Path animation** – Für jede Richtung (und die Gruppen red / referee / ball) werden die **IDLE**-Pose (linkes Feld, vor dem Zyklus) und der restliche Laufzyklus definiert. Beim Ball gibt es den *Rotation*-Zyklus. Standposen werden nicht in Actions, sondern hier definiert.

## 13. Animiertes GIF exportieren (File ▸ Export animated GIF…)

| Abschnitt | Optionen |
|---|---|
| **Content** | Frames: gesamter Film / Play-Intervall / ab hier. Bereich: Kamerafenster (folgt dem Scroll) oder gesamtes Feld. |
| **Size and speed** | Skalierung 1–8×, weiche Skalierung, fps 1–50, letzten Frame halten (ms), Endlosschleife. |
| **Quality** | Preset (*Smallest file*, *Small*, *Balanced*, *High quality*, *Maximum quality*, *Custom*), 2–256 Farben, nur jeden N-ten Frame, gemeinsame Palette, Dithering, Optimierung. |

*Calculate size* schätzt Dateigröße, Abmessungen und Dauer ohne zu speichern; *Export…* fragt nach dem Speicherpfad. Der Vorgang besitzt eine Fortschrittsanzeige und kann abgebrochen werden. Mit gemeinsamer Palette und ohne Dithering entstehen die kleinsten Dateien. Die Einstellungen bleiben erhalten, solange der Editor geöffnet ist.

## 14. Tastenkürzel

| Taste | Aktion |
|---|---|
| **V / D / P / H** | Select / Draw / Click path / Camera |
| **Leertaste** | Play from here / stop |
| **Pfeiltasten** | 1 px verschieben (Shift = 5 px) |
| **PgUp / PgDn**, **, / .**, Mausrad | Vorheriger / nächster Frame |
| **Home / End** | Erster / letzter Frame |
| **[ / ]** | Vorherige / nächste Pose |
| **Ins / Del** | Frame einfügen / löschen |
| **Enter / Backspace / Esc** | Pfad beenden / Punkt entfernen / abbrechen oder Auswahl aufheben |
| **Ctrl+Z / Ctrl+Y** | Rückgängig / wiederholen |
| **Ctrl+A** | Alle Spieler auswählen |
| **Ctrl+N / O / S / Shift+S** | Neu / Öffnen / Speichern / Speichern unter |
| **Ctrl + / Ctrl –** | Feld-Zoom |
| **Ctrl+Mausrad** | Bereichs-Zoom |

Werkzeugtasten und Leertaste werden ignoriert, während in ein Textfeld geschrieben wird.

## 15. Empfohlene Arbeitsabläufe

**Eine Szene von Grund auf erstellen**
1. *File ▸ New scene*. Frame 1 zeigt die Anstoßaufstellung.
2. *Scene properties* festlegen (Ausgang, Typ, Autor).
3. Einen Spieler auswählen, **D** oder **P** drücken und die Bewegung zeichnen: Frames werden erstellt und Laufposen automatisch zugewiesen.
4. Für die anderen Sprites wiederholen; für den Ball Ball oder Schatten auswählen.
5. Aktionen (Schuss, Hechtsprung, Jubel) im richtigen Frame über die Registerkarte *Actions* hinzufügen.
6. Mit *Ghosts* und *Play all* prüfen; Seilpfade korrigieren und *Smooth* / *Even speed* verwenden.
7. Kamera einstellen (*Camera follows…*) und die gewünschten Sounds auf den entsprechenden Frames setzen.
8. *Save as numbered scene…*

**Eine Szene für die andere Mannschaft wiederverwenden**: öffnen, *Edit ▸ Mirror scene*, unter einer anderen Nummer speichern.

**Vorschau zum Teilen**: *Export animated GIF…* mit Preset *Balanced*, Bereich *camera window*.

## 16. Hinweise und Fehlerbehebung

- **„Graphics not found“** → *File ▸ PIC folder…* verwenden und den Ordner mit `26.VGA`, `27.VGA`, `29.VGA` wählen.
- **„Data files“-Warnung beim Start** → prüfen, dass der Ordner `data` neben der ausführbaren Datei die drei gültigen JSON-Dateien enthält. Bei einer PyInstaller-`--onefile`-Build muss der Pfad aus `sys.executable` und nicht aus `__file__` ermittelt werden.
- **New scene funktioniert nicht** → `tore_kickoff.json` fehlt oder ist unvollständig: *Save current frame as kick-off formation* auf einem gültigen Frame verwenden.
- **Der Pfad endet zu früh** → 256 Frames oder der Feldrand wurde erreicht (Sprites werden auf das Feld begrenzt).
- **Pfeiltasten bewegen das Sprite nicht** → zuerst in das Feld klicken, damit es den Fokus erhält.
- **ANZAHL wird nicht aktualisiert** → Die Datei muss im Szenenordner oder im übergeordneten Ordner liegen; die Nummer muss das bereits registrierte Maximum überschreiten.
- **Posen ändern sich nicht** → prüfen, dass das ausgewählte Sprite kein Tor ist und der gewünschte Bereich (*frame* / *this + following*) eingestellt ist.
- Pose-Kategorien mit **(?)** in den Daten müssen noch überprüft werden.
- Änderungen an den Daten (JSON) können mit Undo **nicht** rückgängig gemacht werden.

## Anhang – Szenendateiformat (Zusammenfassung)
- 12-Byte-Signatur: `BM-Ed1.0-WK\0` oder `BM-Ed1.3-WK\0`.
- 4 Byte: Frame der Soundereignisse (255 = keiner).
- 1 Byte: Anzahl der Frames − 1.
- Für jeden Frame 164 Byte: Scroll (X low, Y high) + 27 Datensätze aus 3 Wörtern (x, y, Sprite-ID) in Zeichenreihenfolge.
- Am Ende: Längenbyte + Autorenname in Codepage 437, beendet durch `\0`.
- Tore haben spezielle IDs (1000 links, über 1000 rechts) und x entspricht der x-Koordinate des Balls.
