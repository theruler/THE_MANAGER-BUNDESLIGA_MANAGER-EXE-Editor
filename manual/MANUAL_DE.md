# THE MANAGER / Bundesliga Manager Professional / Bundesliga Manager Hattrick String-Editor — Handbuch

Dieses Handbuch beschreibt das Programm so, wie es der Anwender sieht. Es setzt keine Programmierkenntnisse voraus.

Die Bezeichnungen von Schaltflächen, Menüs und Reitern sind hier so angegeben, wie sie in der englischen Oberfläche erscheinen. In der deutschen Oberfläche sind die meisten davon übersetzt. Die Reiter zu Bundesliga Manager Hattrick (Abschnitt 9) erscheinen immer auf Englisch.

## 1. Was dieses Programm kann

Der Editor ändert Texte, eingebettete Schriften und ausgewählte Spieleinstellungen in unterstützten DOS-Programmdateien.

Er unterstützt zwei Spielefamilien:

- **THE MANAGER / Bundesliga Manager Professional** — Abschnitte 4 bis 8
- **Bundesliga Manager Hattrick (BMH)** — Abschnitt 9

Der Editor kann:

- Spieltexte bearbeiten
- eingebettete Schriften bearbeiten
- Texte als JSON exportieren und importieren
- Texte übersetzen
- das Startjahr ändern
- die Region zwischen Deutschland, Italien, Frankreich und England umstellen
- ausstehende Änderungen vor dem Speichern in einer Vorschau anzeigen
- die Texte bearbeiten, die in Programmdateien von Bundesliga Manager Hattrick gespeichert sind, zusammen mit den Textdateien, Schriften und Bildordnern dieses Spiels (Abschnitt 9)

Das Startjahr und der Regionswechsel sind für die Profile von THE MANAGER vorgesehen.

Der Editor erkennt ein Spiel an seiner inneren Struktur, nicht an seinem Dateinamen. Das Umbenennen einer Programmdatei hat keinen Einfluss auf die Erkennung.

Unbekannte oder inkompatible Programmdateien bleiben nicht unterstützt und können weder bearbeitet noch gespeichert werden.

Der Editor startet das Spiel selbst nie.

## 2. Das Programm starten

Starten Sie:

`THE MANAGER - Bundesliga Manager String-Editor.exe`

per Doppelklick.

Die eigenständige Windows-Version benötigt kein Python.

Neben dem Programm liegt ein Ordner `data` mit:

- `char-mapping.json` — speichert Zeichenzuordnungen und bestätigte Schriftzuweisungen
- `deepl_key.txt` — optionale Datei für einen DeepL-API-Schlüssel

Lassen Sie den Ordner `data` neben dem Programm liegen.

Wenn Sie die ausführbare Datei des Editors verschieben, verschieben Sie den Ordner `data` mit.

## 3. Sprache der Oberfläche

Der Editor startet auf Englisch.

Die Oberfläche kann umgeschaltet werden zwischen:

- Englisch
- Deutsch
- Spanisch
- Französisch
- Italienisch

Verwenden Sie:

**View → Language**

Die Änderung wirkt sofort.

Die geladene Programmdatei, der ausgewählte Text, der Suchtext, die Filter und der ausstehende Bearbeitungszustand bleiben erhalten.

Das Ändern der Oberflächensprache verändert die geladene Spieldatei nicht.

Die gewählte Oberflächensprache wird nicht dauerhaft gespeichert. Beim nächsten Programmstart wird wieder Englisch verwendet.

Einige technische Filterwerte können auf Englisch bleiben, weil sie interne Vertragswerte sind, zum Beispiel:

- `Fixed`
- `Suffix-Shared`
- `READ-ONLY`
- `Problems`

Die Reiter zu Bundesliga Manager Hattrick (Abschnitt 9) werden immer auf Englisch angezeigt, unabhängig von der gewählten Oberflächensprache.

## 4. Eine Spieldatei laden

Arbeiten Sie immer mit einer Sicherungskopie Ihrer originalen Spieldatei.

Wählen Sie:

**📁 Choose EXE…**

oder:

