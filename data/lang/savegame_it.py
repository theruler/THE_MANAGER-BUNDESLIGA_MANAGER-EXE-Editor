# -*- coding: utf-8 -*-

LANG_NAME = 'Italiano'

TEXTS_IT = {'grp.manager': 'Manager',
 'grp.squad': 'Squadra',
 'grp.economy': 'Economia',
 'grp.league': 'Campionato',
 'grp.cups': 'Coppe',
 'grp.clubs': 'Club',
 'grp.messages': 'Messaggi',
 'pg.profile': 'Profilo',
 'pg.history': 'Storico',
 'pg.stats': 'Statistiche',
 'pg.roster': 'Rosa',
 'pg.players': 'Giocatori',
 'pg.stadium': 'Stadio',
 'pg.loans': 'Prestiti',
 'pg.sponsors': 'Sponsor',
 'pg.standings': 'Classifica',
 'pg.results': 'Risultati',
 'pg.calendar': 'Calendario',
 'pg.cup_state': 'Stato',
 'pg.cup_ties': 'Accoppiamenti',
 'pg.clubs': 'Dati club',
 'pg.series': 'Serie in corso',
 'pg.records': 'Record',
 'pg.versus': 'Scontri diretti',
 'pg.messages': 'Messaggi',
 'err.too_short': 'File troppo corto: non è un salvataggio BMP.',
 'err.bad_sig': 'Firma non valida: non è un salvataggio BMP.',
 'err.chk1': 'Checksum 1 errato.',
 'err.chk2': 'Checksum 2 errato.',
 'err.truncated': 'File danneggiato o troncato.',
 'err.verify': 'verifica di rilettura fallita',
 'err.page': 'Errore nella pagina: {error}',
 'pos.gk': 'POR',
 'pos.df': 'DIF',
 'pos.mf': 'CEN',
 'pos.fw': 'ATT',
 'tb.savegame': 'Savegame:',
 'tb.folder': 'Cartella…',
 'tb.open': 'Apri file…',
 'tb.save': 'Salva .MAN',
 'tb.save_as': 'Salva con nome…',
 'tb.manager': 'Manager:',
 'ph.no_dir': 'Nessuna cartella selezionata.\nUsa «Apri file…» per aprire un savegame .MAN.',
 'ph.none': 'Nessun file .MAN trovato in:\n{dir}',
 'ph.pick': "Trovati {n} file .MAN.\nSeleziona un savegame dall'elenco in alto per aprirlo.",
 'dlg.title': 'Savegame Editor',
 'dlg.folder': 'Cartella con i savegame .MAN',
 'dlg.open': 'Apri savegame',
 'dlg.save_as': 'Salva savegame con nome',
 'dlg.type_man': 'Savegame BMP',
 'dlg.type_all': 'Tutti i file',
 'dlg.discard': '{name} ha modifiche non salvate. Scartarle?',
 'dlg.roundtrip': "Alla apertura la ricodifica NON era identica all'originale.\nSalvare comunque?",
 'dlg.save_failed': 'Salvataggio non riuscito:\n{error}',
 'status.none': 'Nessun savegame caricato.',
 'status.loaded_ok': '{name}: checksum OK, ricodifica identica: sì',
 'status.loaded_warn': '{name}: checksum OK, ricodifica identica: NO – salvare con cautela',
 'status.saved': 'Salvato {name}, checksum ricalcolati{backup}.',
 'status.backup': ' (backup .bak creato)',
 'status.dirty': '● Modifiche non salvate',
 'mgr.item': 'Manager {n}: {name}',
 'c.club': 'Club',
 'c.name': 'Nome',
 'c.home': 'Casa',
 'c.away': 'Trasf.',
 'c.away_full': 'Trasferta',
 'c.home_team': 'Squadra di casa',
 'c.away_team': 'Squadra ospite',
 'lbl.league': 'Lega:',
 'lists.leagues': 'Prima lega|Seconda lega|Terza lega',
 'lists.titles': 'Scudetti|Coppa nazionale|Coppa dei campioni|Coppa delle coppe|Coppa UEFA',
 'lists.cups': 'Coppa nazionale|Coppa dei campioni|Coppa delle coppe|Coppa UEFA',
 'lists.sizes': 'Nessuno|Piccolo|Medio|Grande',
 'lists.grade_1': '1 – Insufficiente',
 'lists.grade_6': '6 – Ottimo',
 'lists.records': 'Vitt. casa|Sconf. casa|Gol fatti casa|Gol subiti casa|Vitt. trasf.|Sconf. trasf.|Gol '
                  'fatti trasf.|Gol subiti trasf.',
 'prof.identity': 'Identità e cassa',
 'prof.name': 'Nome manager',
 'prof.cash': 'Cassa',
 'prof.date': 'Data (g / m / anno)',
 'prof.level': 'Livello (1–5)',
 'prof.mgmt': 'Gestione squadra',
 'prof.internal': 'Valori interni',
 'prof.internal_items': 'Lega (0/1/2)|Spareggio (byte 265)|Flag stagione (byte 320)',
 'prof.note': 'Cambiando club viene aggiornata anche la lega (0/1/2).',
 'hist.palmares': 'Palmarès',
 'hist.seasons_played': 'Stagioni giocate',
 'hist.titles': 'Titoli: {name}',
 'hist.round': 'Turno in corso: {name}',
 'hist.balance': 'Bilancio complessivo',
 'hist.balance_items': 'Punti|Gol fatti|Gol subiti|Vittorie|Sconfitte|Pareggi|Partite giocate|Punti subiti '
                       '(2×G − Pt)',
 'hist.seasons': 'Stagioni',
 'hist.add': '+ Aggiungi stagione',
 'hist.remove': '− Rimuovi ultima',
 'hist.season_cols': 'Posizione|Lega|Coppa naz.|Europa',
 'hist.note': 'Max 50 stagioni; la nuova riga copia la precedente. Posizione: 1–18 prima lega, 19–38 '
              'seconda, 39–58 terza; 255 = non ancora manager. Nelle coppe il bit 7 (+128) indica la '
              'vittoria.',
 'stats.positions': 'Posizione in classifica per giornata',
 'stats.attendance': 'Spettatori per partita (migliaia)',
 'stats.series': 'Serie record del manager (21 valori)',
 'stats.note': 'Le statistiche di serie comprendono sette categorie per totale, casa e trasferta. I byte '
               '267–304 e 330–346 memorizzano la cronologia per giornata.',
 'squad.cols': 'Giocatore|Ruolo|Espulsioni\n'
               'dirette (+0)|Ammonizioni\n'
               '(+1)|Espulsioni\n'
               'doppia gialla\n'
               '(+2)|Gol\n'
               'campionato\n'
               '(+3)|Gol Coppa\n'
               'Italia (+4)|Gol\n'
               'Europa (+5)|Presenze\n'
               'campionato\n'
               '(+6)|Presenze Coppa\n'
               'Italia (+7)|Presenze\n'
               'Europa (+8)|Flag di\n'
               'stato (+9)|Numero\n'
               'maglia (+10)|Contratto\n'
               '(stagioni)\n'
               '(+11)|Prestito\n'
               '(+12)|Squalifica /\n'
               'infortunio\n'
               '(+13)',
 'squad.all99': 'Tutti a 99 (Cond/Tec/Forma)',
 'squad.count': '{n} giocatori in rosa',
 'squad.note': 'Condizione, tecnica e forma sono i valori correnti della rosa; freschezza va da 50 a 150. Il '
               'contratto è espresso in stagioni. Il contatore +13 indica partite per la squalifica e '
               'settimane per l’infortunio. Doppio clic o Invio per modificare una cella, Tab per passare '
               'alla successiva.',
 'pl.search': 'Cerca:',
 'pl.club': 'Club:',
 'pl.all': 'Tutti',
 'pl.cols': 'Nome\n'
            'giocatore|Età\n'
            '(anni)|Condizione\n'
            '(attuale)|Tecnica\n'
            '(attuale)|Forma\n'
            '(attuale)|Codice\n'
            'posizione\n'
            '(0–99)|Gruppo\n'
            'ruolo|Gol in\n'
            'campionato|Presenze in\n'
            'campionato|Club\n'
            'attuale',
 'pl.count': '{n} giocatori',
 'std.facilities': 'Impianti',
 'std.ticket': 'Prezzo biglietto',
 'std.lights': 'Riflettori',
 'std.screen': 'Megaschermo',
 'std.condition_stadium': 'Condizione stadio',
 'std.comfort': 'Comfort',
 'std.attendance': 'Affluenza',
 'std.season_att': 'Presenze stagione',
 'std.record_att': 'Record spettatori',
 'std.record_opp': 'Avversario del record',
 'std.min_att': 'Minimo spettatori',
 'std.min_opp': 'Avversario del minimo',
 'std.expansions': 'Ampliamenti stadio',
 'std.exp_items': 'Posti a sedere|Posti in piedi|Posti coperti|Riflettori|Megaschermo|Condizione|Comfort',
 'std.above': '(sopra)',
 'std.exp_cols': 'Voce|Attuale|In costruzione|Giorni mancanti',
 'std.note': 'Riflettori, megaschermo, condizione e comfort si impostano nel riquadro «Impianti».',
 'loan.bank': 'Banca',
 'loan.lender': 'Finanziatore {n}',
 'loan.cols': 'Da|Importo|Interessi/mese|Tasso %|Inizio|Scadenza',
 'loan.note': 'Importo pari a zero: prestito non attivo. Le date sono nel formato gg/mm/aaaa. Per creare un '
              'prestito, impostare anche gli interessi (importo × tasso / 100).',
 'sp.shirt': 'Maglia',
 'sp.board': 'Cartellone',
 'sp.tv': 'TV',
 'sp.adcost': 'Spese pubblicità',
 'sp.income': 'Entrate pubblicitarie',
 'sp.item': 'Voce',
 'sp.amount': 'Importo',
 'sp.contracts': 'Contratti attivi',
 'sp.contract_cols': 'Spazio|Mesi rimasti|N° sponsor',
 'sp.offers': 'Offerte sponsor',
 'sp.offer_cols': 'Sponsor|Maglia: anni|Maglia: importo|Cartelloni: anni|Cartelloni: importo',
 'sp.note': 'Le entrate provengono dalla tabella pubblicitaria del manager. I campi contratto e offerta sono '
            'memorizzati nel relativo record.',
 'st.resort': 'Riordina',
 'st.cols': 'Club|Punti\n'
            'totali|Differenza\n'
            'reti|Punti\n'
            'in casa|Punti\n'
            'in trasferta|Gol fatti\n'
            'in casa|Gol fatti\n'
            'in trasferta|Gol subiti\n'
            'in casa|Gol subiti\n'
            'in trasferta|Partite giocate\n'
            'in casa|Partite giocate\n'
            'in trasferta|Vittorie\n'
            'in casa|Vittorie\n'
            'in trasferta|Sconfitte\n'
            'in casa|Sconfitte\n'
            'in trasferta|Punti\n'
            'classifica storica',
 'st.note': 'I punti totali sono la somma dei punti ottenuti in casa e in trasferta; la differenza reti è '
            'data dai gol fatti meno i gol subiti. Le altre colonne mostrano separatamente i dati delle '
            'partite in casa e in trasferta. L’ordinamento usa prima i punti totali e poi la differenza '
            'reti; «Riordina» lo aggiorna.',
 'res.round': 'Giornata {n}',
 'res.match': 'Partita',
 'res.note': 'Il salvataggio memorizza solo i gol, non le squadre delle giornate passate. 255 = non giocata; '
             '30 gol in casa = partita rinviata.',
 'cal.season': 'Stagione in corso',
 'cal.day': 'Giorno della stagione',
 'cal.next': 'Prossima giornata ({n}ª lega)',
 'cal.matches': 'partite della giornata in corso',
 'cal.note': "Doppio clic su una squadra per sceglierla dall'elenco.",
 'cup.relegation': 'Relegazione',
 'cup.first_leg': 'Andata',
 'cup.outcome': 'Esito (1 = sale)',
 'cup.round': 'Turno in corso',
 'cup.legs_played': 'Andata giocata',
 'cup.qualified': 'Qualificate europee tedesche (lista)',
 'cup.slots': 'Posti europei (3 × 6, 128 = libero)',
 'cup.label': 'Coppa:',
 'cup.goals_h': 'Gol C',
 'cup.goals_a': 'Gol T',
 'cup.first_leg_goals': 'Andata coppe europee (gol, 3 × 32)',
 'cup.note': 'Per i gol dei turni: +10 dopo i supplementari, +20 dopo i rigori.',
 'cl.search': 'Cerca club:',
 'cl.cols': 'Base|C1|C2|C3|T1|T2|T3|F1|F2|F3|Stato',
 'cl.count': '{n} club',
 'cl.note': 'C = condizione, T = tecnica, F = forma (tre valori ciascuno). Indici 0–17 prima lega, 18–37 '
            'seconda, 38–57 terza, il resto club esteri.',
 'ser.note': 'La tabella contiene 21 valori relativi alle serie in corso del club.',
 'rec.none': 'Nessun club.',
 'rec.cols': 'Record|Valore (a:b)|Avversario',
 'rec.note': 'Record dei club e relativo avversario. Ogni byte contiene due valori da 0 a 15, scritti come '
             'a:b.',
 'vs.note': 'Ultime 5 partite del manager contro ogni club, come gol subiti:gol propri (max 15 per cella). '
            'Cella vuota = nessuna partita.',
 'msg.manager': 'Manager {n} – {name}',
 'msg.none': 'Nessun messaggio.',
 'msg.note': 'Il segno ^ va a capo. Puoi cambiare il testo dei messaggi esistenti (max 240 caratteri); '
             'aggiungere o eliminare messaggi richiede di aggiornare anche i puntatori interni e non è '
             'supportato.',
 'grp.advanced': 'Avanzate',
 'pg.market': 'Mercato',
 'pg.ext_standings': 'Classifica estesa',
 'pg.raw': 'Blocchi grezzi',
 'pg.options': 'Opzioni di gioco',
 'opt.panel': 'Opzioni di gioco (ATT/DIS)',
 'opt.series': 'Serie A|Serie B|Serie C',
 'opt.items': 'Parziali 1° tempo|Risultati finali|Tabella',
 'opt.others': 'Azioni di gioco|Coppa Italia|Coppe europee|Recuperi|Giornale|Oscurire',
 'opt.other': 'Altre opzioni',
 'opt.speed': 'Velocità di gioco',
 'std.capacity': 'Capienza totale (calcolata)',
 'loan.total': 'Debito totale',
 'loan.interest_total': 'Interessi mensili totali',
 'squad.avg': 'Media rosa – Cond {c} · Tec {t} · Forma {f}',
 'squad.extra_cols': 'Fattore\n'
                     'allenamento\n'
                     '(+14)|Indice\n'
                     'giocatore\n'
                     '(+15)|Condizione\n'
                     '(+16)|Tecnica\n'
                     '(+17)|Forma\n'
                     '(+18)|Freschezza\n'
                     '(+19)|Programma\n'
                     'allenamento\n'
                     '(+20)|Valutazione\n'
                     'partita\n'
                     '(+21, i8)|Club\n'
                     'offerente\n'
                     '(+22)|Tipo\n'
                     'infortunio\n'
                     '(+23)|Trattative /\n'
                     'carriera\n'
                     '(+24)|Colonna\n'
                     'orizzontale X\n'
                     '(i8, +25)|Profondità\n'
                     'verticale Y\n'
                     '(u8, +26)|Byte +27\n'
                     '(non mappato)|Presenze\n'
                     'campionato\n'
                     '(+28, u16)|Presenze Coppa\n'
                     'Italia (+30, u16)|Presenze\n'
                     'Europa\n'
                     '(+32, u16)|Gol\n'
                     'campionato\n'
                     '(+34, u16)|Gol Coppa\n'
                     'Italia (+36, u16)|Gol\n'
                     'Europa\n'
                     '(+38, u16)|Ingaggio\n'
                     'mensile\n'
                     '(i32, +40–43)|Byte +44–47\n'
                     '(non mappati)|Puntatore\n'
                     'notifica\n'
                     '(i32, +48)',
 'pl.extra_cols': 'Media\niniziale\n(+27)|Preferenza\nlaterale\n(+32)|Proprietario /\nstato mercato\n(+33)',
 'squad.extra_note': 'Ingaggio mensile: intero signed a 32 bit ai byte +40–43. I byte +44–47 non hanno una '
                     'funzione assegnata.',
 'pl.note': '+27 = media iniziale di condizione, tecnica e forma; non segue le variazioni delle '
            'caratteristiche correnti. +32 (0–6) = preferenza laterale usata dalla formazione automatica per '
            'scegliere la colonna orizzontale. +33: 0–3 manager, 4 mercato, 5 libero. Ruolo +31: 0–24 '
            'portiere, 25–49 difensore, 50–74 centrocampista, 75–99 attaccante.',
 'pl.owner_market': 'Mercato',
 'pl.owner_free': 'Libero',
 'mk.cols': 'Giocatore|Ruolo|Rifiuti\n'
            'offerte\n'
            '(+3)|Flag di\n'
            'stato (+9)|Prestito\n'
            '(+12)|Squalifica /\n'
            'infortunio\n'
            '(+13)|Fattore\n'
            'allenamento\n'
            '(+14)|Indice\n'
            'giocatore\n'
            '(+15)|Condizione\n'
            '(+16)|Tecnica\n'
            '(+17)|Forma\n'
            '(+18)|Freschezza\n'
            '(+19)|Programma\n'
            'allenamento\n'
            '(+20)|Valutazione\n'
            'partita\n'
            '(+21, i8)|Club\n'
            'offerente\n'
            '(+22)|Tipo\n'
            'infortunio\n'
            '(+23)|Trattative /\n'
            'carriera\n'
            '(+24)|Byte +27\n'
            '(non mappato)|Valore\n'
            'mercato\n'
            '(i32, +40)|Byte +44–47\n'
            '(non mappati)|Puntatore\n'
            'notifica\n'
            '(i32, +48)',
 'mk.count': '{n} giocatori in lista',
 'mk.note': 'Il mercato usa gli slot 100–111. +40–43 = valore economico (i32); +3 = rifiuti per manager; +9 '
            '= flag di stato; +12 = prestito; +13 = partite di squalifica o settimane di infortunio; +22 = '
            'club offerente; +23 = tipo di infortunio; +14 e +20 = allenamento; +21 = valutazione della '
            'partita; +24 = stato del contratto/carriera; +27 e +44–47 = campi non decifrati; +48–51 = '
            'puntatore a una notifica.',
 'xs.cols': 'Serie A (b4–11)|Serie B (b13–20)|?2|?3|?24|?25|?28|?29|?40|?41|?44|?45|?46|b32–37',
 'xs.note': 'Record di classifica completo da 54 byte per ciascun club. Le due serie esadecimali contengono '
            'due valori a 4 bit per byte.',
 'cal.perm': 'Ordine di sorteggio del calendario (20 valori per lega)',
 'cal.perm_note': 'Permutazione degli slot delle squadre usata per costruire il calendario (1ª lega 0–19, 2ª '
                  '20–39, 3ª 40–59). Modificarla cambia il calendario delle giornate future.',
 'raw.block5': 'Recuperi: tabella 20 × 5 byte (5457–5556)',
 'raw.cols5': 'Identificatore\n'
              '(+0)|Indice giorno\n'
              '(+1)|Giornata campionato\n'
              '(+2)|Lega\n'
              '(+3)|Indice partita\n'
              '(+4)',
 'raw.tail1': 'Blocco finale 34063–34223',
 'raw.tail2': 'Blocco finale 34226–34366',
 'raw.note': 'Gli offset sono assoluti nel buffer decodificato. Il byte 34367 è visualizzato nella pagina '
             'Coppe; i messaggi da 34368 sono gestiti nella pagina Messaggi.',
 'std.home_games': 'Partite in casa giocate',
 'std.avg_att': 'Media spettatori (calcolata)',
 'prof.mgmt_items': 'Intensità partita (0–34)|Sovvenzioni giovanili (0–34)|Palloni: condizione|Palloni: '
                    'gioco|Palloni: tiro|Palloni: tattica|Morale (0–40)|Partite con pubblico|Intensità '
                    'allenamento|Allenamento portiere|Allenamento difesa|Allenamento centrocampo|Allenamento '
                    'attacco',
 'prof.portrait_id': 'Portrait (1–4)',
 'prof.extra': 'Altri campi',
 'prof.extra_item': 'Byte +{off}',
 'prof.extra_note': '+480 e +482 sono due valori a 16 bit. +480 viene ricalcolato dal gioco; +482 non ha una '
                    'funzione assegnata. Gli altri campi non hanno una descrizione disponibile.',
 'stats.chart': 'Grafico delle presenze',
 'opt.speed_byte': 'Velocità (0–70)',
 'opt.note': 'Le caselle attivano o disattivano le relative opzioni di visualizzazione.',
 'info.version': 'Versione',
 'info.unknown': 'sconosciuta',
 'info.edited': "MODIFICATO CON L'EDITOR",
 'info.ingame': 'in-game',
 'info.bmp_ita_mod': 'mod ITA su EXE tedesco',
 'raw.recovery_note': 'I 20 record da 5 byte descrivono le partite rinviate: identificatore, indice giorno, '
                      'giornata, lega e partita.',
 'raw.unknown_area': 'Dati aggiuntivi e aree non decifrate (34063–34221)',
 'raw.unknown_34063': '34063–34064 · 2 byte non decifrati',
 'raw.unknown_34065': '34065–34094 · 30 byte non decifrati',
 'raw.unknown_34095': '34095–34098 · 4 byte non decifrati',
 'raw.unknown_34215': '34215–34221 · 7 byte non decifrati',
 'raw.calendar_title': 'Indice e tabella delle maschere del calendario (34226–34321)',
 'raw.calendar_index': 'Indice corrente (byte 34226)',
 'raw.calendar_index_note': 'Il programma usa questo byte come indice per selezionare un elemento della '
                            'tabella seguente. Non è il numero della giornata mostrato nel calendario.',
 'raw.calendar_mask': 'Maschera di avanzamento delle tre leghe · 95 byte (34227–34321)',
 'raw.daily_words': 'Otto valori a 16 bit aggiornati durante il ciclo giornaliero (34322–34337)',
 'raw.trailing_values': 'Altri valori del blocco finale (34338–34366)',
 'raw.unknown_byte': 'Byte non decifrato (34338)',
 'raw.offset': 'Offset',
 'raw.word_value': 'Valore a 16 bit',
 'raw.dword_value': 'Valore a 32 bit',
 'tip.recovery_marker': 'Byte +0: identificatore del record di recupero.',
 'tip.recovery_day_index': 'Byte +1: indice del giorno di calendario associato al recupero.',
 'tip.recovery_matchday': 'Byte +2: giornata originaria del campionato.',
 'tip.recovery_league': 'Byte +3: indice della lega (0, 1 o 2).',
 'tip.recovery_fixture': 'Byte +4: indice della partita nella giornata.',
 'tip.raw_34063': 'Valore a 16 bit che identifica il tipo e la durata della partita. Valori noti: '
                  '22222/22251 = senza fine; 1964/1993 = un anno; 1966/1995 = tre anni. Le varianti '
                  'distinguono l’avvio storico da quello normale.',
 'tip.raw_34065': 'Area di 30 byte (34065–34094) senza funzione assegnata.',
 'tip.raw_34095': 'Quattro byte (34095–34098) che precedono il selettore delle regole; funzione non '
                  'identificata.',
 'tip.raw_34215': 'Sette contatori di giorni relativi ai blocchi degli ampliamenti dello stadio.',
 'tip.calendar_mask': 'Tabella binaria di 95 byte. L’indice +34226 seleziona il byte corrente; i bit '
                      'indicano quali leghe avanzano di giornata.',
 'tip.daily_word': 'Contatore signed a 16 bit della disponibilità di un campo di allenamento.',
 'tip.save_offset': 'Offset assoluto del campo nel buffer decodificato del savegame.',
 'tip.trailing_dword': 'Uno dei sette valori a 32 bit (34339–34366). La dimensione dei campi è nota, ma il '
                       'significato operativo non è ancora identificato.',
 'mark.name': 'IMBROGLIONE',
 'tip.generic': 'Informazioni sulla colonna «{label}». Passa il mouse qui per consultare il campo '
                'rappresentato.',
 'tip.value_column': '{description} Colonna {column}: valore nella stessa posizione di ogni riga del blocco.',
 'tip.unknown_values': 'Valori consecutivi di un blocco dati non ancora decifrato.',
 'tip.index': 'Indice progressivo della riga o dello slot mostrato.',
 'tip.balance_item': 'Voce del bilancio complessivo della squadra; il significato specifico è indicato nella '
                     'prima colonna.',
 'tip.home_total': 'Totale relativo alle partite giocate in casa.',
 'tip.away_total': 'Totale relativo alle partite giocate in trasferta.',
 'tip.season_position': 'Posizione finale ottenuta dal manager nella stagione selezionata.',
 'tip.season_league': 'Risultato della stagione in campionato.',
 'tip.season_cup': 'Risultato della stagione nella coppa nazionale.',
 'tip.season_europe': 'Risultato della stagione nelle competizioni europee.',
 'tip.positions_by_round': 'Posizione del manager in classifica dopo ciascuna giornata. Ogni valore '
                           'corrisponde a una giornata.',
 'tip.attendance_by_match': 'Numero di spettatori della partita corrispondente, memorizzato in migliaia.',
 'tip.series_unverified': 'Valore della sequenza statistica del manager.',
 'tip.player_index': 'Indice del giocatore collegato nella tabella anagrafica da 151 record; è il byte +15 '
                     'dello slot di rosa.',
 'tip.unknown_bytes42': 'Byte +42–43 dello slot di rosa; funzione non identificata.',
 'tip.player': 'Nome del giocatore collegato a questo slot della rosa o del mercato.',
 'tip.role_group': 'Gruppo di ruolo derivato dal codice posizione del record giocatore: portiere, difensore, '
                   'centrocampista o attaccante.',
 'tip.shirt_number': 'Numero di maglia assegnato al giocatore.',
 'tip.condition_current': 'Condizione corrente del giocatore nella rosa.',
 'tip.technique_current': 'Valore corrente della tecnica del giocatore.',
 'tip.form_current': 'Forma corrente del giocatore.',
 'tip.freshness': 'Freschezza/stanchezza corrente del giocatore; il valore è memorizzato separatamente da '
                  'condizione, tecnica e forma.',
 'tip.monthly_wage': 'Ingaggio mensile del giocatore. Le routine operative di creazione e contratto leggono '
                     'e scrivono il campo completo a 32 bit +40–43; records.ts espone invece un accessore '
                     'u16 sui soli byte +40–41. L’editor mostra il valore i32 completo.',
 'tip.contract_seasons': 'Durata del contratto espressa in stagioni.',
 'tip.suspension_injury': 'Partite di squalifica residue oppure settimane di infortunio residue. Il tipo di '
                          'evento è indicato dai flag di stato.',
 'tip.yellow_cards': 'Numero di ammonizioni registrate per il giocatore.',
 'tip.direct_reds': 'Numero di espulsioni dirette registrate per il giocatore.',
 'tip.league_goals': 'Gol segnati dal giocatore in campionato.',
 'tip.league_appearances': 'Presenze del giocatore in campionato.',
 'tip.training_factor': 'Fattore individuale che modifica l’efficacia dell’allenamento; 50 rappresenta il '
                        'fattore neutro.',
 'tip.training_program': 'Programma di allenamento codificato in bit: durata residua, intensità e direzione '
                         'della variazione.',
 'tip.pitch_column': 'Coordinata orizzontale X salvata nel byte +25 dello slot di rosa. Il gioco la '
                     'interpreta come int8; nelle formazioni automatiche parte dalla colonna 0–6 e può '
                     'essere spostata in base alla preferenza laterale del giocatore.',
 'tip.pitch_line': 'Coordinata di profondità Y salvata nel byte +26 dello slot di rosa (0–7): 0 verso la '
                   'porta avversaria, 7 verso la propria. I titolari della stessa linea condividono '
                   'normalmente la stessa profondità, salvo piccoli spostamenti previsti dal modulo.',
 'tip.apps_league': 'Contatore a 16 bit delle presenze in campionato.',
 'tip.apps_cup': 'Contatore a 16 bit delle presenze nella coppa nazionale.',
 'tip.apps_europe': 'Contatore a 16 bit delle presenze nelle coppe europee e negli spareggi secondo la '
                    'routine del gioco.',
 'tip.goals_cup': 'Contatore a 16 bit dei gol nella coppa nazionale.',
 'tip.goals_europe': 'Contatore a 16 bit dei gol nelle coppe europee.',
 'tip.second_yellow': 'Espulsioni causate da una seconda ammonizione.',
 'tip.state_flags': 'Bitmask di stato: bit 0 squalifica, bit 1 infortunio, bit 6 offerta per un proprio '
                    'giocatore, bit 7 proprio giocatore sul mercato.',
 'tip.loan': 'Informazioni sul prestito: club proprietario codificato nel byte +12 e flag 0x80 per '
             'distinguere lo stato del prestito.',
 'tip.match_rating': 'Valutazione con segno ottenuta dal giocatore nella partita più recente; viene azzerata '
                     'prima della gara successiva.',
 'tip.offering_club': 'Indice del club che ha presentato un’offerta per il giocatore.',
 'tip.injury_type': 'Codice numerico del tipo di infortunio. Il codice resta memorizzato anche dopo la '
                    'guarigione.',
 'tip.contract_status': 'Stato delle trattative: 0–99 contatore di attesa per nuove trattative; da 100 '
                        'offerta di rinnovo pendente; il bit 7 segnala il ritiro.',
 'tip.unknown_byte27': 'Byte +27 del record di rosa; funzione non identificata.',
 'tip.unknown_bytes44': 'Byte +44–47 del record di rosa; funzione non identificata.',
 'tip.notification_pointer': 'Riferimento a 32 bit a una notifica associata al giocatore.',
 'tip.age': 'Età del giocatore in anni.',
 'tip.condition_base': 'Valore di condizione nel record anagrafico del giocatore; non coincide '
                       'necessariamente con la condizione corrente della rosa.',
 'tip.technique_base': 'Valore di tecnica nel record anagrafico del giocatore.',
 'tip.form_base': 'Valore di forma nel record anagrafico del giocatore.',
 'tip.position_value': 'Codice posizione da 0 a 99: 0–24 portiere, 25–49 difensore, 50–74 centrocampista, '
                       '75–99 attaccante.',
 'tip.current_club': 'Club attualmente associato al giocatore nel record anagrafico.',
 'tip.initial_average': 'Media iniziale (condizione + tecnica + forma) / 3, memorizzata alla creazione e non '
                        'aggiornata insieme alle caratteristiche correnti.',
 'tip.preferred_side': 'Preferenza laterale del giocatore (0–6), usata dalla formazione automatica per '
                       'scegliere o correggere la colonna orizzontale.',
 'tip.owner': 'Proprietario/stato del giocatore: 0–3 manager, 4 mercato, 5 giocatore libero.',
 'tip.market_value': 'Prezzo o valore economico del giocatore nel mercato, memorizzato come intero con segno '
                     'a 32 bit.',
 'tip.offer_refusals': 'Rifiuti delle offerte dei manager, codificati nei bit del byte +3.',
 'tip.stadium_item': 'Tipo di impianto o settore dello stadio interessato dall’ampliamento.',
 'tip.current_value': 'Valore attuale della struttura o del settore dello stadio.',
 'tip.work_in_progress': 'Valore della struttura quando i lavori saranno completati, oppure livello in '
                         'costruzione.',
 'tip.days_remaining': 'Giorni mancanti al completamento dei lavori.',
 'tip.lender': 'Soggetto che ha concesso il prestito: banca oppure altro manager.',
 'tip.loan_number': 'Numero progressivo del prestito per quel finanziatore.',
 'tip.loan_amount': 'Capitale del prestito, memorizzato come valore a 32 bit.',
 'tip.monthly_interest': 'Importo degli interessi da pagare ogni mese.',
 'tip.interest_rate': 'Tasso percentuale applicato al capitale del prestito.',
 'tip.start_date': 'Data di inizio del prestito; il mese nel file è memorizzato da 0 a 11.',
 'tip.end_date': 'Data di scadenza del prestito; il mese nel file è memorizzato da 0 a 11.',
 'tip.sponsor_item': 'Voce delle entrate pubblicitarie registrate per il manager.',
 'tip.amount': 'Importo economico associato alla voce o al contratto.',
 'tip.sponsor_slot': 'Slot riservato al contratto dello sponsor.',
 'tip.months_remaining': 'Mesi ancora validi del contratto pubblicitario.',
 'tip.sponsor_count': 'Numero/codice dello sponsor associato allo slot.',
 'tip.sponsor': 'Indice o identificativo dello sponsor nell’offerta.',
 'tip.shirt_years': 'Durata in anni dell’offerta per la sponsorizzazione della maglia.',
 'tip.shirt_amount': 'Importo offerto per la sponsorizzazione della maglia.',
 'tip.boards_years': 'Durata in anni dell’offerta per i cartelloni pubblicitari.',
 'tip.boards_amount': 'Importo offerto per i cartelloni pubblicitari.',
 'tip.club': 'Nome del club a cui si riferiscono i dati della riga.',
 'tip.points': 'Punti totali in classifica, calcolati dai punti ottenuti in casa e in trasferta.',
 'tip.goal_difference': 'Differenza reti totale, calcolata da gol fatti meno gol subiti.',
 'tip.home_points': 'Punti ottenuti nelle partite giocate in casa.',
 'tip.away_points': 'Punti ottenuti nelle partite giocate in trasferta.',
 'tip.home_goals_for': 'Gol segnati in casa.',
 'tip.away_goals_for': 'Gol segnati in trasferta.',
 'tip.home_goals_against': 'Gol subiti in casa.',
 'tip.away_goals_against': 'Gol subiti in trasferta.',
 'tip.home_games': 'Partite giocate in casa.',
 'tip.away_games': 'Partite giocate in trasferta.',
 'tip.home_wins': 'Vittorie ottenute in casa.',
 'tip.away_wins': 'Vittorie ottenute in trasferta.',
 'tip.home_losses': 'Sconfitte subite in casa.',
 'tip.away_losses': 'Sconfitte subite in trasferta.',
 'tip.historical_points': 'Campo storico aggiuntivo memorizzato nel record del club; non è usato per il '
                          'totale punti calcolato sopra.',
 'tip.match_no': 'Numero progressivo della partita nella giornata selezionata.',
 'tip.home_goals': 'Gol segnati dalla squadra di casa nella partita.',
 'tip.away_goals': 'Gol segnati dalla squadra in trasferta nella partita.',
 'tip.score_separator': 'Separatore visivo fra il risultato della squadra di casa e quello della squadra '
                        'ospite.',
 'tip.home_team': 'Club indicato come squadra di casa nell’accoppiamento.',
 'tip.away_team': 'Club indicato come squadra ospite nell’accoppiamento.',
 'tip.calendar_order': 'Elemento della permutazione usata dal gioco per costruire le giornate future del '
                       'calendario.',
 'tip.european_qualifiers': 'Indice del club qualificato alle competizioni europee, secondo la lista '
                            'memorizzata nel salvataggio.',
 'tip.european_places': 'Slot dei posti europei; 128 indica uno slot libero.',
 'tip.club_name': 'Nome del club nel database del salvataggio.',
 'tip.club_base': 'Valore base del club nel record anagrafico dei club.',
 'tip.club_condition_home': 'Valore relativo alla condizione del club nella prima voce della serie.',
 'tip.club_condition_away': 'Valore relativo alla condizione del club nella seconda voce della serie.',
 'tip.club_condition_third': 'Valore relativo alla condizione del club nella terza voce della serie.',
 'tip.club_technique_home': 'Valore relativo alla tecnica del club nella prima voce della serie.',
 'tip.club_technique_away': 'Valore relativo alla tecnica del club nella seconda voce della serie.',
 'tip.club_technique_third': 'Valore relativo alla tecnica del club nella terza voce della serie.',
 'tip.club_form_home': 'Valore relativo alla forma del club nella prima voce della serie.',
 'tip.club_form_away': 'Valore relativo alla forma del club nella seconda voce della serie.',
 'tip.club_form_third': 'Valore relativo alla forma del club nella terza voce della serie.',
 'tip.club_status': 'Codice di stato del club.',
 'tip.external_series_a': 'Blocco esadecimale di 8 byte associato alla serie A; ogni byte contiene due '
                          'valori a 4 bit.',
 'tip.external_series_b': 'Blocco esadecimale di 8 byte associato alla serie B; ogni byte contiene due '
                          'valori a 4 bit.',
 'tip.club_record_unknown': 'Byte +{offset} del record club da 54 byte.',
 'tip.club_record_tail': 'Valori esadecimali dei byte +32–37 del record club.',
 'tip.raw_record_byte': 'Byte +{offset} del record grezzo da 5 byte mostrato nella tabella.',
 'tip.raw_block_values': 'Valori consecutivi del blocco dati che inizia all’offset {start}.',
 'tip.series_column': 'Valore {number} della sequenza statistica del club.',
 'tip.record': 'Nome del record detenuto dal club.',
 'tip.record_value': 'Valore del record, rappresentato come coppia di numeri da 0 a 15 (a:b).',
 'tip.record_opponent': 'Club avversario associato al record.',
 'tip.versus_home': 'Una delle ultime 5 partite del manager contro questo club, giocata in casa. Il '
                    'risultato è codificato come gol subiti:gol segnati dal manager.',
 'tip.versus_away': 'Una delle ultime 5 partite del manager contro questo club, giocata in trasferta. Il '
                    'risultato è codificato come gol subiti:gol segnati dal manager.',
 'squad.hint': 'Coordinate salvate per ogni giocatore: +25 = X orizzontale (i8); +26 = profondità Y (0–7: 0 '
               'verso la porta avversaria, 7 verso la propria). I numeri di maglia 1–11 identificano i '
               'titolari. Il modulo del manager è nel byte 51 + 2 × indice manager: 1 manuale, 2 = 4-4-2, 3 '
               '= 3-5-2, 4 = 3-4-3; il byte successivo è la copia di riserva. Doppio clic o Invio per '
               'modificare una cella; Tab passa alla successiva.',
 'pl.hint': 'Elenco dei giocatori del salvataggio. Le intestazioni spiegano i campi anagrafici e i valori '
            'correnti.',
 'mk.hint': 'Il mercato occupa gli slot 100–111. Passa il mouse sulle intestazioni per leggere la '
            'descrizione estesa dei campi.',
 'tip.european_first_leg_goals': 'Gol della partita di andata nelle competizioni europee, memorizzati nel '
                                 'blocco dei risultati delle coppe.',
 'squad.formation_info': 'Modulo salvato: {active} · Backup: {backup}',
 'squad.system_manual': 'Manuale',
 'squad.system_unknown': 'Non riconosciuto ({value})',
 'opt.items_full': 'Parziali 1° tempo · Serie A|Risultati finali · Serie A|Tabella · Serie A|Parziali 1° '
                   'tempo · Serie B|Risultati finali · Serie B|Tabella · Serie B|Parziali 1° tempo · Serie '
                   'C|Risultati finali · Serie C|Tabella · Serie C|Scene dei gol|Coppa Italia|Coppe '
                   'europee|Recuperi|Giornale|Oscurire',
 'opt.option_name': 'Opzione',
 'opt.raw_byte': 'Stato',
 'tip.runtime_option': 'Interruttore di visualizzazione del menu Opzioni.',
 'tip.runtime_option_value': 'Stato dell’interruttore di visualizzazione.',
 'opt.speed_value': 'Velocità (0–70)',
 'opt.speed_note': 'Intervallo ammesso: 0–70. Valore predefinito: 40.',
 'tip.speed_runtime': 'Valore a 16 bit della velocità di gioco (0–70).',
 'raw.game_type': 'Tipo e durata della partita (34063–34064)',
 'raw.end_year_code': 'Codice tipo/durata (u16)',
 'raw.end_year_meaning': 'Interpretazione',
 'raw.endyear_endless_historical': 'Partita senza fine · avvio storico',
 'raw.endyear_endless': 'Partita senza fine · avvio normale',
 'raw.endyear_one_historical': 'Partita di 1 anno · avvio storico',
 'raw.endyear_one': 'Partita di 1 anno · avvio normale',
 'raw.endyear_three_historical': 'Partita di 3 anni · avvio storico',
 'raw.endyear_three': 'Partita di 3 anni · avvio normale',
 'raw.endyear_other': 'Valore non riconosciuto ({value})',
 'raw.rule_2026': 'Selettore delle regole (34099)',
 'raw.rule_value': 'Regolamento',
 'raw.rules_original': 'Regole 1993',
 'raw.rules_2026': 'Regole 2026',
 'raw.poach_counts': 'Contatori trasferimenti tra manager (34100–34115)',
 'raw.manager_number': 'Manager {n}',
 'raw.poacher': 'Manager che tenta',
 'raw.owner_manager': 'Proprietario {n}',
 'raw.poach_note': 'Contatore dei trasferimenti conclusi per ciascuna combinazione di manager acquirente e '
                   'manager proprietario.',
 'raw.unknown_34116_label': 'Byte non mappato (+34116)',
 'raw.debt_mask': 'Maschera blocco acquisti (+34117)',
 'raw.derby_stakes': 'Puntata derby per manager (34118–34121)',
 'raw.derby_levels': '50.000 DM|100.000 DM|250.000 DM|500.000 DM',
 'raw.manager': 'Manager',
 'raw.stake': 'Livello puntata',
 'raw.youth_counts': 'Contatori settore giovanile (34122–34129)',
 'raw.promotions': 'Promozioni in prima squadra',
 'raw.youth_poached': 'Giovani appena promossi sottratti',
 'raw.youth_note': 'Valori per manager: giovani promossi in prima squadra e giovani trasferiti a un altro '
                   'manager. I contatori si azzerano al cambio di stagione.',
 'raw.unknown_34130': '34130–34214 · 85 byte non decifrati',
 'raw.stadium_lockout': 'Giorni di blocco per tipo di ampliamento stadio (34215–34221)',
 'raw.speed_snapshot': 'Word della velocità di gioco (34222–34223)',
 'raw.speed_value': 'Velocità (0–70)',
 'tip.rule_2026': '0 = regole 1993; 1 = regole 2026.',
 'tip.poach_count_row': 'Manager che acquista (riga). Le quattro celle indicano il manager proprietario.',
 'tip.poach_count': 'Numero di trasferimenti conclusi per questa coppia di manager acquirente/proprietario.',
 'tip.debt_mask': 'Maschera di blocco acquisti per indebitamento: un bit per manager. La soglia è un saldo '
                  'inferiore a −1.000.000 DM.',
 'tip.manager_index': 'Indice del manager, da 0 a 3.',
 'tip.derby_stake': 'Livello della puntata derby: 0 = 50.000 DM, 1 = 100.000 DM, 2 = 250.000 DM, 3 = 500.000 '
                    'DM.',
 'tip.youth_promotions': 'Numero di giovani promossi in prima squadra nella stagione per questo manager.',
 'tip.youth_poach': 'Numero di giovani promossi e successivamente trasferiti a un altro manager nella '
                    'stagione.',
 'tip.raw_34130': 'Area di 85 byte (34130–34214) senza funzione assegnata.',
 'tip.stadium_lockout': 'Sette contatori di giorni di blocco per gli ampliamenti dello stadio. Il codice '
                        'originale imposta un blocco casuale di 15–55 giorni dopo il rifiuto di un’offerta. '
                        'È noto l’array da 34215; la corrispondenza precisa tra i sette indici e i singoli '
                        'tipi va mantenuta con cautela.',
 'raw.training_camps': 'Disponibilità degli 8 campi di allenamento (34322–34337)',
 'raw.camp_number': 'Campo',
 'raw.camp_status': 'Disponibilità',
 'raw.camp_counter': 'Contatore residuo (i16)',
 'raw.camp_open_days': 'Aperto · {days} giorni',
 'raw.camp_closed_days': 'Chiuso · {days} giorni',
 'raw.camp_changeover': 'Cambio stato',
 'raw.camp_note': 'Otto valori signed a 16 bit, uno per campo. Negativo = aperto; positivo = chiuso. Il '
                  'contatore avanza di un giorno verso zero; a zero riparte con segno opposto e durata di '
                  '20–70 giorni.',
 'tip.camp_number': 'Indice del campo di allenamento (1–8).',
 'tip.camp_status': 'Negativo = aperto; positivo = chiuso; zero = cambio di stato. Il valore assoluto indica '
                    'i giorni residui.',
 'tip.camp_counter': 'Valore signed a 16 bit all’offset 34322 + 2 × indice. Diminuisce di un giorno fino a '
                     'zero, poi riparte con segno opposto e durata di 20–70 giorni.',
 'raw.additional_fields': 'Altri campi aggiuntivi (34116–34129)'}
