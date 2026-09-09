# Newspaper CSV – Quick Guide

The Newspaper CSV is designed so you can translate the newspaper without having to deal with BMP's internal `%x`, `#`, `%e`, etc. syntax yourself.

## 1. Export the CSV

Open the extended BMP v2.0 EXE in the editor and choose:

**Export Newspaper CSV**

Save the exported `newspaper.csv` wherever you want.

The CSV contains all 179 newspaper strings, split into 635 component rows for easier translation.

## 2. Where to enter your translation

Only edit the:

`translated_text`

column.

Do not modify:

* `string_id`
* `block`
* `component_id`
* `parent_id`
* `selector`
* `branch_index`
* `condition`
* `context`
* `source_text`
* `note`

If `translated_text` is left empty, the original `source_text` will be kept.

## 3. Keep the [[...]] markers

You will see markers such as:

`[[TEAM_A]]`
`[[TEAM_B]]`
`[[PLAYER_1]]`
`[[PLAYER_2]]`
`[[MANAGER]]`
`[[SCORE_0]]`
`[[SCORE_1]]`
`[[BREAK]]`
`[[SEL:S01]]`

These replace BMP's internal control codes.

Do not delete, rename or duplicate them.

You may move them inside the same translated line if this is necessary for natural Italian word order.

Example:

Source:

`[[TEAM_A]] BESIEGT [[TEAM_B]]`

Translation:

`[[TEAM_B]] VIENE SCONFITTA DA [[TEAM_A]]`

This is valid because both markers are still present.

## 4. Selection blocks

A marker such as:

`[[SEL:S01]]`

represents an internal BMP selection block.

You do not have to reconstruct it yourself.

The different possible texts inside that selection are listed as separate CSV rows. Translate those rows individually.

The editor rebuilds the original `%x...#...#%` structure automatically during import.

## 5. Do not use % or #

Do not manually write BMP control codes such as:

`%a`
`%b`
`%e`
`%x...`

Also avoid literal `%` and `#` characters in `translated_text`.

The editor generates all required BMP control syntax automatically.

## 6. Word length

A single word may contain a maximum of **49 characters**.

Normal sentences may of course be much longer.

The extended EXE provides an additional **19 KB string pool**, so translated newspaper texts can be considerably longer than the original German texts.

If the original B1/B3 blocks become full, the editor automatically moves suitable newspaper strings into the extended pool.

You do not have to manage this manually.

## 7. Import

When the translation is finished:

1. Save the CSV.
2. Open the extended BMP v2.0 EXE in the editor.
3. Choose **Import Newspaper CSV**.
4. Select your edited CSV.

The editor then:

* checks the CSV structure,
* checks all required markers,
* reconstructs BMP's internal newspaper syntax,
* checks the word-length limit,
* rebuilds the strings,
* uses the extended pool automatically if necessary,
* and validates everything before applying the changes.

If the CSV contains an invalid structure, the import is blocked instead of silently creating a broken newspaper string.

## In short

You only translate the normal text in `translated_text`.

Keep the `[[...]]` markers.

The editor handles the complicated BMP newspaper syntax and the additional string space automatically.