**File → Open EXE…**

und wählen Sie eine unterstützte Spieldatei.

Wird die Datei erkannt, erscheint ihr Profil und der Editor wird verfügbar.

Wird die Datei nicht erkannt, bleibt der Editor gesperrt.

Der Editor rät nicht, wenn die Struktur der Datei keinem unterstützten Profil entspricht.

Sowohl EXEPACK-gepackte als auch bereits entpackte unterstützte Dateien können geladen werden.

Programmdateien von Bundesliga Manager Hattrick verwenden einen eigenen DOS-Extender und müssen nicht entpackt werden. Sie werden auf dieselbe Weise geladen und öffnen die in Abschnitt 9 beschriebenen Reiter.

## 5. Startjahr

Das Startjahr kann direkt im oberen Bereich des Editors geändert werden.

Die Funktion steht für alle drei unterstützten Programmprofile von THE MANAGER zur Verfügung.

Geben Sie das gewünschte Jahr ein oder wählen Sie es aus.

Der Editor prüft den Wert, bevor er ihn anwendet.

Der unterstützte Bereich ist:

`1900–2099`

Das Ändern des Startjahres verändert nur die Kopie der Programmdatei im Speicher des Editors.

Auf die Festplatte wird erst geschrieben, wenn Sie **Save As** verwenden.

Wenn Sie das Jahr auf den ursprünglichen Wert zurückstellen, entfällt diese ausstehende Änderung.

## 6. Regionswechsel

Der Regionswechsel steht im oberen Bereich des Editors zur Verfügung.

Die verfügbaren Regionen sind:

- Deutschland
- Italien
- Frankreich
- England

Der Editor verwendet die ursprüngliche interne Länderkonfiguration, die die Spieldateien benutzen.

Es werden nur diese vier gültigen Konfigurationen angeboten. Interne technische Regionswerte werden dem Anwender nicht angezeigt.

Das Ändern der Region verändert nur die Programmdatei im Speicher.

Auf die Festplatte wird erst beim Speichern geschrieben.

Wenn Sie die Region auf den ursprünglichen Wert zurückstellen, entfällt diese ausstehende Änderung.

Frankreich wurde mit dem Regionswechsel erfolgreich im Spiel getestet.

Die französische Spieldatei selbst ist derzeit kein eigenes unterstütztes Editorprofil. Der Regionswechsel ändert die Länderkonfiguration eines der drei unterstützten Programmprofile.

## 7. Text suchen und ändern

Der Bereich **Strings** zeigt das bearbeitbare Textverzeichnis des geladenen Spiels.

Jeder Eintrag zeigt Informationen wie:

- Nummer
- Offset
- aktueller Text

Verwenden Sie **Search**, um Text zu finden.

Die Suche prüft sowohl den aktuellen als auch den ursprünglichen Text. Ein Text ist daher auch nach dem Bearbeiten noch auffindbar.

**Filter ▸** bietet zusätzliche Filter für:

- Art
- Schrift
- Änderungsstatus
- Status

Wählen Sie einen Text aus, um ihn im Bearbeitungsbereich zu öffnen.

Führende, nachgestellte und mehrfache Leerzeichen bleiben erhalten, weil viele Spieltexte Leerzeichen zur Ausrichtung verwenden.

Ändern Sie den Text und wählen Sie:

**✔ Apply change**

Zu diesem Zeitpunkt wird noch nichts in die Spieldatei geschrieben.

Die Änderung bleibt im Editor ausstehend, bis Sie speichern.

## 8. Texte verlängern

Normale Texte liegen in gemeinsamen Textblöcken.

Texte im selben Block teilen sich den verfügbaren freien Platz.

Ein kurzer Text kann daher durch einen längeren ersetzt werden, solange der gesamte Block noch passt.

Der Editor zeigt Informationen wie diese:

```text
normal | FLOW.FON | bytes 14→21 (Δ +7) | PASS | Shared B3 rest after all changes: 46 bytes
```

