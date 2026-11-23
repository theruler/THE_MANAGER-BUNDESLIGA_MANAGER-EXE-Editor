# -*- coding: utf-8 -*-

LANG_NAME = 'Deutsch'

TEXTS_DE = {'grp.manager': 'Manager',
 'grp.squad': 'Mannschaft',
 'grp.economy': 'Finanzen',
 'grp.league': 'Liga',
 'grp.cups': 'Pokale',
 'grp.clubs': 'Vereine',
 'grp.messages': 'Nachrichten',
 'pg.profile': 'Profil',
 'pg.history': 'Historie',
 'pg.stats': 'Statistiken',
 'pg.roster': 'Kader',
 'pg.players': 'Spieler',
 'pg.stadium': 'Stadion',
 'pg.loans': 'Kredite',
 'pg.sponsors': 'Sponsoren',
 'pg.standings': 'Tabelle',
 'pg.results': 'Ergebnisse',
 'pg.calendar': 'Spielplan',
 'pg.cup_state': 'Status',
 'pg.cup_ties': 'Paarungen',
 'pg.clubs': 'Vereinsdaten',
 'pg.series': 'Laufende Serien',
 'pg.records': 'Rekorde',
 'pg.versus': 'Direkte Duelle',
 'pg.messages': 'Nachrichten',
 'err.too_short': 'Datei zu kurz: kein BMP-Spielstand.',
 'err.bad_sig': 'Ungültige Signatur: kein BMP-Spielstand.',
 'err.chk1': 'Prüfsumme 1 ist falsch.',
 'err.chk2': 'Prüfsumme 2 ist falsch.',
 'err.truncated': 'Datei beschädigt oder abgeschnitten.',
 'err.verify': 'Gegenprüfung beim Wiedereinlesen fehlgeschlagen',
 'err.page': 'Fehler auf dieser Seite: {error}',
 'pos.gk': 'TW',
 'pos.df': 'ABW',
 'pos.mf': 'MIT',
 'pos.fw': 'STU',
 'tb.savegame': 'Spielstand:',
 'tb.folder': 'Ordner…',
 'tb.open': 'Datei öffnen…',
 'tb.save': '.MAN speichern',
 'tb.save_as': 'Speichern unter…',
 'tb.manager': 'Manager:',
 'ph.no_dir': 'Kein Ordner ausgewählt.\nMit „Datei öffnen…“ einen .MAN-Spielstand öffnen.',
 'ph.none': 'Keine .MAN-Datei gefunden in:\n{dir}',
 'ph.pick': '{n} .MAN-Datei(en) gefunden.\nWähle oben einen Spielstand aus der Liste, um ihn zu öffnen.',
 'dlg.title': 'Savegame-Editor',
 'dlg.folder': 'Ordner mit den .MAN-Spielständen',
 'dlg.open': 'Spielstand öffnen',
 'dlg.save_as': 'Spielstand speichern unter',
 'dlg.type_man': 'BMP-Spielstand',
 'dlg.type_all': 'Alle Dateien',
 'dlg.discard': '{name} hat ungespeicherte Änderungen. Verwerfen?',
 'dlg.roundtrip': 'Beim Öffnen war die Neucodierung NICHT identisch mit dem Original.\nTrotzdem speichern?',
 'dlg.save_failed': 'Speichern fehlgeschlagen:\n{error}',
 'status.none': 'Kein Spielstand geladen.',
 'status.loaded_ok': '{name}: Prüfsumme OK, Neucodierung identisch: ja',
 'status.loaded_warn': '{name}: Prüfsumme OK, Neucodierung identisch: NEIN – vorsichtig speichern',
 'status.saved': '{name} gespeichert, Prüfsummen neu berechnet{backup}.',
 'status.backup': ' (.bak-Sicherung erstellt)',
 'status.dirty': '● Ungespeicherte Änderungen',
 'mgr.item': 'Manager {n}: {name}',
 'c.club': 'Verein',
 'c.name': 'Name',
 'c.home': 'Heim',
 'c.away': 'Ausw.',
 'c.away_full': 'Auswärts',
 'c.home_team': 'Heimmannschaft',
 'c.away_team': 'Gastmannschaft',
 'lbl.league': 'Liga:',
 'lists.leagues': '1. Liga|2. Liga|3. Liga',
 'lists.titles': 'Meistertitel|Nationaler Pokal|Europapokal der Landesmeister|Europapokal der '
                 'Pokalsieger|UEFA-Pokal',
 'lists.cups': 'Nationaler Pokal|Europapokal der Landesmeister|Europapokal der Pokalsieger|UEFA-Pokal',
 'lists.sizes': 'Keine|Klein|Mittel|Groß',
 'lists.grade_1': '1 – Mangelhaft',
 'lists.grade_6': '6 – Hervorragend',
 'lists.records': 'Heimsiege|Heimniederlagen|Heimtore|Heimgegentore|Auswärtssiege|Auswärtsniederlagen|Auswärtstore|Auswärtsgegentore',
 'prof.identity': 'Identität und Kasse',
 'prof.name': 'Managername',
 'prof.cash': 'Kasse',
 'prof.date': 'Datum (T / M / Jahr)',
 'prof.level': 'Stufe (1–5)',
 'prof.mgmt': 'Teamführung',
 'prof.internal': 'Interne Werte',
 'prof.internal_items': 'Liga (0/1/2)|Relegation (Byte 265)|Saison-Flag (Byte 320)',
 'prof.note': 'Beim Wechsel des Vereins wird auch die Liga (0/1/2) angepasst.',
 'hist.palmares': 'Erfolge',
 'hist.seasons_played': 'Gespielte Saisons',
 'hist.titles': 'Titel: {name}',
 'hist.round': 'Aktuelle Runde: {name}',
 'hist.balance': 'Gesamtbilanz',
 'hist.balance_items': 'Punkte|Tore|Gegentore|Siege|Niederlagen|Unentschieden|Spiele gespielt|?432 (mit '
                       'Vorzeichen)',
 'hist.seasons': 'Saisons',
 'hist.add': '+ Saison hinzufügen',
 'hist.remove': '− Letzte entfernen',
 'hist.season_cols': 'Platz|Liga|Pokal|Europa',
 'hist.note': 'Max. 50 Saisons; eine neue Zeile kopiert die vorherige. Platz: 1–18 erste Liga, 19–38 zweite, '
              '39–58 dritte; 255 = noch nicht Manager. Bei Pokalen markiert Bit 7 (+128) den Sieg.',
 'stats.positions': 'Tabellenplatz je Spieltag',
 'stats.attendance': 'Zuschauer pro Spiel (Tausend)',
 'stats.series': 'Rekordserien des Managers (21 Werte)',
 'stats.note': 'Die Serienstatistik umfasst sieben Kategorien für Gesamt-, Heim- und Auswärtsspiele. Die '
               'Bytes 267–304 und 330–346 speichern den Spieltagsverlauf.',
 'squad.cols': 'Spieler|Position|Direkte Rote\n'
               '(+0)|Gelbe Karten\n'
               '(+1)|Gelb-Rote\n'
               '(+2)|Ligatore\n'
               '(+3)|Pokaltore\n'
               '(+4)|Europapokal-\n'
               'tore (+5)|Ligaeinsätze\n'
               '(+6)|Pokal-\n'
               'einsätze (+7)|Europa-\n'
               'einsätze (+8)|Statusflags\n'
               '(+9)|Trikotnummer\n'
               '(+10)|Vertrag\n'
               '(Saisons)\n'
               '(+11)|Leihe\n'
               '(+12)|Sperre /\n'
               'Verletzung\n'
               '(+13)',
 'squad.all99': 'Alle auf 99 (Kond/Tec/Form)',
 'squad.count': '{n} Spieler im Kader',
 'squad.note': 'Kondition, Technik und Form sind die aktuellen Kaderwerte; Frische liegt zwischen 50 und '
               '150. Der Vertrag ist in Saisons angegeben. Zähler +13 bedeutet bei einer Sperre Spiele und '
               'bei einer Verletzung Wochen. Doppelklick oder Eingabetaste zum Bearbeiten; Tab wechselt zur '
               'nächsten Zelle.',
 'pl.search': 'Suchen:',
 'pl.club': 'Verein:',
 'pl.all': 'Alle',
 'pl.cols': 'Spieler-\n'
            'name|Alter\n'
            '(Jahre)|Kondi-\n'
            'tion\n'
            '(aktuell)|Tech-\n'
            'ik\n'
            '(aktuell)|Form\n'
            '(aktuell)|Positions-\n'
            'code\n'
            '(0–99)|Positions-\n'
            'gruppe|Liga-\n'
            'tore|Liga-\n'
            'einsätze|Aktueller\n'
            'Verein',
 'pl.count': '{n} Spieler',
 'std.facilities': 'Anlagen',
 'std.ticket': 'Eintrittspreis',
 'std.lights': 'Flutlicht',
 'std.screen': 'Videoleinwand',
 'std.condition_stadium': 'Stadionzustand',
 'std.comfort': 'Komfort',
 'std.attendance': 'Zuschauer',
 'std.season_att': 'Saisonbesucher',
 'std.record_att': 'Zuschauerrekord',
 'std.record_opp': 'Gegner beim Rekord',
 'std.min_att': 'Zuschauerminimum',
 'std.min_opp': 'Gegner beim Minimum',
 'std.expansions': 'Stadionausbau',
 'std.exp_items': 'Sitzplätze|Stehplätze|Überdachte Plätze|Flutlicht|Videoleinwand|Zustand|Komfort',
 'std.above': '(oben)',
 'std.exp_cols': 'Posten|Aktuell|Im Bau|Verbleibende Tage',
 'std.note': 'Flutlicht, Videoleinwand, Zustand und Komfort werden im Feld „Anlagen“ eingestellt.',
 'loan.bank': 'Bank',
 'loan.lender': 'Geldgeber {n}',
 'loan.cols': 'Von|Betrag|Zinsen/Monat|Zinssatz %|Beginn|Fällig',
 'loan.note': 'Ein Betrag von null kennzeichnet einen inaktiven Kredit. Datumsformat: TT/MM/JJJJ. Beim '
              'Anlegen eines Kredits auch die Zinsen setzen (Betrag × Zinssatz / 100).',
 'sp.shirt': 'Trikot',
 'sp.board': 'Bande',
 'sp.tv': 'TV',
 'sp.adcost': 'Werbekosten',
 'sp.income': 'Werbeeinnahmen',
 'sp.item': 'Posten',
 'sp.amount': 'Betrag',
 'sp.contracts': 'Aktive Verträge',
 'sp.contract_cols': 'Fläche|Restmonate|Sponsor-Nr.',
 'sp.offers': 'Sponsorenangebote',
 'sp.offer_cols': 'Sponsor|Trikot: Jahre|Trikot: Betrag|Banden: Jahre|Banden: Betrag',
 'sp.note': 'Die Einnahmen stehen in der Werbetabelle des Managers. Vertrags- und Angebotsfelder sind im '
            'jeweiligen Datensatz gespeichert.',
 'st.resort': 'Neu sortieren',
 'st.cols': 'Verein|Punkte\n'
            'gesamt|Tordifferenz|Punkte\n'
            'Heim|Punkte\n'
            'Auswärts|Tore erzielt\n'
            'Heim|Tore erzielt\n'
            'Auswärts|Gegentore\n'
            'Heim|Gegentore\n'
            'Auswärts|Spiele\n'
            'Heim|Spiele\n'
            'Auswärts|Siege\n'
            'Heim|Siege\n'
            'Auswärts|Niederlagen\n'
            'Heim|Niederlagen\n'
            'Auswärts|Punkte\n'
            'gesamt historisch',
 'st.note': 'Gesamtpunkte sind die Summe aus Heim- und Auswärtspunkten; die Tordifferenz ergibt sich aus '
            'erzielten minus kassierten Toren. Die übrigen Spalten zeigen Heim- und Auswärtswerte getrennt. '
            'Sortiert wird nach Gesamtpunkten und danach nach Tordifferenz; „Neu sortieren“ aktualisiert die '
            'Reihenfolge.',
 'res.round': 'Spieltag {n}',
 'res.match': 'Spiel',
 'res.note': 'Der Spielstand speichert nur die Tore, nicht die Mannschaften vergangener Spieltage. 255 = '
             'nicht gespielt; 30 Heimtore = verlegtes Spiel.',
 'cal.season': 'Laufende Saison',
 'cal.day': 'Tag der Saison',
 'cal.next': 'Nächster Spieltag (Liga {n})',
 'cal.matches': 'Spiele des aktuellen Spieltags',
 'cal.note': 'Doppelklick auf eine Mannschaft, um sie aus der Liste zu wählen.',
 'cup.relegation': 'Relegation',
 'cup.first_leg': 'Hinspiel',
 'cup.outcome': 'Ergebnis (1 = Aufstieg)',
 'cup.round': 'Aktuelle Runde',
 'cup.legs_played': 'Hinspiel gespielt',
 'cup.qualified': 'Deutsche Europapokal-Teilnehmer (Liste)',
 'cup.slots': 'Europäische Plätze (3 × 6, 128 = frei)',
 'cup.label': 'Pokal:',
 'cup.goals_h': 'Tore H',
 'cup.goals_a': 'Tore A',
 'cup.first_leg_goals': 'Hinspiele Europapokale (Tore, 3 × 32)',
 'cup.note': 'Tore in Pokalrunden: +10 nach Verlängerung, +20 nach Elfmeterschießen.',
 'cl.search': 'Verein suchen:',
 'cl.cols': 'Basis|K1|K2|K3|T1|T2|T3|F1|F2|F3|Status',
 'cl.count': '{n} Vereine',
 'cl.note': 'K = Kondition, T = Technik, F = Form (je drei Werte). Indizes 0–17 erste Liga, 18–37 zweite, '
            '38–57 dritte, der Rest ausländische Vereine.',
 'ser.note': 'Die Tabelle enthält 21 Werte zu den laufenden Serien des Vereins.',
 'rec.none': 'Keine Vereine.',
 'rec.cols': 'Rekord|Wert (a:b)|Gegner',
 'rec.note': 'Vereinsrekorde und der jeweilige Gegner. Jedes Byte enthält zwei Werte von 0 bis 15, '
             'geschrieben als a:b.',
 'vs.note': 'Die letzten 5 Spiele des Managers gegen jeden Verein, als Gegentore:eigene Tore (max. 15 pro '
            'Zelle). Leere Zelle = kein Spiel.',
 'msg.manager': 'Manager {n} – {name}',
 'msg.none': 'Keine Nachrichten.',
 'msg.note': 'Das Zeichen ^ ist ein Zeilenumbruch. Du kannst den Text vorhandener Nachrichten ändern (max. '
             '240 Zeichen); Nachrichten hinzuzufügen oder zu löschen würde auch interne Zeiger betreffen und '
             'wird nicht unterstützt.',
 'grp.advanced': 'Erweitert',
 'pg.market': 'Transfermarkt',
 'pg.ext_standings': 'Erweiterte Tabelle',
 'pg.raw': 'Rohblöcke',
 'std.capacity': 'Gesamtkapazität (berechnet)',
 'loan.total': 'Gesamtschulden',
 'loan.interest_total': 'Zinsen pro Monat gesamt',
 'squad.avg': 'Kaderschnitt – Kond {c} · Tec {t} · Form {f}',
 'squad.extra_cols': 'Trainings-\n'
                     'faktor\n'
                     '(+14)|Spieler-\n'
                     'index\n'
                     '(+15)|Kondition\n'
                     '(+16)|Technik\n'
                     '(+17)|Form\n'
                     '(+18)|Frische\n'
                     '(+19)|Trainings-\n'
                     'programm\n'
                     '(+20)|Spiel-\n'
                     'bewertung\n'
                     '(+21, i8)|Anbietender\n'
                     'Verein\n'
                     '(+22)|Verletzungs-\n'
                     'art\n'
                     '(+23)|Vertrag /\n'
                     'Karriere\n'
                     '(+24)|Horizontale\n'
                     'Koordinate X\n'
                     '(i8, +25)|Tiefe\n'
                     'Koordinate Y\n'
                     '(u8, +26)|Byte +27\n'
                     '(unbekannt)|Liga-\n'
                     'einsätze\n'
                     '(+28, u16)|Pokal-\n'
                     'einsätze\n'
                     '(+30, u16)|Europa-\n'
                     'einsätze\n'
                     '(+32, u16)|Liga-\n'
                     'tore\n'
                     '(+34, u16)|Pokal-\n'
                     'tore\n'
                     '(+36, u16)|Europa-\n'
                     'tore\n'
                     '(+38, u16)|Monats-\n'
                     'gehalt\n'
                     '(i32, +40–43)|Bytes +44–47\n'
                     '(unbekannt)|Meldungs-\n'
                     'zeiger\n'
                     '(i32, +48)',
 'pl.extra_cols': 'Anfangs-\ndurchschnitt\n(+27)|Seiten-\nvorliebe\n(+32)|Besitzer /\nMarktstatus\n(+33)',
 'squad.extra_note': 'Monatsgehalt: vorzeichenbehaftete 32-Bit-Zahl in den Bytes +40–43. Für die Bytes '
                     '+44–47 ist keine Funktion zugeordnet.',
 'pl.note': '+27 = Anfangsmittel aus Kondition, Technik und Form; der Wert folgt nicht den aktuellen '
            'Eigenschaften. +32 (0–6) = Seitenpräferenz für die automatische Wahl der horizontalen Position. '
            '+33: 0–3 Manager, 4 Transfermarkt, 5 frei. Rolle +31: 0–24 Torwart, 25–49 Abwehr, 50–74 '
            'Mittelfeld, 75–99 Sturm.',
 'pl.owner_market': 'Transfermarkt',
 'pl.owner_free': 'Frei',
 'mk.cols': 'Spieler|Position|Angebots-\n'
            'ablehnungen\n'
            '(+3)|Statusflags\n'
            '(+9)|Leihe\n'
            '(+12)|Sperre /\n'
            'Verletzung\n'
            '(+13)|Trainings-\n'
            'faktor\n'
            '(+14)|Spieler-\n'
            'index\n'
            '(+15)|Kondition\n'
            '(+16)|Technik\n'
            '(+17)|Form\n'
            '(+18)|Frische\n'
            '(+19)|Trainings-\n'
            'programm\n'
            '(+20)|Spiel-\n'
            'bewertung\n'
            '(i8, +21)|Anbietender\n'
            'Verein\n'
            '(+22)|Verletzungs-\n'
            'typ\n'
            '(+23)|Verhandlung /\n'
            'Karriere\n'
            '(+24)|Byte +27\n'
            '(unbekannt)|Marktwert\n'
            '(i32, +40)|Bytes +44–47\n'
            '(unbekannt)|Meldungs-\n'
            'zeiger\n'
            '(i32, +48)',
 'mk.count': '{n} Spieler gelistet',
 'mk.note': 'Der Markt verwendet die Plätze 100–111. +40–43 = Geldwert (i32); +3 = abgelehnte Angebote je '
            'Manager; +9 = Statusbits; +12 = Leihe; +13 = Sperrspiele oder Verletzungswochen; +22 = '
            'anbietender Verein; +23 = Verletzungsart; +14 und +20 = Training; +21 = Spielbewertung; +24 = '
            'Vertrags-/Karrierestatus; +27 und +44–47 = nicht zugeordnete Felder; +48–51 = '
            'Nachrichtenzeiger.',
 'xs.cols': 'Serie A (b4–11)|Serie B (b13–20)|?2|?3|?24|?25|?28|?29|?40|?41|?44|?45|?46|b32–37',
 'xs.note': 'Vollständiger Tabellen-Datensatz mit 54 Byte je Verein. Die beiden Hexadezimalreihen enthalten '
            'je Byte zwei 4-Bit-Werte.',
 'cal.perm': 'Auslosungsreihenfolge des Spielplans (20 Werte je Liga)',
 'cal.perm_note': 'Permutation der Mannschaftsplätze für den Spielplan (1. Liga 0–19, 2. 20–39, 3. 40–59). '
                  'Änderungen wirken auf künftige Spieltage.',
 'raw.block5': 'Nachholspiele: 20 Datensätze × 5 Byte (5457–5556)',
 'raw.cols5': 'Kennung\n(+0)|Tagesindex\n(+1)|Spieltag\n(+2)|Liga\n(+3)|Spielindex\n(+4)',
 'raw.tail1': 'Unbekannte Datenbereiche 34063–34221',
 'raw.tail2': 'Kalender- und Folgedaten 34226–34366',
 'raw.note': 'Offsets sind absolute Positionen im dekodierten Puffer. Byte 34367 wird auf der Pokalseite '
             'angezeigt; Meldungen ab 34368 stehen auf der Meldungsseite.',
 'std.home_games': 'Gespielte Heimspiele',
 'std.avg_att': 'Zuschauerschnitt (berechnet)',
 'prof.mgmt_items': 'Spielintensität (0–34)|Jugendförderung (0–34)|Bälle: Kondition|Bälle: Spiel|Bälle: '
                    'Schuss|Bälle: Taktik|Moral (0–40)|Spiele mit '
                    'Zuschauern|Trainingsintensität|Torwarttraining|Abwehrtraining|Mittelfeldtraining|Angriffstraining',
 'prof.portrait_id': 'Porträt (1–4)',
 'prof.extra': 'Weitere Felder',
 'prof.extra_item': 'Byte +{off}',
 'prof.extra_note': '+480 und +482 sind getrennte 16-Bit-Werte. +480 wird vom Spiel neu berechnet; +482 hat '
                    'keine zugewiesene Bedeutung. Für die übrigen Felder liegt keine Beschreibung vor.',
 'stats.chart': 'Zuschauerverlauf',
 'pg.options': 'Spieloptionen',
 'opt.panel': 'Spieloptionen (EIN/AUS)',
 'opt.series': '1. Liga|2. Liga|3. Liga',
 'opt.items': 'Halbzeitergebnisse|Endergebnisse|Tabelle',
 'opt.others': 'Spielaktionen|Nationaler Pokal|Europapokale|Nachholspiele|Zeitung|Überblendungen',
 'opt.other': 'Weitere Optionen',
 'opt.speed': 'Spielgeschwindigkeit',
 'opt.speed_byte': 'Geschwindigkeit (0–70)',
 'opt.note': 'Mit den Kontrollkästchen werden die jeweiligen Anzeigeoptionen ein- oder ausgeschaltet.',
 'info.version': 'Version',
 'info.unknown': 'unbekannt',
 'info.edited': 'MIT DEM EDITOR BEARBEITET',
 'info.ingame': 'im Spiel',
 'info.bmp_ita_mod': 'ITA-Mod auf deutscher EXE',
 'raw.recovery_note': 'Die 20 Datensätze zu je fünf Byte beschreiben Nachholspiele: Kennung, Tagesindex, '
                      'Spieltag, Liga und Spiel.',
 'raw.unknown_area': 'Zusatzdaten und nicht zugeordnete Bereiche (34063–34221)',
 'raw.unknown_34063': '34063–34064 · 2 nicht entschlüsselte Bytes',
 'raw.unknown_34065': '34065–34094 · 30 nicht entschlüsselte Bytes',
 'raw.unknown_34095': '34095–34098 · 4 nicht entschlüsselte Bytes',
 'raw.unknown_34215': '34215–34221 · 7 nicht entschlüsselte Bytes',
 'raw.calendar_title': 'Kalenderindex und Liga-Spielplanmaske (34226–34321)',
 'raw.calendar_index': 'Aktueller Index (Byte 34226)',
 'raw.calendar_index_note': 'Das Spiel verwendet dieses Byte als Index für einen Eintrag der folgenden '
                            'Tabelle. Es ist nicht die angezeigte Spieltagsnummer.',
 'raw.calendar_mask': 'Fortschrittsmaske der drei Ligen · 95 Byte (34227–34321)',
 'raw.daily_words': 'Acht 16-Bit-Werte, die sich im Tagesablauf ändern (34322–34337)',
 'raw.trailing_values': 'Weitere Werte im Endblock (34338–34366)',
 'raw.unknown_byte': 'Nicht entschlüsseltes Byte (34338)',
 'raw.offset': 'Offset',
 'raw.word_value': '16-Bit-Wert',
 'raw.dword_value': '32-Bit-Wert',
 'mark.name': 'SCHUMMLER',
 'tip.generic': 'Information about the “{label}” column. Hover here for details about the represented field.',
 'tip.value_column': '{description} Column {column}: value in the same position of each row in this data '
                     'block.',
 'tip.unknown_values': 'Consecutive values from a data block whose meaning has not been decoded.',
 'tip.index': 'Sequential index of the displayed row or slot.',
 'tip.balance_item': 'Overall team-balance item; its exact meaning is shown in the first column.',
 'tip.home_total': 'Total for matches played at home.',
 'tip.away_total': 'Total for matches played away.',
 'tip.season_position': 'Final position achieved by the manager in the selected season.',
 'tip.season_league': 'Season result in the league.',
 'tip.season_cup': 'Season result in the domestic cup.',
 'tip.season_europe': 'Season result in European competitions.',
 'tip.positions_by_round': 'Manager league-table position after each matchday. Each value corresponds to one '
                           'round.',
 'tip.attendance_by_match': 'Attendance for the corresponding match, stored in thousands.',
 'tip.series_unverified': 'Wert in der Serienstatistik des Managers.',
 'tip.player_index': 'Index des verknüpften Spielers in der 151 Einträge großen Spielertabelle; gespeichert '
                     'in Kaderbyte +15.',
 'tip.unknown_bytes42': 'Kaderplatz-Bytes +42–43; Funktion nicht zugeordnet.',
 'tip.player': 'Player name linked to this squad or transfer-market slot.',
 'tip.role_group': 'Role group derived from the player position code: goalkeeper, defender, midfielder or '
                   'forward.',
 'tip.shirt_number': 'Shirt number assigned to the player.',
 'tip.condition_current': 'Player current condition in the squad.',
 'tip.technique_current': 'Player current technique value.',
 'tip.form_current': 'Player current form.',
 'tip.freshness': 'Current freshness/fatigue value, stored separately from condition, technique and form.',
 'tip.monthly_wage': 'Monatsgehalt des Spielers. Die Routinen für Spieleranlage und Vertrag lesen und '
                     'schreiben das vollständige 32-Bit-Feld +40–43; records.ts stellt dagegen nur einen '
                     'u16-Zugriff auf +40–41 bereit. Der Editor zeigt den vollständigen i32-Wert.',
 'tip.contract_seasons': 'Contract duration expressed in seasons.',
 'tip.suspension_injury': 'Remaining suspension matches or injury weeks. The event type is indicated by the '
                          'status flags.',
 'tip.yellow_cards': 'Number of yellow cards recorded for the player.',
 'tip.direct_reds': 'Number of direct red cards recorded for the player.',
 'tip.league_goals': 'Goals scored by the player in the league.',
 'tip.league_appearances': 'Player appearances in the league.',
 'tip.training_factor': 'Individual factor modifying training effectiveness; 50 is the neutral factor.',
 'tip.training_program': 'Trainingsprogramm in Bitfeldern: Restdauer, Stärke und Änderungsrichtung.',
 'tip.pitch_column': 'Horizontale X-Koordinate im Kaderplatz-Byte +25. Das Spiel interpretiert sie als int8; '
                     'automatische Formationen beginnen bei den Spalten 0–6 und können sie gemäß '
                     'Seitenvorliebe des Spielers tauschen.',
 'tip.pitch_line': 'Tiefenkoordinate Y im Kaderplatz-Byte +26 (0–7): 0 zum gegnerischen Tor, 7 zum eigenen '
                   'Tor. Spieler derselben Linie teilen normalerweise eine Tiefe, mit kleinen '
                   'formationsabhängigen Verschiebungen.',
 'tip.apps_league': '16-bit counter of league appearances.',
 'tip.apps_cup': '16-bit counter of domestic-cup appearances.',
 'tip.apps_europe': '16-bit counter of European-cup appearances and play-offs according to the game routine.',
 'tip.goals_cup': '16-bit counter of goals in the domestic cup.',
 'tip.goals_europe': '16-bit counter of goals in European competitions.',
 'tip.second_yellow': 'Dismissals caused by a second yellow card.',
 'tip.state_flags': 'Status bitmask: bit 0 suspension, bit 1 injury, bit 6 offer for a manager-owned player, '
                    'bit 7 manager-owned player on the market.',
 'tip.loan': 'Loan information: owning club is encoded in byte +12, with flag 0x80 used to distinguish loan '
             'status.',
 'tip.match_rating': 'Signed rating earned in the most recent match; reset before the next match.',
 'tip.offering_club': 'Index of the club that made an offer for the player.',
 'tip.injury_type': 'Numeric injury-type code. The code remains stored after recovery.',
 'tip.contract_status': 'Negotiation state: 0–99 is the waiting counter before new approaches; 100 or more '
                        'indicates a pending renewal offer; bit 7 signals retirement.',
 'tip.unknown_byte27': 'Kaderplatz-Byte +27; Funktion nicht zugeordnet.',
 'tip.unknown_bytes44': 'Kaderplatz-Bytes +44–47; Funktion nicht zugeordnet.',
 'tip.notification_pointer': '32-bit reference to a notification associated with the player.',
 'tip.age': 'Player age in years.',
 'tip.condition_base': 'Condition value in the player master record; it is not necessarily the current squad '
                       'condition.',
 'tip.technique_base': 'Technique value in the player master record.',
 'tip.form_base': 'Form value in the player master record.',
 'tip.position_value': 'Position code from 0 to 99: 0–24 goalkeeper, 25–49 defender, 50–74 midfielder, 75–99 '
                       'forward.',
 'tip.current_club': 'Club currently associated with the player master record.',
 'tip.initial_average': 'Initial average (condition + technique + form) / 3, stored at creation and not '
                        'updated with current attributes.',
 'tip.preferred_side': 'Seitenpräferenz des Spielers (0–6), die bei der automatischen Formation die '
                       'horizontale Position beeinflusst.',
 'tip.owner': 'Player owner/state: 0–3 managers, 4 transfer market, 5 unattached player.',
 'tip.market_value': 'Player transfer price/value, stored as a signed 32-bit integer.',
 'tip.offer_refusals': 'Manager offer refusals, encoded in the bits of byte +3.',
 'tip.stadium_item': 'Stadium facility or section affected by the expansion.',
 'tip.current_value': 'Current value of the facility or stadium section.',
 'tip.work_in_progress': 'Facility value after completion, or the level currently being built.',
 'tip.days_remaining': 'Number of days remaining until construction is completed.',
 'tip.lender': 'Loan provider: the bank or another manager.',
 'tip.loan_number': 'Sequential loan number for that lender.',
 'tip.loan_amount': 'Loan principal, stored as a 32-bit value.',
 'tip.monthly_interest': 'Interest amount payable each month.',
 'tip.interest_rate': 'Percentage rate applied to the loan principal.',
 'tip.start_date': 'Loan start date; the month is stored from 0 to 11 in the file.',
 'tip.end_date': 'Loan maturity date; the month is stored from 0 to 11 in the file.',
 'tip.sponsor_item': 'Advertising-income item recorded for the manager.',
 'tip.amount': 'Economic amount associated with the item or contract.',
 'tip.sponsor_slot': 'Slot reserved for the sponsor contract.',
 'tip.months_remaining': 'Months remaining on the advertising contract.',
 'tip.sponsor_count': 'Sponsor number/code associated with the slot.',
 'tip.sponsor': 'Sponsor index or identifier in the offer.',
 'tip.shirt_years': 'Offer duration in years for shirt sponsorship.',
 'tip.shirt_amount': 'Amount offered for shirt sponsorship.',
 'tip.boards_years': 'Offer duration in years for advertising boards.',
 'tip.boards_amount': 'Amount offered for advertising boards.',
 'tip.club': 'Club name to which the row data refers.',
 'tip.points': 'Total league points, calculated from home and away points.',
 'tip.goal_difference': 'Total goal difference, calculated as goals for minus goals against.',
 'tip.home_points': 'Points earned in home matches.',
 'tip.away_points': 'Points earned in away matches.',
 'tip.home_goals_for': 'Goals scored at home.',
 'tip.away_goals_for': 'Goals scored away.',
 'tip.home_goals_against': 'Goals conceded at home.',
 'tip.away_goals_against': 'Goals conceded away.',
 'tip.home_games': 'Matches played at home.',
 'tip.away_games': 'Matches played away.',
 'tip.home_wins': 'Wins achieved at home.',
 'tip.away_wins': 'Wins achieved away.',
 'tip.home_losses': 'Losses suffered at home.',
 'tip.away_losses': 'Losses suffered away.',
 'tip.historical_points': 'Additional historical field stored in the club record; it is not included in the '
                          'calculated points total above.',
 'tip.match_no': 'Sequential match number in the selected matchday.',
 'tip.home_goals': 'Goals scored by the home team in the match.',
 'tip.away_goals': 'Goals scored by the away team in the match.',
 'tip.score_separator': 'Visual separator between the home and away score.',
 'tip.home_team': 'Club listed as the home team in the fixture.',
 'tip.away_team': 'Club listed as the away team in the fixture.',
 'tip.calendar_order': 'Permutation entry used by the game to build future calendar matchdays.',
 'tip.european_qualifiers': 'Index of a club qualified for European competitions, as stored in the savegame '
                            'list.',
 'tip.european_places': 'European-place slot; 128 indicates an empty slot.',
 'tip.club_name': 'Club name in the savegame club database.',
 'tip.club_base': 'Base value of the club in its master record.',
 'tip.club_condition_home': 'Club condition value in the first entry of the series.',
 'tip.club_condition_away': 'Club condition value in the second entry of the series.',
 'tip.club_condition_third': 'Club condition value in the third entry of the series.',
 'tip.club_technique_home': 'Club technique value in the first entry of the series.',
 'tip.club_technique_away': 'Club technique value in the second entry of the series.',
 'tip.club_technique_third': 'Club technique value in the third entry of the series.',
 'tip.club_form_home': 'Club form value in the first entry of the series.',
 'tip.club_form_away': 'Club form value in the second entry of the series.',
 'tip.club_form_third': 'Club form value in the third entry of the series.',
 'tip.club_status': 'Statuscode des Vereins.',
 'tip.external_series_a': '8-byte hexadecimal block associated with Series A; each byte contains two 4-bit '
                          'values.',
 'tip.external_series_b': '8-byte hexadecimal block associated with Series B; each byte contains two 4-bit '
                          'values.',
 'tip.club_record_unknown': 'Byte +{offset} des 54-Byte-Vereinsdatensatzes.',
 'tip.club_record_tail': 'Hexadezimalwerte der Vereinsdatensatz-Bytes +32–37.',
 'tip.raw_record_byte': 'Byte +{offset} of the raw 5-byte record shown in this table.',
 'tip.raw_block_values': 'Aufeinanderfolgende Werte des Datenblocks ab Offset {start}.',
 'tip.series_column': 'Wert {number} in der Serienstatistik des Vereins.',
 'tip.record': 'Name of the record held by the club.',
 'tip.record_value': 'Record value shown as a pair of numbers from 0 to 15 (a:b).',
 'tip.record_opponent': 'Opponent club associated with the record.',
 'tip.versus_home': 'One of the manager’s last 5 matches against this club, played at home. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'tip.versus_away': 'One of the manager’s last 5 matches against this club, played away. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'squad.hint': 'Gespeicherte Feldpositionen: +25 = horizontales X (i8); +26 = Tiefe Y (0–7: 0 zum '
               'gegnerischen Tor, 7 zum eigenen Tor). Rückennummern 1–11 kennzeichnen die Startelf. Das '
               'System des Managers steht bei Byte 51 + 2 × Managerindex: 1 manuell, 2 = 4-4-2, 3 = 3-5-2, 4 '
               '= 3-4-3; das Folgebyte ist die Sicherung. Doppelklick oder Enter bearbeitet eine Zelle; Tab '
               'wechselt weiter.',
 'pl.hint': 'All players in the savegame. Headings describe the player master-record fields and current '
            'values.',
 'mk.hint': 'The transfer market uses slots 100–111. Hover over a heading to read the extended field '
            'description.',
 'tip.european_first_leg_goals': 'Goals from the first-leg matches in European competitions, stored in the '
                                 'cup-results block.',
 'squad.formation_info': 'Gespeichertes System: {active} · Sicherung: {backup}',
 'squad.system_manual': 'Manuell',
 'squad.system_unknown': 'Unbekannt ({value})',
 'opt.items_full': 'Halbzeitergebnisse · 1. Liga|Endergebnisse · 1. Liga|Tabelle · 1. '
                   'Liga|Halbzeitergebnisse · 2. Liga|Endergebnisse · 2. Liga|Tabelle · 2. '
                   'Liga|Halbzeitergebnisse · 3. Liga|Endergebnisse · 3. Liga|Tabelle · 3. '
                   'Liga|Torszenen|Nationaler Pokal|Europapokale|Nachholspiele|Zeitung|Überblendungen',
 'opt.option_name': 'Option',
 'opt.raw_byte': 'Status',
 'tip.runtime_option': 'Anzeigeschalter im Spieloptionen-Menü.',
 'tip.runtime_option_value': 'Status des Anzeigeschalters.',
 'opt.speed_value': 'Geschwindigkeit (0–70)',
 'opt.speed_note': 'Zulässiger Bereich: 0–70. Standardwert: 40.',
 'tip.speed_runtime': '16-Bit-Wert der Spielgeschwindigkeit (0–70).',
 'raw.game_type': 'Spieltyp und Spieldauer (34063–34064)',
 'raw.end_year_code': 'Typ-/Dauercode (u16)',
 'raw.end_year_meaning': 'Bedeutung',
 'raw.endyear_endless_historical': 'Endlosspiel · historischer Start',
 'raw.endyear_endless': 'Endlosspiel · normaler Start',
 'raw.endyear_one_historical': '1-Jahres-Spiel · historischer Start',
 'raw.endyear_one': '1-Jahres-Spiel · normaler Start',
 'raw.endyear_three_historical': '3-Jahres-Spiel · historischer Start',
 'raw.endyear_three': '3-Jahres-Spiel · normaler Start',
 'raw.endyear_other': 'Unbekannter Wert ({value})',
 'raw.rule_2026': 'Regelauswahl (34099)',
 'raw.rule_value': 'Regelwerk',
 'raw.rules_original': 'Regeln 1993',
 'raw.rules_2026': 'Regeln 2026',
 'raw.poach_counts': 'Transfers zwischen Managern (34100–34115)',
 'raw.manager_number': 'Manager {n}',
 'raw.poacher': 'Abwerbender Manager',
 'raw.owner_manager': 'Besitzer {n}',
 'raw.poach_note': 'Anzahl abgeschlossener Transfers für jede Kombination aus kaufendem und besitzendem '
                   'Manager.',
 'raw.unknown_34116_label': 'Nicht entschlüsseltes Byte (+34116)',
 'raw.debt_mask': 'Kaufsperren-Bitmaske (+34117)',
 'raw.derby_stakes': 'Derby-Einsatz je Manager (34118–34121)',
 'raw.derby_levels': '50.000 DM|100.000 DM|250.000 DM|500.000 DM',
 'raw.manager': 'Manager',
 'raw.stake': 'Einsatzstufe',
 'raw.youth_counts': 'Jugendzähler (34122–34129)',
 'raw.promotions': 'Jugendspieler in die erste Mannschaft',
 'raw.youth_poached': 'Abgeworbene frisch beförderte Spieler',
 'raw.youth_note': 'Werte je Manager: in die erste Mannschaft beförderte Jugendspieler und an andere Manager '
                   'abgegebene Jugendspieler. Die Zähler werden zum Saisonwechsel zurückgesetzt.',
 'raw.unknown_34130': '34130–34214 · 85 nicht entschlüsselte Bytes',
 'raw.stadium_lockout': 'Sperrtage je Stadionausbauart (34215–34221)',
 'raw.speed_snapshot': 'Spielgeschwindigkeits-Wort (34222–34223)',
 'raw.speed_value': 'Geschwindigkeit (0–70)',
 'tip.raw_34063': '16-Bit-Wert für Spieltyp und Spieldauer. Bekannte Werte: 22222/22251 = unbegrenzt; '
                  '1964/1993 = ein Jahr; 1966/1995 = drei Jahre. Die Varianten unterscheiden historischen '
                  'und normalen Start.',
 'tip.raw_34065': '30-Byte-Bereich (34065–34094) ohne zugewiesene Funktion.',
 'tip.raw_34095': 'Vier Bytes (34095–34098) vor der Regelauswahl; Funktion nicht zugeordnet.',
 'tip.rule_2026': '0 = Regeln 1993; 1 = Regeln 2026.',
 'tip.poach_count_row': 'Kaufender Manager (Zeile). Die vier Zellen zeigen den besitzenden Manager.',
 'tip.poach_count': 'Anzahl abgeschlossener Transfers für diese Kombination aus kaufendem und besitzendem '
                    'Manager.',
 'tip.debt_mask': 'Kaufsperrmaske wegen Schulden: ein Bit je Manager. Schwelle: Kontostand unter −1.000.000 '
                  'DM.',
 'tip.manager_index': 'Managerindex von 0 bis 3.',
 'tip.derby_stake': 'Derbyeinsatz: 0 = 50.000 DM, 1 = 100.000 DM, 2 = 250.000 DM, 3 = 500.000 DM.',
 'tip.youth_promotions': 'Anzahl der in dieser Saison in die erste Mannschaft beförderten Jugendspieler '
                         'dieses Managers.',
 'tip.youth_poach': 'Anzahl der beförderten Jugendspieler, die in dieser Saison zu einem anderen Manager '
                    'wechselten.',
 'tip.raw_34130': '85-Byte-Bereich (34130–34214) ohne zugewiesene Funktion.',
 'tip.stadium_lockout': 'Sieben Sperrtage-Zähler für Stadionausbauarten. Der Originalcode setzt nach '
                        'Ablehnung eines Ausbauangebots zufällig 15–55 Sperrtage. Der Basisoffset 34215 ist '
                        'bekannt; die genaue Zuordnung der sieben Indizes zu den Ausbauarten bleibt '
                        'vorsichtig zu behandeln.',
 'raw.training_camps': 'Verfügbarkeit der 8 Trainingslager (34322–34337)',
 'raw.camp_number': 'Lager',
 'raw.camp_status': 'Verfügbarkeit',
 'raw.camp_counter': 'Restzähler (i16)',
 'raw.camp_open_days': 'Geöffnet · {days} Tage',
 'raw.camp_closed_days': 'Geschlossen · {days} Tage',
 'raw.camp_changeover': 'Statuswechsel',
 'raw.camp_note': 'Acht vorzeichenbehaftete 16-Bit-Werte, je einer pro Trainingsplatz. Negativ = geöffnet; '
                  'positiv = geschlossen. Der Zähler bewegt sich täglich um eins auf null zu; bei null '
                  'startet er mit umgekehrtem Vorzeichen und 20–70 Tagen neu.',
 'tip.camp_number': 'Index des Trainingsplatzes (1–8).',
 'tip.camp_status': 'Negativ = geöffnet; positiv = geschlossen; null = Wechsel. Der Absolutwert gibt die '
                    'Resttage an.',
 'tip.camp_counter': 'Vorzeichenbehafteter 16-Bit-Wert bei Offset 34322 + 2 × Index. Sinkt täglich bis null '
                     'und startet dann mit umgekehrtem Vorzeichen und 20–70 Tagen neu.',
 'tip.daily_word': 'Vorzeichenbehafteter 16-Bit-Verfügbarkeitszähler eines Trainingsplatzes.',
 'tip.recovery_marker': 'Byte +0: Kennung des Nachholspiel-Datensatzes.',
 'tip.recovery_day_index': 'Byte +1: Kalender-Tagesindex des Nachholspiels.',
 'tip.recovery_matchday': 'Byte +2: ursprünglicher Ligaspieltag.',
 'tip.recovery_league': 'Byte +3: Ligaindex (0, 1 oder 2).',
 'tip.recovery_fixture': 'Byte +4: Spielindex innerhalb des Spieltags.',
 'tip.raw_34215': 'Sieben Tageszähler für Sperrzeiten bei Stadionerweiterungen.',
 'tip.calendar_mask': 'Binärtabelle mit 95 Byte. Index +34226 wählt das aktuelle Byte; die Bits bestimmen, '
                      'welche Ligen zum nächsten Spieltag wechseln.',
 'raw.additional_fields': 'Weitere Zusatzfelder (34116–34129)'}
