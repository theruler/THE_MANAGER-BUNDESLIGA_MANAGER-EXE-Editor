# THE MANAGER / Bundesliga Manager Professional Editor

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
- VGA/CP editor



## String editor

Strings can be modified and enlarged at will.

<img width="1177" height="849" alt="immagine" src="https://github.com/user-attachments/assets/24e366be-eae2-48d2-8d3c-06d7b69e9662" />


## Font Editor
Fonts can be freely modified and remapped, the string editor will interpret and show the mapped character, while converting the hex value into the string.
Accented letters can be modified and replaced. Width of the single char can be adjusted.
<img width="1280" height="851" alt="image" src="https://github.com/user-attachments/assets/12317ce8-f358-49d2-b196-69476d404c69" />


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

## Starting Year and Points per victory rule

The starting year and the points rule can be changed directly from the top bar of the editor for all supported executable profiles.


## Newspaper built-in visual editor

A visual newspaper editor can be selected to better edit the lines. Tags can be moved, deleted or added.

<img width="1177" height="973" alt="immagine" src="https://github.com/user-attachments/assets/a94d8583-b036-484b-b420-5fddad49dd67" />


## Executable extension option

To make more room for the strings and newspaper, an option to enlarge the original executables has been added for all the supported versions.


## MANA.DAT editor

Usable as standalone or a built-in main editor TAB 

LEGAUE TAB
- Teams can be swapped by dragging the buttons to new position
- RESET puts every stat to zero
- SHUFFLE shuffles the teams within each league
- RANDOMIZE randomizes all the stats based on current team position in each league, according to an algorithm that take sin account actual statistic distributions of POINTS a GOALS made in a real championship, adapted to the limits and features of the in-game mechanics.

<img width="1229" height="719" alt="immagine" src="https://github.com/user-attachments/assets/f9f46d47-1993-49db-98bd-9341f1bdccff" />

UEFA TAB
- Actual participant teams can be selected by year (source https://kassiesa.net/uefa/data/)
- Stats can be randomized within a given range or directly edited

<img width="1226" height="717" alt="immagine" src="https://github.com/user-attachments/assets/fe6f69a7-fa20-4a29-8909-4c6f8b2e9a0b" />

## VGA/CP editor

Usable as standalone or a built-in main editor TAB, it supports all graphic formats and compression.

<img width="1065" height="839" alt="immagine" src="https://github.com/user-attachments/assets/ecc3c0bb-70c7-4800-a526-480ca29ea440" />

## Usage

1. Open a supported EXE.
2. Make the required changes.
3. Review them with **Changes / Details**.
4. Save the modified executable with **Save As**.

Modified EXEPACK executables are saved unpacked. The editor does not contain an EXEPACK compressor.
Always keep a backup of the original executable and test modified executables before regular use.


## Release

Standalone Windows executables included. Python is not required for normal use.