Die Zeile zeigt die Art des Textes, seine Schrift, die alte und neue Länge in Bytes (Δ ist die Differenz), das Prüfergebnis und — bei Texten in einem gemeinsamen Block — die Blocknummer und die Bytes, die nach allen ausstehenden Änderungen in diesem Block noch frei sind.

Wenn eine Änderung nicht mehr passen würde, meldet der Editor das Problem und erlaubt das Speichern erst, wenn es behoben ist.

Bei Bundesliga Manager Hattrick funktioniert der freie Platz anders. Siehe Abschnitt 9.4.

## 9. Bundesliga Manager Hattrick (BMH)

### 9.1 Unterstützte Dateien

Folgende Programmdateien werden unterstützt:

| Programmdatei | Sprache | Version | Textdatei |
|---|---|---|---|
| `BMH.EXE` | Deutsch | V2.24 | `TEXTD.BLK` |
| `BMH_1.EXE` | Deutsch | V3.7 | `TEXTD.BLK` |
| `FLTD.EXE` | Englisch | — | `TEXTE.BLK` |

Andere Versionen des Spiels werden nicht unterstützt: Die Funktionen für die Texte in der Programmdatei bleiben dann gesperrt, genau wie bei jeder unbekannten Programmdatei.

Die Textdatei (`TEXTD.BLK` oder `TEXTE.BLK`) wird neben der Programmdatei gesucht. Fehlt sie, bittet der Editor Sie, sie auszuwählen. Brechen Sie ab und ist die Programmdatei eine unterstützte Version, können Sie die Texte in der Programmdatei trotzdem bearbeiten.

Öffnen Sie die Programmdatei wie in Abschnitt 4 beschrieben. Der Editor erkennt sie an ihrer Struktur, auch eine umbenannte Datei wird gefunden.

### 9.2 Die Reiter

Nach dem Laden werden folgende Reiter angezeigt:

- **BMH EXE Strings** — die Texte, die in der Programmdatei gespeichert sind (immer der erste Reiter ganz links)
- **BMH Strings** — die Texte der Textdatei `.BLK`
- **VGA …** — ein Reiter für jeden Bildordner, der neben der Programmdatei gefunden wird
- **Fonts** — die Spielschriften `BMH2.FNT` und `BMH3.FNT`, geladen aus dem Ordner `F` neben der Programmdatei
- **Options** — Einstellungen, darunter die Zeichenzuordnung

Die Bild- und Schriftreiter werden nur gefüllt, wenn ihre Ordner und Dateien neben der Programmdatei gefunden werden.

### 9.3 BMH EXE Strings

Dieser Reiter listet die übersetzbaren Texte auf, die in der Programmdatei gespeichert sind: Bezeichnungen, Meldungen und den Spielkommentar.

Jeder Eintrag zeigt:

- die Nummer (ID)
- den Offset in der Datei
- den aktuellen Text

Verwenden Sie **Search**, um Text zu finden. Die Suche findet auch den ursprünglichen Text bereits bearbeiteter Texte.

Aktivieren Sie **Modified only**, um nur die von Ihnen geänderten Texte zu sehen.

Wählen Sie einen Text aus, um ihn im **Bearbeitungsbereich** zu öffnen:

- jedes Leerzeichen (0x20) wird blau hervorgehoben, weil Leerzeichen für die Ausrichtung wichtig sind
- unter dem Text zeigt der Editor, wie viele Bytes der Text belegt und wie viele Bytes sein Platz bietet
- mit **Apply** übernehmen Sie die Änderung, mit **Discard** verwerfen Sie sie

In die Datei wird erst beim Speichern geschrieben (Abschnitt 9.9).

**Was angezeigt wird**

Es werden nur echte Texte angeboten. Folgendes ist absichtlich ausgeblendet, weil eine Änderung das Spiel beschädigen könnte:

- Dateinamen und Pfade, Gerätenamen, der Versionstext
- Zeichentabellen und Silbenlisten
- Steuerfolgen, die kein Text sind
- in der englischen Programmdatei außerdem reine Satzzeichen und Layoutfragmente

Die deutschen Programmdateien bieten 175 Texte, die englische 55.

**Sonderzeichen**

