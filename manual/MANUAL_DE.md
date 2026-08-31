
### MANUAL_DE.md

```markdown
# THE MANAGER / Bundesliga Manager Professional String-Editor — Handbuch

Dieses Handbuch beschreibt den Editor aus Sicht eines Endnutzers. Programmierkenntnisse sind nicht erforderlich.

## 1. Was das Programm macht

Der Editor kann Texte, eingebettete Fonts und ausgewählte Spieleinstellungen in unterstützten DOS-EXE-Dateien bearbeiten.

Unterstützte Spielversionen:

- THE MANAGER – englische Fassung
- THE MANAGER – italienische Fassung
- Bundesliga Manager Professional / BMP 2.0

Der Editor kann:

- Spieltexte bearbeiten
- eingebettete Fonts bearbeiten
- Strings als JSON exportieren und importieren
- Texte übersetzen
- das Startjahr ändern
- die Region zwischen Deutschland, Italien, Frankreich und England ändern
- ausstehende Änderungen vor dem Speichern anzeigen

Der Editor erkennt ein Spiel anhand seines internen Aufbaus und nicht anhand des Dateinamens.

Das Umbenennen einer EXE beeinflusst die Erkennung daher nicht.

Unbekannte oder inkompatible EXE-Dateien bleiben nicht unterstützt und können nicht bearbeitet oder gespeichert werden.

Der Editor selbst startet das Spiel niemals.

## 2. Programm starten

Starte:

`THE MANAGER - Bundesliga Manager String-Editor.exe`

per Doppelklick.

Die eigenständige Windows-Version benötigt keine Python-Installation.

Neben dem Programm befindet sich ein Ordner `data` mit:

- `char-mapping.json` — speichert Zeichenzuordnungen und bestätigte Font-Zuweisungen
- `deepl_key.txt` — optionale Datei für einen DeepL-API-Schlüssel

Lass den Ordner `data` neben dem Programm liegen.

Wenn du die Editor-EXE verschiebst, verschiebe den `data`-Ordner mit.

## 3. Sprache der Benutzeroberfläche

Der Editor startet standardmäßig auf Englisch.

Die Benutzeroberfläche kann zwischen folgenden Sprachen umgeschaltet werden:

- Englisch
- Deutsch
- Spanisch
- Französisch
- Italienisch

Verwende:

**View → Language**

Die Umstellung erfolgt sofort.

Die aktuell geladene EXE, der ausgewählte String, der Suchtext, die Filter und der aktuelle Bearbeitungszustand bleiben erhalten.

Das Umschalten der Sprache verändert die geladene Spiel-EXE nicht.

Die gewählte Sprache wird nicht dauerhaft gespeichert. Beim nächsten Programmstart ist die Oberfläche wieder Englisch.

Einige technische Filterwerte können auch in der deutschen Oberfläche Englisch bleiben, zum Beispiel:

- `Fixed`
- `Suffix-Shared`
- `READ-ONLY`
- `Problems`

Dabei handelt es sich um feste technische Werte und nicht um normale UI-Beschriftungen.

## 4. Spieldatei laden

Arbeite immer mit einer Sicherung deiner ursprünglichen Spiel-EXE.

Wähle:

**📁 EXE auswählen…**

oder:

**Datei → EXE öffnen…**

und öffne eine unterstützte Spiel-EXE.

Wird die Datei erkannt, erscheint ihr Profil und der Editor wird freigeschaltet.

Wird die Datei nicht erkannt, bleibt der Editor gesperrt.

Der Editor versucht nicht, bei einer unbekannten EXE-Struktur zu raten.

Sowohl gepackte EXEPACK-Dateien als auch bereits entpackte unterstützte EXE-Dateien können geladen werden.

## 5. Startjahr

Das Startjahr kann direkt im oberen Bereich des Editors geändert werden.

Die Funktion steht für alle drei unterstützten EXE-Profile zur Verfügung.

Gib das gewünschte Jahr ein bzw. wähle es aus.

Der Editor prüft den Wert vor der Übernahme.

Der unterstützte Bereich ist:

`1900–2099`

Eine Änderung des Startjahres verändert zunächst nur die im Speicher befindliche Arbeitskopie der EXE.

Auf die Festplatte wird erst mit **Speichern unter…** geschrieben.

Wenn du das Startjahr wieder auf den ursprünglichen Wert zurückstellst, verschwindet diese ausstehende Änderung wieder.

## 6. Region Changer

Der Region Changer befindet sich im oberen Bereich des Editors.

Zur Auswahl stehen:

- Deutschland
- Italien
- Frankreich
- England

Der Editor verwendet dafür die ursprüngliche interne Länder-Konfiguration der Spiel-EXE.

Es werden ausschließlich diese vier gültigen Länder angeboten.

Die internen technischen Regionswerte werden dem Benutzer nicht angezeigt.

Eine Regionsänderung verändert zunächst nur die im Speicher befindliche EXE.

Erst beim Speichern wird sie auf die Festplatte geschrieben.

Wenn du wieder auf die ursprüngliche Region zurückstellst, verschwindet die ausstehende Regionsänderung.

Frankreich wurde mit dem Region Changer erfolgreich ingame getestet.

Die französische Spiel-EXE selbst ist derzeit kein eigenes unterstütztes Editorprofil. Der Region Changer ändert die Länder-Konfiguration innerhalb eines der drei unterstützten EXE-Profile.

## 7. Text suchen und ändern

Der Bereich **Strings** zeigt den bearbeitbaren Textbestand der geladenen EXE.

Zu jedem Eintrag werden Informationen wie:

- Nummer
- Offset
- aktueller Text

angezeigt.

Mit **Suche** kannst du nach Text suchen.

Die Suche berücksichtigt sowohl den aktuellen als auch den ursprünglichen Text. Dadurch findest du einen String auch dann wieder, wenn du ihn bereits geändert hast.

Über **Filter ▸** stehen zusätzliche Filter zur Verfügung, unter anderem für:

- Art
- Font
- Änderungszustand
- Status

Wähle einen String aus, um ihn im Bearbeitungsbereich zu öffnen.

Führende, nachfolgende und mehrfache Leerzeichen bleiben erhalten, da viele Spieltexte Leerzeichen zur Ausrichtung verwenden.

Ändere den Text und wähle:

**✔ Änderung übernehmen**

Dabei wird noch nichts in die Spiel-EXE auf der Festplatte geschrieben.

Die Änderung bleibt im Editor ausstehend, bis du speicherst.

## 8. Strings verlängern

Normale Strings liegen in gemeinsam genutzten Stringblöcken.

Alle Strings eines Blocks teilen sich den verfügbaren freien Speicher.

Ein kurzer String kann deshalb durch einen deutlich längeren ersetzt werden, solange der gesamte Block weiterhin in seinen verfügbaren Bereich passt.

Der Editor zeigt Informationen ähnlich wie:

```text
normal | FLOW.FON | Bytes 14→21 (Δ +7) | PASS | Gemeinsamer Rest B3 nach allen Änderungen: 46 Bytes