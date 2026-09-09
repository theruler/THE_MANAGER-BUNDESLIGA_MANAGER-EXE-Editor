# THE MANAGER / Bundesliga Manager Professional String-Editor

Editor for supported THE MANAGER / Bundesliga Manager Professional DOS executables.
By Theruler and Nobody

## Supported versions

- THE MANAGER – English version
- THE MANAGER – Italian version
- Bundesliga Manager Professional / BMP 2.0

Executable profiles are detected automatically. File names do not matter.

## Features

- Edit game strings
- Edit embedded fonts
- JSON string export / import
- Translation support
- Changes / Preview before saving
- Starting Year editor
- Region Changer
- Points per victory rule changer (2/3)
- English, German, Spanish, French and Italian interface
- Packed EXEPACK input support
- Standalone Windows release
- Newspaper csv exporter/importer
- Newspaper built-in visual editor
- MANA.DAT editor
- Executable extension option

## Usage

1. Open a supported EXE.
2. Make the required changes.
3. Review them with **Changes / Details**.
4. Save the modified executable with **Save As**.

Modified EXEPACK executables are saved unpacked. The editor does not contain an EXEPACK compressor.
Always keep a backup of the original executable and test modified executables before regular use.



## Region Changer

The Region Changer uses the original country configuration present in the game executables.

1. Germany (starting DM 1.500.000)
2. Italy (Starting Lire 750.000 Milion)
3. France (starting Francs 500.000)
4. England (starting Pounds 375.000)

Only Germany fetaures:
- Full newspaper (the other regions have the Body of the article filled with "XXXX X XX" lines).
- 1963 Historical start of the Bundesliga
- German flag screen at the beginning of each match (instead of black screen)
- Developer's birthdays easter egg

Only England features:
- ST, ND, RD, TH added to the date days and match minutes

## Starting Year

The starting year can be changed directly from the editor for all supported executable profiles.


## Points per victory rule

The points rule can be changed directly from the editor for all supported executable profiles.


## Newspaper built-in visual editor

A visual newspaper editor can be selected to better edit the lines. Tags can be moved, deleted or added.


## Executable extension option

To make more room for the text strings an option to enlarge the original executables has been added for all the supported versions.


## MANA.DAT editor

LEGAUE TAB
- Teams can be swapped by dragging the buttons to new position
- RESET puts every stat to zero
- SHUFFLE shuffles the teams within each league
- RANDOMIZE randomizes all the stats based on current team position in each league, according to an algorithm that take sin account actual statistic distributions of POINTS a GOALS made in a real championship, adapted to the limits and features of the in-game mechanics.

UEFA TAB
- Actual participant teams can be selected by year (source https://kassiesa.net/uefa/data/)
- Stats can be randomized within a given range or directly edited



## Release

A standalone Windows executable is included. Python is not required for normal use.