Das Spiel verwendet den deutschen 7-Bit-Zeichensatz. Der Editor zeigt dessen Sonderzeichen als normale Buchstaben: `Ä Ö Ü ä ö ü ß §`.

Zeichen, die das Spiel nicht darstellen kann, lassen sich nicht eingeben. Im Reiter **Options** (Zeichenzuordnung) kann einem Byte ein anderes Zeichen zugewiesen werden. Beachten Sie, dass die Schrift dieses Zeichen ebenfalls enthalten muss.

Ein Byte ohne Buchstaben kann als `\xNN` geschrieben werden, zum Beispiel `\x1F`.

**Leere Texte**

Ein Text darf nicht leer sein. Verwenden Sie ein einzelnes Leerzeichen, wenn ein Text leer erscheinen soll.

### 9.4 Freier Platz und die Platzanzeige

Die Texte in der Programmdatei haben einen festen Platz. Ist ein Text länger als sein Platz, schreibt der Editor ihn an eine andere Stelle und korrigiert den Verweis darauf. Das geschieht automatisch.

Die **Platzanzeige** im Bearbeitungsbereich, rechts ausgerichtet, zeigt die Lage. Sie lautet zum Beispiel:

`3,912 / 7,967 bytes (49%) - 4,055 free`

- die erste Zahl ist der Platz, den alle Texte benötigen
- die zweite Zahl ist der für diese Texte verfügbare Platz
- der Balken zeigt, wie voll er ist: grün unter 85 %, orange ab 85 %, rot ab 95 %
- **NOT ENOUGH SPACE** (rot) bedeutet, dass die Texte nicht passen. Speichern ist erst möglich, wenn Sie einige Texte kürzen.

**Deutsche Versionen (`BMH.EXE`, `BMH_1.EXE`)**

Neben dem Platz der Texte selbst enthalten diese Versionen 4.032 Bytes ungenutzten Platz, den der Editor automatisch verwendet. Der Text der Platzanzeige zeigt dann auch, wie viel davon belegt ist.

**Englische Version (`FLTD.EXE`)**

Diese Programmdatei enthält keinen ungenutzten Platz, der sicher verwendet werden kann. Die 55 Texte dürfen zusammen nicht länger werden als ihr ursprünglicher Platz (2.872 Bytes, davon etwa 14 Bytes frei). Ein Text kann nur länger werden, wenn andere Texte um dieselbe Menge kürzer werden. Übersetzungen in Sprachen mit längeren Wörtern müssen daher abgekürzt werden.

> **Hinweis:** Der zusätzliche Platz der deutschen Versionen wurde an der Struktur der Dateien geprüft. Er wurde noch nicht durch Ausführen des Spiels bestätigt. Testen Sie jedes veränderte Spiel, bevor Sie es weitergeben.

### 9.5 Spielkommentar — der Vorlageneditor

Ein Teil der Texte sind keine einfachen Texte, sondern **Vorlagen**. Das Spiel baut daraus jedes Mal einen anderen Satz. In jeder Programmdatei gibt es 22 davon, zum Beispiel:

`%x10HE#%c#x %x02RUNS#RUNS#x WITH THE BALL.`

Für diese Texte ersetzt der **Template editor** das einfache Textfeld. Es ist derselbe Editor, der in THE MANAGER für Zeitungstexte verwendet wird.

Das Kontrollkästchen **Template editor** neben den Schaltflächen schaltet ihn ein (Standard) oder aus. Ist er ausgeschaltet, wird die Vorlage als einfacher Text angezeigt.

**Wie eine Vorlage aufgebaut ist**

- Der Text wird in **Komponenten** zerlegt. **ROOT** ist der ganze Satz.
- Ein **Selektor** ist eine Stelle, an der das Spiel zwischen Alternativen wählt. Jede Alternative ist ein **Zweig**. Jeder Zweig hat sein eigenes Textfeld.
- Ein Zweig kann weitere Selektoren und **Tags** enthalten.
- Ein Tag ist ein Platzhalter, den das Spiel ausfüllt, zum Beispiel ein Spielername.

**Tags**

