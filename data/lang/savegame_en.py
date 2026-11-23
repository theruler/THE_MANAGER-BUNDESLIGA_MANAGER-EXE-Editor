# -*- coding: utf-8 -*-

LANG_NAME = 'English'

TEXTS_EN = {'grp.manager': 'Manager',
 'grp.squad': 'Team',
 'grp.economy': 'Economy',
 'grp.league': 'Championship',
 'grp.cups': 'Cups',
 'grp.clubs': 'Clubs',
 'grp.messages': 'Messages',
 'pg.profile': 'Profile',
 'pg.history': 'History',
 'pg.stats': 'Statistics',
 'pg.roster': 'Roster',
 'pg.players': 'Players',
 'pg.stadium': 'Stadium',
 'pg.loans': 'Loans',
 'pg.sponsors': 'Sponsors',
 'pg.standings': 'Standings',
 'pg.results': 'Results',
 'pg.calendar': 'Fixtures',
 'pg.cup_state': 'Status',
 'pg.cup_ties': 'Ties',
 'pg.clubs': 'Club data',
 'pg.series': 'Current runs',
 'pg.records': 'Records',
 'pg.versus': 'Head-to-head',
 'pg.messages': 'Messages',
 'err.too_short': 'File too short: not a BMP savegame.',
 'err.bad_sig': 'Invalid signature: not a BMP savegame.',
 'err.chk1': 'Checksum 1 is wrong.',
 'err.chk2': 'Checksum 2 is wrong.',
 'err.truncated': 'File damaged or truncated.',
 'err.verify': 'Read-back verification failed.',
 'err.page': 'Error in this page: {error}',
 'pos.gk': 'GK',
 'pos.df': 'DF',
 'pos.mf': 'MF',
 'pos.fw': 'FW',
 'tb.savegame': 'Savegame:',
 'tb.folder': 'Folder…',
 'tb.open': 'Open file…',
 'tb.save': 'Save .MAN',
 'tb.save_as': 'Save as…',
 'tb.manager': 'Manager:',
 'ph.no_dir': 'No folder selected.\nUse “Open file…” to open a .MAN savegame.',
 'ph.none': 'No .MAN file found in:\n{dir}',
 'ph.pick': '{n} .MAN file(s) found.\nPick a savegame from the list above to open it.',
 'dlg.title': 'Savegame Editor',
 'dlg.folder': 'Folder with the .MAN savegames',
 'dlg.open': 'Open savegame',
 'dlg.save_as': 'Save savegame as',
 'dlg.type_man': 'BMP savegame',
 'dlg.type_all': 'All files',
 'dlg.discard': '{name} has unsaved changes. Discard them?',
 'dlg.roundtrip': 'When opened, re-encoding was NOT identical to the original.\nSave anyway?',
 'dlg.save_failed': 'Saving failed:\n{error}',
 'status.none': 'No savegame loaded.',
 'status.loaded_ok': '{name}: checksum OK, re-encoding identical: yes',
 'status.loaded_warn': '{name}: checksum OK, re-encoding identical: NO – save with care',
 'status.saved': 'Saved {name}, checksums recomputed{backup}.',
 'status.backup': ' (.bak backup created)',
 'status.dirty': '● Unsaved changes',
 'mgr.item': 'Manager {n}: {name}',
 'c.club': 'Club',
 'c.name': 'Name',
 'c.home': 'Home',
 'c.away': 'Away',
 'c.away_full': 'Away',
 'c.home_team': 'Home team',
 'c.away_team': 'Away team',
 'lbl.league': 'League:',
 'lists.leagues': 'First league|Second league|Third league',
 'lists.titles': "League titles|National cup|Champions Cup|Cup Winners' Cup|UEFA Cup",
 'lists.cups': "National cup|Champions Cup|Cup Winners' Cup|UEFA Cup",
 'lists.sizes': 'None|Small|Medium|Large',
 'lists.grade_1': '1 – Poor',
 'lists.grade_6': '6 – Excellent',
 'lists.records': 'Home wins|Home defeats|Home goals for|Home goals against|Away wins|Away defeats|Away '
                  'goals for|Away goals against',
 'prof.identity': 'Identity and cash',
 'prof.name': 'Manager name',
 'prof.cash': 'Cash',
 'prof.date': 'Date (d / m / year)',
 'prof.level': 'Level (1–5)',
 'prof.mgmt': 'Team management',
 'prof.internal': 'Internal values',
 'prof.internal_items': 'League (0/1/2)|Play-off (byte 265)|Season flag (byte 320)',
 'prof.note': 'Changing the club also updates the league (0/1/2).',
 'hist.palmares': 'Honours',
 'hist.seasons_played': 'Seasons played',
 'hist.titles': 'Titles: {name}',
 'hist.round': 'Current round: {name}',
 'hist.balance': 'Overall record',
 'hist.balance_items': 'Points|Goals for|Goals against|Wins|Defeats|Draws|Games played|?432 (signed)',
 'hist.seasons': 'Seasons',
 'hist.add': '+ Add season',
 'hist.remove': '− Remove last',
 'hist.season_cols': 'Position|League|Nat. cup|Europe',
 'hist.note': 'Max 50 seasons; a new row copies the previous one. Position: 1–18 first league, 19–38 second, '
              '39–58 third; 255 = not yet a manager. In the cups bit 7 (+128) marks a win.',
 'stats.positions': 'League position by matchday',
 'stats.attendance': 'Attendance per match (thousands)',
 'stats.series': "Manager's record runs (21 values)",
 'stats.note': 'Run statistics contain seven categories for total, home and away matches. Bytes 267–304 and '
               '330–346 store matchday history.',
 'squad.cols': 'Player|Role|Straight reds\n'
               '(+0)|Yellow cards\n'
               '(+1)|Second-yellow\n'
               'dismissals\n'
               '(+2)|League goals\n'
               '(+3)|Domestic-cup\n'
               'goals (+4)|European\n'
               'goals (+5)|League apps\n'
               '(+6)|Domestic-cup\n'
               'apps (+7)|European\n'
               'apps (+8)|Status flags\n'
               '(+9)|Shirt number\n'
               '(+10)|Contract\n'
               '(seasons)\n'
               '(+11)|Loan\n'
               '(+12)|Suspension /\n'
               'injury\n'
               '(+13)',
 'squad.all99': 'All to 99 (Fit/Tec/Form)',
 'squad.count': '{n} players in the squad',
 'squad.note': 'Condition, technique and form are the current squad values; freshness ranges from 50 to 150. '
               'Contract is in seasons. Counter +13 is measured in matches for suspensions and weeks for '
               'injuries. Double-click or press Enter to edit a cell; Tab moves to the next cell.',
 'pl.search': 'Search:',
 'pl.club': 'Club:',
 'pl.all': 'All',
 'pl.cols': 'Player\n'
            'name|Age\n'
            '(years)|Condition\n'
            '(current)|Technique\n'
            '(current)|Form\n'
            '(current)|Position\n'
            'code\n'
            '(0–99)|Role\n'
            'group|League\n'
            'goals|League\n'
            'appearances|Current\n'
            'club',
 'pl.count': '{n} players',
 'std.facilities': 'Facilities',
 'std.ticket': 'Ticket price',
 'std.lights': 'Floodlights',
 'std.screen': 'Big screen',
 'std.condition_stadium': 'Stadium condition',
 'std.comfort': 'Comfort',
 'std.attendance': 'Attendance',
 'std.season_att': 'Season attendance',
 'std.record_att': 'Record attendance',
 'std.record_opp': 'Record opponent',
 'std.min_att': 'Lowest attendance',
 'std.min_opp': 'Lowest-attendance opponent',
 'std.expansions': 'Stadium expansions',
 'std.exp_items': 'Seats|Standing places|Covered places|Floodlights|Big screen|Condition|Comfort',
 'std.above': '(above)',
 'std.exp_cols': 'Item|Current|Under construction|Days left',
 'std.note': 'Floodlights, big screen, condition and comfort are set in the “Facilities” box.',
 'loan.bank': 'Bank',
 'loan.lender': 'Lender {n}',
 'loan.cols': 'From|Amount|Interest/month|Rate %|Start|Due',
 'loan.note': 'An amount of zero indicates an inactive loan. Dates use dd/mm/yyyy. When creating a loan, '
              'also set the interest (amount × rate / 100).',
 'sp.shirt': 'Shirt',
 'sp.board': 'Board',
 'sp.tv': 'TV',
 'sp.adcost': 'Advertising costs',
 'sp.income': 'Advertising income',
 'sp.item': 'Item',
 'sp.amount': 'Amount',
 'sp.contracts': 'Active contracts',
 'sp.contract_cols': 'Space|Months left|Sponsor no.',
 'sp.offers': 'Sponsor offers',
 'sp.offer_cols': 'Sponsor|Shirt: years|Shirt: amount|Boards: years|Boards: amount',
 'sp.note': "Income is stored in the manager's advertising table. Contract and offer fields are stored in "
            'the corresponding record.',
 'st.resort': 'Re-sort',
 'st.cols': 'Club|Total\n'
            'points|Goal\n'
            'difference|Home\n'
            'points|Away\n'
            'points|Home goals\n'
            'scored|Away goals\n'
            'scored|Home goals\n'
            'conceded|Away goals\n'
            'conceded|Home matches\n'
            'played|Away matches\n'
            'played|Home\n'
            'wins|Away\n'
            'wins|Home\n'
            'losses|Away\n'
            'losses|All-time\n'
            'points',
 'st.note': 'Total points are the sum of home and away points; goal difference is goals scored minus goals '
            'conceded. The other columns show home and away statistics separately. Rows are ordered by total '
            'points, then goal difference; “Re-sort” refreshes that order.',
 'res.round': 'Matchday {n}',
 'res.match': 'Match',
 'res.note': 'The savegame stores only the goals, not the teams of past matchdays. 255 = not played; 30 home '
             'goals = postponed match.',
 'cal.season': 'Current season',
 'cal.day': 'Day of the season',
 'cal.next': 'Next matchday (league {n})',
 'cal.matches': 'matches of the current matchday',
 'cal.note': 'Double-click a team to pick it from the list.',
 'cup.relegation': 'Relegation',
 'cup.first_leg': 'First leg',
 'cup.outcome': 'Outcome (1 = promoted)',
 'cup.round': 'Current round',
 'cup.legs_played': 'First leg played',
 'cup.qualified': 'German European qualifiers (list)',
 'cup.slots': 'European slots (3 × 6, 128 = free)',
 'cup.label': 'Cup:',
 'cup.goals_h': 'Goals H',
 'cup.goals_a': 'Goals A',
 'cup.first_leg_goals': 'European cups first leg (goals, 3 × 32)',
 'cup.note': 'For round goals: +10 after extra time, +20 after penalties.',
 'cl.search': 'Search club:',
 'cl.cols': 'Base|F1|F2|F3|T1|T2|T3|M1|M2|M3|Status',
 'cl.count': '{n} clubs',
 'cl.note': 'In this table: F = fitness, T = technique, M = form (three values each). Indices 0–17 first '
            'league, 18–37 second, 38–57 third, the rest foreign clubs.',
 'ser.note': 'The table contains 21 values describing the club’s current runs.',
 'rec.none': 'No clubs.',
 'rec.cols': 'Record|Value (a:b)|Opponent',
 'rec.note': 'Club records and the opponent. Each byte holds two values from 0 to 15, written as a:b.',
 'vs.note': "The manager's last 5 matches against each club, as goals against:goals for (max 15 per cell). "
            'Empty cell = no match.',
 'msg.manager': 'Manager {n} – {name}',
 'msg.none': 'No messages.',
 'msg.note': 'The ^ sign is a line break. You can change the text of existing messages (max 240 characters); '
             'adding or deleting messages would also require updating internal pointers and is not '
             'supported.',
 'grp.advanced': 'Advanced',
 'pg.market': 'Market',
 'pg.ext_standings': 'Extended standings',
 'pg.raw': 'Raw blocks',
 'std.capacity': 'Total capacity (computed)',
 'loan.total': 'Total debt',
 'loan.interest_total': 'Total monthly interest',
 'squad.avg': 'Squad average – Fit {c} · Tec {t} · Form {f}',
 'squad.extra_cols': 'Training\n'
                     'factor\n'
                     '(+14)|Player\n'
                     'index\n'
                     '(+15)|Condition\n'
                     '(+16)|Technique\n'
                     '(+17)|Form\n'
                     '(+18)|Freshness\n'
                     '(+19)|Training\n'
                     'program\n'
                     '(+20)|Match\n'
                     'rating\n'
                     '(+21, i8)|Offering\n'
                     'club\n'
                     '(+22)|Injury\n'
                     'type\n'
                     '(+23)|Negotiation /\n'
                     'career status\n'
                     '(+24)|Horizontal\n'
                     'coordinate X\n'
                     '(i8, +25)|Depth\n'
                     'coordinate Y\n'
                     '(u8, +26)|Byte +27\n'
                     '(unknown)|League\n'
                     'appearances\n'
                     '(+28, u16)|Cup\n'
                     'appearances\n'
                     '(+30, u16)|Europe\n'
                     'appearances\n'
                     '(+32, u16)|League\n'
                     'goals\n'
                     '(+34, u16)|Cup\n'
                     'goals\n'
                     '(+36, u16)|Europe\n'
                     'goals\n'
                     '(+38, u16)|Monthly\n'
                     'wage\n'
                     '(i32, +40–43)|Bytes +44–47\n'
                     '(unknown)|Notification\n'
                     'pointer\n'
                     '(i32, +48)',
 'pl.extra_cols': 'Initial\naverage\n(+27)|Side\npreference\n(+32)|Owner /\nmarket state\n(+33)',
 'squad.extra_note': 'Monthly wage: signed 32-bit integer at bytes +40–43. Bytes +44–47 have no assigned '
                     'function.',
 'pl.note': '+27 = initial average of condition, technique and form; it does not track current attributes. '
            '+32 (0–6) = side preference used by automatic formation to choose the horizontal column. +33: '
            '0–3 managers, 4 transfer market, 5 free. Role +31: 0–24 goalkeeper, 25–49 defender, 50–74 '
            'midfielder, 75–99 forward.',
 'pl.owner_market': 'Market',
 'pl.owner_free': 'Free',
 'mk.cols': 'Player|Role|Rejected\n'
            'offers\n'
            '(+3)|Status flags\n'
            '(+9)|Loan\n'
            '(+12)|Suspension /\n'
            'injury\n'
            '(+13)|Training\n'
            'factor\n'
            '(+14)|Player-table\n'
            'index\n'
            '(+15)|Condition\n'
            '(+16)|Technique\n'
            '(+17)|Form\n'
            '(+18)|Freshness\n'
            '(+19)|Training\n'
            'program\n'
            '(+20)|Match rating\n'
            '(i8, +21)|Offering club\n'
            '(+22)|Injury type\n'
            '(+23)|Negotiation /\n'
            'career status\n'
            '(+24)|Byte +27\n'
            '(unmapped)|Market value\n'
            '(i32, +40)|Bytes +44–47\n'
            '(unmapped)|Message pointer\n'
            '(i32, +48)',
 'mk.count': '{n} players listed',
 'mk.note': 'The market uses slots 100–111. +40–43 = economic value (i32); +3 = rejected offers by manager; '
            '+9 = status flags; +12 = loan; +13 = suspension matches or injury weeks; +22 = offering club; '
            '+23 = injury type; +14 and +20 = training; +21 = match rating; +24 = contract/career status; '
            '+27 and +44–47 = unidentified fields; +48–51 = notification pointer.',
 'xs.cols': 'Series A (b4–11)|Series B (b13–20)|?2|?3|?24|?25|?28|?29|?40|?41|?44|?45|?46|b32–37',
 'xs.note': 'Complete 54-byte standings record for each club. The two hexadecimal series contain two 4-bit '
            'values per byte.',
 'cal.perm': 'Fixture draw order (20 values per league)',
 'cal.perm_note': 'Permutation of team slots used to build the fixture list (1st league 0–19, 2nd 20–39, 3rd '
                  '40–59). Changing it alters the future matchdays.',
 'raw.block5': 'Postponed fixtures: 20 × 5-byte records (5457–5556)',
 'raw.cols5': 'Identifier\n(+0)|Day index\n(+1)|League round\n(+2)|League\n(+3)|Fixture index\n(+4)',
 'raw.tail1': 'Tail block 34063–34223',
 'raw.tail2': 'Tail block 34226–34366',
 'raw.note': 'Offsets are absolute positions in the decoded buffer. Byte 34367 is shown on the Cups page; '
             'messages from 34368 onward are handled on the Messages page.',
 'std.home_games': 'Home matches played',
 'std.avg_att': 'Average attendance (computed)',
 'prof.mgmt_items': 'Match intensity (0–34)|Youth grants (0–34)|Balls: fitness|Balls: play|Balls: '
                    'shooting|Balls: tactics|Morale (0–40)|Matches with crowd|Training intensity|Goalkeeper '
                    'training|Defence training|Midfield training|Attack training',
 'prof.portrait_id': 'Portrait (1–4)',
 'prof.extra': 'Other fields',
 'prof.extra_item': 'Byte +{off}',
 'prof.extra_note': '+480 and +482 are separate 16-bit values. +480 is recalculated by the game; +482 has no '
                    'assigned meaning. The remaining fields have no available description.',
 'stats.chart': 'Attendance chart',
 'pg.options': 'Game options',
 'opt.panel': 'Game options (ON/OFF)',
 'opt.series': 'League 1|League 2|League 3',
 'opt.items': 'Half-time scores|Final scores|Table',
 'opt.others': 'Match scenes|National cup|European cups|Postponed matches|Newspaper|Fade effects',
 'opt.other': 'Other options',
 'opt.speed': 'Game speed',
 'opt.speed_byte': 'Speed (0–70)',
 'opt.note': 'Use the checkboxes to enable or disable the corresponding display options.',
 'info.version': 'Version',
 'info.unknown': 'unknown',
 'info.edited': 'EDITED WITH THE EDITOR',
 'info.ingame': 'in-game',
 'info.bmp_ita_mod': 'ITA mod on German EXE',
 'raw.recovery_note': 'The 20 five-byte records describe postponed fixtures: identifier, day index, '
                      'matchday, league and fixture.',
 'raw.unknown_area': 'Additional data and unidentified areas (34063–34221)',
 'raw.unknown_34063': '34063–34064 · 2 unidentified bytes',
 'raw.unknown_34065': '34065–34094 · 30 undecoded bytes',
 'raw.unknown_34095': '34095–34098 · 4 undecoded bytes',
 'raw.unknown_34215': '34215–34221 · 7 unidentified bytes',
 'raw.calendar_title': 'Calendar index and league schedule mask table (34226–34321)',
 'raw.calendar_index': 'Current index (byte 34226)',
 'raw.calendar_index_note': 'The game uses this byte as an index into the table below. It is not the '
                            'displayed matchday number.',
 'raw.calendar_mask': 'Three-league progression mask · 95 bytes (34227–34321)',
 'raw.daily_words': 'Eight 16-bit values updated during the daily cycle (34322–34337)',
 'raw.trailing_values': 'Other values in the final data block (34338–34366)',
 'raw.unknown_byte': 'Unidentified byte (34338)',
 'raw.offset': 'Offset',
 'raw.word_value': '16-bit value',
 'raw.dword_value': '32-bit value',
 'tip.recovery_marker': 'Byte +0: identifier for the postponed-fixture record.',
 'tip.recovery_day_index': 'Byte +1: calendar-day index associated with the replay.',
 'tip.recovery_matchday': 'Byte +2: original league matchday.',
 'tip.recovery_league': 'Byte +3: league index (0, 1 or 2).',
 'tip.recovery_fixture': 'Byte +4: fixture index within the matchday.',
 'tip.raw_34063': '16-bit value identifying game type and duration. Known values: 22222/22251 = endless; '
                  '1964/1993 = one year; 1966/1995 = three years. Each pair distinguishes historical and '
                  'normal starts.',
 'tip.raw_34065': '30-byte area (34065–34094) with no assigned function.',
 'tip.raw_34095': 'Four bytes (34095–34098) before the rules selector; function not identified.',
 'tip.raw_34215': 'Seven day counters for stadium-expansion lockouts.',
 'tip.calendar_mask': '95-byte binary table. Index +34226 selects the current byte; its bits indicate which '
                      'leagues advance to the next matchday.',
 'tip.daily_word': 'Signed 16-bit availability counter for a training ground.',
 'tip.save_offset': 'Absolute offset of this field in the decoded savegame buffer.',
 'tip.trailing_dword': 'One of seven 32-bit values (34339–34366). The field size is known, but its '
                       'operational meaning has not been identified.',
 'mark.name': 'CHEATER',
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
 'tip.series_unverified': 'Value in the manager’s run-statistics sequence.',
 'tip.player_index': 'Index of the linked player in the 151-record player table; stored in squad-slot byte '
                     '+15.',
 'tip.unknown_bytes42': 'Squad-slot bytes +42–43; function not identified.',
 'tip.player': 'Player name linked to this squad or transfer-market slot.',
 'tip.role_group': 'Role group derived from the player position code: goalkeeper, defender, midfielder or '
                   'forward.',
 'tip.shirt_number': 'Shirt number assigned to the player.',
 'tip.condition_current': 'Player current condition in the squad.',
 'tip.technique_current': 'Player current technique value.',
 'tip.form_current': 'Player current form.',
 'tip.freshness': 'Current freshness/fatigue value, stored separately from condition, technique and form.',
 'tip.monthly_wage': 'Player monthly wage. The operational creation and contract routines read and write the '
                     'complete 32-bit field at +40–43; records.ts exposes a u16 accessor for only +40–41. '
                     'The editor displays the full i32 value.',
 'tip.contract_seasons': 'Contract duration expressed in seasons.',
 'tip.suspension_injury': 'Remaining suspension matches or injury weeks. The event type is indicated by the '
                          'status flags.',
 'tip.yellow_cards': 'Number of yellow cards recorded for the player.',
 'tip.direct_reds': 'Number of direct red cards recorded for the player.',
 'tip.league_goals': 'Goals scored by the player in the league.',
 'tip.league_appearances': 'Player appearances in the league.',
 'tip.training_factor': 'Individual factor modifying training effectiveness; 50 is the neutral factor.',
 'tip.training_program': 'Training program encoded in bits: remaining duration, intensity and direction of '
                         'change.',
 'tip.pitch_column': 'Horizontal X coordinate stored in roster-slot byte +25. The game interprets it as '
                     'int8; automatic formations start from columns 0–6 and may swap columns according to '
                     'each player’s side preference.',
 'tip.pitch_line': 'Depth Y coordinate stored in roster-slot byte +26 (0–7): 0 toward the opponents’ goal, 7 '
                   'toward your own. Starters in the same line normally share a depth, with small '
                   'formation-specific offsets.',
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
 'tip.unknown_byte27': 'Squad-record byte +27; function not identified.',
 'tip.unknown_bytes44': 'Squad-record bytes +44–47; function not identified.',
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
 'tip.preferred_side': 'Player side preference (0–6), used by automatic formation to choose or adjust the '
                       'horizontal column.',
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
 'tip.club_status': 'Club status code.',
 'tip.external_series_a': '8-byte hexadecimal block associated with Series A; each byte contains two 4-bit '
                          'values.',
 'tip.external_series_b': '8-byte hexadecimal block associated with Series B; each byte contains two 4-bit '
                          'values.',
 'tip.club_record_unknown': 'Byte +{offset} of the 54-byte club record.',
 'tip.club_record_tail': 'Hexadecimal values of club-record bytes +32–37.',
 'tip.raw_record_byte': 'Byte +{offset} of the raw 5-byte record shown in this table.',
 'tip.raw_block_values': 'Consecutive values in the data block beginning at offset {start}.',
 'tip.series_column': 'Value {number} in the club run-statistics sequence.',
 'tip.record': 'Name of the record held by the club.',
 'tip.record_value': 'Record value shown as a pair of numbers from 0 to 15 (a:b).',
 'tip.record_opponent': 'Opponent club associated with the record.',
 'tip.versus_home': 'One of the manager’s last 5 matches against this club, played at home. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'tip.versus_away': 'One of the manager’s last 5 matches against this club, played away. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'squad.hint': 'Saved player positions: +25 = horizontal X (i8); +26 = depth Y (0–7: 0 toward the opponents’ '
               'goal, 7 toward your own). Shirt numbers 1–11 identify starters. The manager’s formation '
               'selector is at byte 51 + 2 × manager index: 1 manual, 2 = 4-4-2, 3 = 3-5-2, 4 = 3-4-3; the '
               'following byte is its backup. Double-click or press Enter to edit a cell; Tab moves to the '
               'next one.',
 'pl.hint': 'All players in the savegame. Headings describe the player master-record fields and current '
            'values.',
 'mk.hint': 'The transfer market uses slots 100–111. Hover over a heading to read the extended field '
            'description.',
 'tip.european_first_leg_goals': 'Goals from the first-leg matches in European competitions, stored in the '
                                 'cup-results block.',
 'squad.formation_info': 'Saved system: {active} · Backup: {backup}',
 'squad.system_manual': 'Manual',
 'squad.system_unknown': 'Unrecognised ({value})',
 'opt.items_full': 'Half-time scores · League 1|Final scores · League 1|Table · League 1|Half-time scores · '
                   'League 2|Final scores · League 2|Table · League 2|Half-time scores · League 3|Final '
                   'scores · League 3|Table · League 3|Goal scenes|National cup|European cups|Postponed '
                   'matches|Newspaper|Fade effects',
 'opt.option_name': 'Option',
 'opt.raw_byte': 'State',
 'tip.runtime_option': 'Display switch from the game options menu.',
 'tip.runtime_option_value': 'State of the display switch.',
 'opt.speed_value': 'Speed (0–70)',
 'opt.speed_note': 'Allowed range: 0–70. Default value: 40.',
 'tip.speed_runtime': '16-bit game-speed value (0–70).',
 'raw.game_type': 'Game type and duration (34063–34064)',
 'raw.end_year_code': 'Type/duration code (u16)',
 'raw.end_year_meaning': 'Interpretation',
 'raw.endyear_endless_historical': 'Endless game · historical start',
 'raw.endyear_endless': 'Endless game · normal start',
 'raw.endyear_one_historical': '1-year game · historical start',
 'raw.endyear_one': '1-year game · normal start',
 'raw.endyear_three_historical': '3-year game · historical start',
 'raw.endyear_three': '3-year game · normal start',
 'raw.endyear_other': 'Unrecognized value ({value})',
 'raw.rule_2026': 'Game rules selector (34099)',
 'raw.rule_value': 'Ruleset',
 'raw.rules_original': '1993 rules',
 'raw.rules_2026': '2026 rules',
 'raw.poach_counts': 'Transfers between managers (34100–34115)',
 'raw.manager_number': 'Manager {n}',
 'raw.poacher': 'Poaching manager',
 'raw.owner_manager': 'Owner {n}',
 'raw.poach_note': 'Number of completed transfers for each buying-manager/owning-manager pair.',
 'raw.unknown_34116_label': 'Undecoded byte (+34116)',
 'raw.debt_mask': 'Purchase-ban mask (+34117)',
 'raw.derby_stakes': 'Derby stake per manager (34118–34121)',
 'raw.derby_levels': 'DM 50,000|DM 100,000|DM 250,000|DM 500,000',
 'raw.manager': 'Manager',
 'raw.stake': 'Stake level',
 'raw.youth_counts': 'Youth-team counters (34122–34129)',
 'raw.promotions': 'Youth promotions to first team',
 'raw.youth_poached': 'Recently promoted players poached',
 'raw.youth_note': 'Per-manager values: youth players promoted to the first team and youth players '
                   'transferred to another manager. Counters reset at the start of a season.',
 'raw.unknown_34130': '34130–34214 · 85 undecoded bytes',
 'raw.stadium_lockout': 'Stadium expansion lockout days by type (34215–34221)',
 'raw.speed_snapshot': 'Game-speed word (34222–34223)',
 'raw.speed_value': 'Speed (0–70)',
 'tip.rule_2026': '0 = 1993 rules; 1 = 2026 rules.',
 'tip.poach_count_row': 'Buying manager (row). The four cells indicate the owning manager.',
 'tip.poach_count': 'Number of completed transfers for this buying-manager/owner pair.',
 'tip.debt_mask': 'Purchase-block mask for debt: one bit per manager. Threshold: balance below −1,000,000 '
                  'DM.',
 'tip.manager_index': 'Manager index, from 0 to 3.',
 'tip.derby_stake': 'Derby stake level: 0 = 50,000 DM, 1 = 100,000 DM, 2 = 250,000 DM, 3 = 500,000 DM.',
 'tip.youth_promotions': 'Number of youth players promoted to the first team this season for this manager.',
 'tip.youth_poach': 'Number of youth players promoted and then transferred to another manager this season.',
 'tip.raw_34130': '85-byte area (34130–34214) with no assigned function.',
 'tip.stadium_lockout': 'Seven day-lockout counters for stadium expansion types. The original code sets a '
                        'random 15–55 day lockout after an expansion offer is refused. The 34215 base is '
                        'known; keep the exact mapping of the seven indices to expansion types cautious.',
 'raw.training_camps': 'Availability of the 8 training camps (34322–34337)',
 'raw.camp_number': 'Camp',
 'raw.camp_status': 'Availability',
 'raw.camp_counter': 'Remaining counter (i16)',
 'raw.camp_open_days': 'Open · {days} days',
 'raw.camp_closed_days': 'Closed · {days} days',
 'raw.camp_changeover': 'State change',
 'raw.camp_note': 'Eight signed 16-bit values, one per training ground. Negative = open; positive = closed. '
                  'The counter moves one day toward zero; at zero it restarts with the opposite sign and a '
                  'duration of 20–70 days.',
 'tip.camp_number': 'Training-ground index (1–8).',
 'tip.camp_status': 'Negative = open; positive = closed; zero = changeover. Absolute value gives remaining '
                    'days.',
 'tip.camp_counter': 'Signed 16-bit value at offset 34322 + 2 × index. Decreases by one per day to zero, '
                     'then restarts with the opposite sign and a duration of 20–70 days.',
 'raw.additional_fields': 'Other additional fields (34116–34129)'}