| Tag | Abzeichen | Bedeutung |
|---|---|---|
| `%a` | TEAM A | Name von Mannschaft A |
| `%b` | TEAM B | Name von Mannschaft B |
| `%c` | PLAYER | der Spieler, um den es im Ereignis geht |
| `%d` | 2ND PLAYER | der zweite Spieler, zum Beispiel der Empfänger des Passes |
| `%f` | DEFENDER | ein Spieler der anderen Mannschaft, der den Ball berührt oder blockt |
| `%z` | OPPONENT | der Gegenspieler im Zweikampf (Tackling, Foul, Dribbling) |
| `%s` | REFEREE | der Name des Schiedsrichters |
| `%0` | METERS | eine Zahl, die Entfernung zum Tor in Metern |
| `%e` | END | beendet den Text |

**Selektoren**

*Zufalls-Selektoren* wählen einen Zweig nach Zufall:

| Abzeichen | Zweige |
|---|---|
| RANDOM2 … RANDOM5 | 2 bis 5 |

*Kontext-Selektoren* wählen nach der Spielsituation. Sie zeigen, welche Alternative zu welcher Situation gehört:

| Abzeichen | Was entschieden wird | Zweige |
|---|---|---|
| SUBJECT | wie der Spieler genannt wird | 1 Pronomen, 2 Name |
| VOLLEY | Volley oder nicht | 1 Volley, 2 normal |
| PASS TYPE | Art des Passes | 1 langer oder hoher Ball, 2 kurzer Pass |
| CARD | Art der Karte | 1 gelb, 2 gelb-rot, 3 rot |
| FLIGHT | wie der Ball fliegt | 1 und 2 lang, 3 hoch, 4 auf die andere Seite |
| CROSS | Art des langen Passes | 1 Flanke in den Strafraum, 2 langer Pass |
| BACKWARDS | Richtung | 1 zurück, 2 nichts |
| DESTINATION | wohin der Ball geht | 1 hinein, 2 in Richtung oder quer |
| SHOT SIDE | Schuss am Tor vorbei | 1 darüber, 2 daneben |
| SHOT END | Ergebnis des Schusses | 1 nahe am Tor, 2 aus |

> **Hinweis:** Die Namen der Tags und Kontext-Selektoren wurden aus dem Spielcode und aus den Texten abgeleitet. Wo eine Bedeutung nicht sicher ist, benennt das Abzeichen, was die Zweigtexte aussagen.

**Mit dem Vorlageneditor arbeiten**

- Klicken Sie in ein Textfeld und ändern Sie den Text dieses Zweigs.
- Ein Tag erscheint im Textfeld als farbiges Abzeichen. Ziehen Sie ein Abzeichen aus dem Vorrat in ein Textfeld, um es einzufügen.
- Ziehen Sie ein Selektor-Abzeichen aus dem Vorrat in ein Textfeld, um einen Selektor mit seinen Zweigen hinzuzufügen.
- **Strg+Z** macht die letzte Änderung in einem Textfeld rückgängig.
- Geben Sie in einem Text kein `#` und kein `%` ein. Sie sind für die Struktur reserviert.
- Vermeiden Sie es, einen Zweig (außer dem ersten) mit dem Buchstaben `x` zu beginnen: Der Editor setzt dann ein Leerzeichen davor, damit die Struktur gültig bleibt.

Der Editor zeigt die Größe der fertigen Vorlage, und die Platzanzeige wird bei jeder Änderung aktualisiert.

Mit **Apply** übernehmen Sie die Vorlage, mit **Discard** verwerfen Sie die Änderungen. Wenn Sie einen anderen Text auswählen, obwohl Änderungen noch nicht übernommen sind, fragt der Editor zuerst nach.

Eine Vorlage ohne gültige Struktur kann weder übernommen noch gespeichert werden. Der Editor nennt den Grund.

### 9.6 Übersetzung

Die Übersetzungsleiste (Dienst, Quellsprache, Zielsprache und die Schaltfläche zum Übersetzen) ist Teil des Bearbeitungsbereichs. Schalten Sie die Option für die automatische Übersetzung im Menü **Tools** ein, um sie anzuzeigen. Sie arbeitet wie in den übrigen Teilen des Editors.

- Steuercodes werden nie an den Übersetzungsdienst gesendet. `\xNN`-Folgen sowie in der Programmdatei die Tags und Strukturzeichen der Vorlagen bleiben unverändert.
- Vorlagen werden Zweig für Zweig übersetzt und wieder zusammengesetzt. Die Struktur kann durch die Übersetzung nicht beschädigt werden.
- Ein Text, der Zeichen enthält, die das Spiel nicht darstellen kann, oder den der Dienst beschädigt zurückgegeben hat, wird übersprungen und bleibt unverändert. Die Ergebnismeldung nennt, wie viele Texte übersprungen wurden.

Der Eintrag **Translate all** im Menü **Tools** übersetzt die Texte des Reiters, der gerade angezeigt wird. Ein Fenster fragt nach dem Bereich: Geben Sie die erste und die letzte ID ein und wählen Sie **Start**. Prüfen Sie das Ergebnis: Maschinelle Übersetzung kurzer Fragmente muss oft korrigiert werden.

### 9.7 Änderungsvorschau

Der erste Eintrag im Menü **Tools** öffnet die Vorschau der ausstehenden Änderungen. Für die Texte der Programmdatei zeigt sie:

- **Summary** — Anzahl der geänderten Texte, wie viele an eine andere Stelle geschrieben werden, belegter Platz und ob Speichern möglich ist
- **Strings** — jeder geänderte Text mit altem und neuem Platz, seiner Länge in Bytes sowie altem und neuem Text
- **Pointers** — die Verweise im Spiel, die korrigiert werden

Die Vorschau ist nur verfügbar, wenn keine Bearbeitung mehr auf **Apply** wartet.

### 9.8 Textdatei, Schriften und Bilder

**BMH Strings** bearbeitet die Textdatei `.BLK` mit denselben Werkzeugen: Suche, **Modified only**, **Apply**, **Discard**, Übersetzung. Die Texte dieser Datei liegen hintereinander, und der Editor baut die Datei beim Speichern neu auf. Testen Sie das Spiel, nachdem Sie Texte deutlich verlängert haben.

Der Reiter **Fonts** bearbeitet `BMH2.FNT` und `BMH3.FNT`. Die **VGA**-Reiter zeigen die Bildordner.

### 9.9 Speichern

Wählen Sie **File → Save As**. Der Editor speichert, was geändert wurde, eine Datei nach der anderen, und fragt jedes Mal nach dem Dateinamen: zuerst die Schriften, dann die Textdatei, dann die Programmdatei.

- Wählen Sie die Originaldatei, fragt der Editor nach einer Bestätigung und behält eine Sicherungskopie des Originals. Die Bestätigungsmeldung zeigt, wo die Sicherung liegt.
- Wurde die Datei seit dem Laden von einem anderen Programm geändert, weigert sich der Editor, sie zu überschreiben.
- Bevor die Programmdatei geschrieben wird, prüft der Editor sein eigenes Ergebnis: Die Dateigröße ist unverändert, das erneute Einlesen liefert genau Ihre Texte, kein anderer Verweis wird berührt, und außerhalb des Textbereichs wurde nichts geändert. Schlägt die Prüfung fehl, wird nichts geschrieben, und die Meldung beginnt mit *Self-check failed*.

Eine gespeicherte Programmdatei kann erneut geladen werden. Der Editor erkennt sie wie zuvor, und der freie Platz wird richtig angezeigt.

### 9.10 Grenzen im Überblick

- Es werden nur die drei Programmdateien aus Abschnitt 9.1 unterstützt.
- In der englischen Programmdatei dürfen die Texte insgesamt nicht länger werden.
- Leere Texte sind nicht erlaubt.
- Zeichen, die das Spiel nicht darstellen kann, sind nicht verwendbar, solange keine Zuordnung und kein Schriftzeichen vorhanden sind.
- Der Editor startet das Spiel nicht. Testen Sie ein verändertes Spiel immer, bevor Sie es verwenden oder weitergeben.
