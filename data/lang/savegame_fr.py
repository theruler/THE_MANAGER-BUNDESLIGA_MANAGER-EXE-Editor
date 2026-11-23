# -*- coding: utf-8 -*-

LANG_NAME = 'Français'

TEXTS_FR = {'grp.manager': 'Manager',
 'grp.squad': 'Équipe',
 'grp.economy': 'Économie',
 'grp.league': 'Championnat',
 'grp.cups': 'Coupes',
 'grp.clubs': 'Clubs',
 'grp.messages': 'Messages',
 'pg.profile': 'Profil',
 'pg.history': 'Historique',
 'pg.stats': 'Statistiques',
 'pg.roster': 'Effectif',
 'pg.players': 'Joueurs',
 'pg.stadium': 'Stade',
 'pg.loans': 'Emprunts',
 'pg.sponsors': 'Sponsors',
 'pg.standings': 'Classement',
 'pg.results': 'Résultats',
 'pg.calendar': 'Calendrier',
 'pg.cup_state': 'État',
 'pg.cup_ties': 'Confrontations',
 'pg.clubs': 'Données des clubs',
 'pg.series': 'Séries en cours',
 'pg.records': 'Records',
 'pg.versus': 'Confrontations directes',
 'pg.messages': 'Messages',
 'err.too_short': 'Fichier trop court : ce n’est pas une sauvegarde BMP.',
 'err.bad_sig': 'Signature invalide : ce n’est pas une sauvegarde BMP.',
 'err.chk1': 'Checksum 1 incorrect.',
 'err.chk2': 'Checksum 2 incorrect.',
 'err.truncated': 'Fichier endommagé ou tronqué.',
 'err.verify': 'Échec de la vérification après relecture.',
 'err.page': 'Erreur dans cette page : {error}',
 'pos.gk': 'GB',
 'pos.df': 'DEF',
 'pos.mf': 'MIL',
 'pos.fw': 'ATT',
 'tb.savegame': 'Sauvegarde :',
 'tb.folder': 'Dossier…',
 'tb.open': 'Ouvrir un fichier…',
 'tb.save': 'Enregistrer .MAN',
 'tb.save_as': 'Enregistrer sous…',
 'tb.manager': 'Manager :',
 'ph.no_dir': 'Aucun dossier sélectionné.\nUtilisez « Ouvrir un fichier… » pour ouvrir une sauvegarde .MAN.',
 'ph.none': 'Aucun fichier .MAN trouvé dans :\n{dir}',
 'ph.pick': '{n} fichier(s) .MAN trouvé(s).\n'
            'Sélectionnez une sauvegarde dans la liste ci-dessus pour l’ouvrir.',
 'dlg.title': 'Éditeur de sauvegarde',
 'dlg.folder': 'Dossier contenant les sauvegardes .MAN',
 'dlg.open': 'Ouvrir la sauvegarde',
 'dlg.save_as': 'Enregistrer la sauvegarde sous',
 'dlg.type_man': 'Sauvegarde BMP',
 'dlg.type_all': 'Tous les fichiers',
 'dlg.discard': '{name} contient des modifications non enregistrées. Les abandonner ?',
 'dlg.roundtrip': 'À l’ouverture, le réencodage n’était PAS identique à l’original.\n'
                  'Enregistrer quand même ?',
 'dlg.save_failed': 'Échec de l’enregistrement :\n{error}',
 'status.none': 'Aucune sauvegarde chargée.',
 'status.loaded_ok': '{name} : checksum OK, réencodage identique : oui',
 'status.loaded_warn': '{name} : checksum OK, réencodage identique : NON – enregistrer avec prudence',
 'status.saved': '{name} enregistré, checksums recalculés{backup}.',
 'status.backup': ' (sauvegarde .bak créée)',
 'status.dirty': '● Modifications non enregistrées',
 'mgr.item': 'Manager {n} : {name}',
 'c.club': 'Club',
 'c.name': 'Nom',
 'c.home': 'Domicile',
 'c.away': 'Ext.',
 'c.away_full': 'Extérieur',
 'c.home_team': 'Équipe à domicile',
 'c.away_team': 'Équipe visiteuse',
 'lbl.league': 'Ligue :',
 'lists.leagues': 'Première ligue|Deuxième ligue|Troisième ligue',
 'lists.titles': 'Titres de championnat|Coupe nationale|Coupe des champions|Coupe des vainqueurs de '
                 'coupe|Coupe UEFA',
 'lists.cups': 'Coupe nationale|Coupe des champions|Coupe des vainqueurs de coupe|Coupe UEFA',
 'lists.sizes': 'Aucun|Petit|Moyen|Grand',
 'lists.grade_1': '1 – Insuffisant',
 'lists.grade_6': '6 – Excellent',
 'lists.records': 'Victoires à domicile|Défaites à domicile|Buts marqués à domicile|Buts encaissés à '
                  'domicile|Victoires à l’extérieur|Défaites à l’extérieur|Buts marqués à l’extérieur|Buts '
                  'encaissés à l’extérieur',
 'prof.identity': 'Identité et trésorerie',
 'prof.name': 'Nom du manager',
 'prof.cash': 'Trésorerie',
 'prof.date': 'Date (j / m / année)',
 'prof.level': 'Niveau (1–5)',
 'prof.mgmt': 'Gestion de l’équipe',
 'prof.internal': 'Valeurs internes',
 'prof.internal_items': 'Ligue (0/1/2)|Barrage (octet 265)|Indicateur de saison (octet 320)',
 'prof.note': 'Lors d’un changement de club, la ligue (0/1/2) est également mise à jour.',
 'hist.palmares': 'Palmarès',
 'hist.seasons_played': 'Saisons jouées',
 'hist.titles': 'Titres : {name}',
 'hist.round': 'Tour en cours : {name}',
 'hist.balance': 'Bilan général',
 'hist.balance_items': 'Points|Buts marqués|Buts encaissés|Victoires|Défaites|Matchs nuls|Matchs joués|?432 '
                       '(signé)',
 'hist.seasons': 'Saisons',
 'hist.add': '+ Ajouter une saison',
 'hist.remove': '− Supprimer la dernière',
 'hist.season_cols': 'Position|Ligue|Coupe nat.|Europe',
 'hist.note': 'Max. 50 saisons ; la nouvelle ligne copie la précédente. Position : 1–18 première ligue, '
              '19–38 deuxième, 39–58 troisième ; 255 = pas encore manager. Dans les coupes, le bit 7 (+128) '
              'indique une victoire.',
 'stats.positions': 'Position au classement par journée',
 'stats.attendance': 'Spectateurs par match (milliers)',
 'stats.series': 'Séries record du manager (21 valeurs)',
 'stats.note': 'Les séries statistiques comprennent sept catégories pour le total, le domicile et '
               'l’extérieur. Les octets 267–304 et 330–346 stockent l’historique par journée.',
 'squad.cols': 'Joueur|Poste|Rouges\n'
               'directs (+0)|Cartons jaunes\n'
               '(+1)|Rouge après\n'
               '2e jaune (+2)|Buts en\n'
               'championnat\n'
               '(+3)|Buts en coupe\n'
               'nationale (+4)|Buts en\n'
               'Europe (+5)|Matchs de\n'
               'championnat\n'
               '(+6)|Matchs en coupe\n'
               'nationale (+7)|Matchs en\n'
               'Europe (+8)|Flags d’état\n'
               '(+9)|N° de maillot\n'
               '(+10)|Contrat\n'
               '(saisons)\n'
               '(+11)|Prêt\n'
               '(+12)|Suspension /\n'
               'blessure\n'
               '(+13)',
 'squad.all99': 'Tout à 99 (Cond./Tech./Forme)',
 'squad.count': '{n} joueurs dans l’effectif',
 'squad.note': 'Condition, technique et forme sont les valeurs actuelles de l’effectif ; la fraîcheur va de '
               '50 à 150. Le contrat est exprimé en saisons. Le compteur +13 correspond aux matchs pour une '
               'suspension et aux semaines pour une blessure. Double-clic ou Entrée pour modifier ; Tab '
               'passe à la cellule suivante.',
 'pl.search': 'Rechercher :',
 'pl.club': 'Club :',
 'pl.all': 'Tous',
 'pl.cols': 'Nom du\n'
            'joueur|Âge\n'
            '(années)|Condition\n'
            '(actuelle)|Technique\n'
            '(actuelle)|Forme\n'
            '(actuelle)|Code de\n'
            'poste\n'
            '(0–99)|Groupe de\n'
            'poste|Buts en\n'
            'championnat|Matchs de\n'
            'championnat|Club\n'
            'actuel',
 'pl.count': '{n} joueurs',
 'std.facilities': 'Installations',
 'std.ticket': 'Prix du billet',
 'std.lights': 'Projecteurs',
 'std.screen': 'Écran géant',
 'std.condition_stadium': 'État du stade',
 'std.comfort': 'Confort',
 'std.attendance': 'Affluence',
 'std.season_att': 'Affluence de la saison',
 'std.record_att': 'Record d’affluence',
 'std.record_opp': 'Adversaire du record',
 'std.min_att': 'Affluence minimale',
 'std.min_opp': 'Adversaire de l’affluence minimale',
 'std.expansions': 'Agrandissements du stade',
 'std.exp_items': 'Places assises|Places debout|Places couvertes|Projecteurs|Écran géant|État|Confort',
 'std.above': '(ci-dessus)',
 'std.exp_cols': 'Élément|Actuel|En construction|Jours restants',
 'std.note': 'Les projecteurs, l’écran géant, l’état et le confort se règlent dans la section « '
             'Installations ».',
 'loan.bank': 'Banque',
 'loan.lender': 'Prêteur {n}',
 'loan.cols': 'De|Montant|Intérêts/mois|Taux %|Début|Échéance',
 'loan.note': 'Un montant égal à zéro indique un prêt inactif. Dates au format JJ/MM/AAAA. Lors de la '
              'création d’un prêt, renseigner également les intérêts (montant × taux / 100).',
 'sp.shirt': 'Maillot',
 'sp.board': 'Panneau publicitaire',
 'sp.tv': 'TV',
 'sp.adcost': 'Dépenses publicitaires',
 'sp.income': 'Revenus publicitaires',
 'sp.item': 'Élément',
 'sp.amount': 'Montant',
 'sp.contracts': 'Contrats actifs',
 'sp.contract_cols': 'Emplacement|Mois restants|N° de sponsor',
 'sp.offers': 'Offres des sponsors',
 'sp.offer_cols': 'Sponsor|Maillot : années|Maillot : montant|Panneaux : années|Panneaux : montant',
 'sp.note': 'Les recettes sont stockées dans le tableau publicitaire du manager. Les champs de contrat et '
            'd’offre figurent dans l’enregistrement correspondant.',
 'st.resort': 'Trier à nouveau',
 'st.cols': 'Club|Points\n'
            'totaux|Différence\n'
            'de buts|Points\n'
            'à domicile|Points\n'
            'à l’extérieur|Buts marqués\n'
            'à domicile|Buts marqués\n'
            'à l’extérieur|Buts encaissés\n'
            'à domicile|Buts encaissés\n'
            'à l’extérieur|Matchs joués\n'
            'à domicile|Matchs joués\n'
            'à l’extérieur|Victoires\n'
            'à domicile|Victoires\n'
            'à l’extérieur|Défaites\n'
            'à domicile|Défaites\n'
            'à l’extérieur|Points\n'
            'historiques',
 'st.note': 'Les points totaux sont la somme des points à domicile et à l’extérieur ; la différence de buts '
            'correspond aux buts marqués moins les buts encaissés. Les autres colonnes séparent les '
            'statistiques à domicile et à l’extérieur. Le tri se fait par points totaux, puis par différence '
            'de buts ; « Trier à nouveau » actualise cet ordre.',
 'res.round': 'Journée {n}',
 'res.match': 'Match',
 'res.note': 'La sauvegarde mémorise uniquement les buts, pas les équipes des journées précédentes. 255 = '
             'non joué ; 30 buts à domicile = match reporté.',
 'cal.season': 'Saison en cours',
 'cal.day': 'Jour de la saison',
 'cal.next': 'Prochaine journée (ligue {n})',
 'cal.matches': 'Matchs de la journée en cours',
 'cal.note': 'Double-cliquez sur une équipe pour la sélectionner dans la liste.',
 'cup.relegation': 'Barrages de relégation',
 'cup.first_leg': 'Aller',
 'cup.outcome': 'Résultat (1 = promu)',
 'cup.round': 'Tour en cours',
 'cup.legs_played': 'Match aller joué',
 'cup.qualified': 'Clubs allemands qualifiés pour l’Europe (liste)',
 'cup.slots': 'Places européennes (3 × 6, 128 = libre)',
 'cup.label': 'Coupe :',
 'cup.goals_h': 'Buts D',
 'cup.goals_a': 'Buts E',
 'cup.first_leg_goals': 'Matchs aller des coupes européennes (buts, 3 × 32)',
 'cup.note': 'Buts des tours : +10 après prolongation, +20 après tirs au but.',
 'cl.search': 'Rechercher un club :',
 'cl.cols': 'Base|C1|C2|C3|T1|T2|T3|F1|F2|F3|État',
 'cl.count': '{n} clubs',
 'cl.note': 'C = condition, T = technique, F = forme (trois valeurs chacune). Indices 0–17 première ligue, '
            '18–37 deuxième, 38–57 troisième ; le reste correspond aux clubs étrangers.',
 'ser.note': 'Le tableau contient 21 valeurs décrivant les séries en cours du club.',
 'rec.none': 'Aucun club.',
 'rec.cols': 'Record|Valeur (a:b)|Adversaire',
 'rec.note': 'Records des clubs et adversaire correspondant. Chaque octet contient deux valeurs de 0 à 15, '
             'écrites sous la forme a:b.',
 'vs.note': 'Les 5 derniers matchs du manager contre chaque club, sous la forme buts encaissés:buts marqués '
            '(max. 15 par cellule). Cellule vide = aucun match.',
 'msg.manager': 'Manager {n} – {name}',
 'msg.none': 'Aucun message.',
 'msg.note': 'Le signe ^ indique un saut de ligne. Vous pouvez modifier le texte des messages existants '
             '(max. 240 caractères) ; ajouter ou supprimer des messages nécessiterait aussi de mettre à jour '
             'les pointeurs internes, ce qui n’est pas pris en charge.',
 'grp.advanced': 'Avancé',
 'pg.market': 'Marché',
 'pg.ext_standings': 'Classement détaillé',
 'pg.raw': 'Blocs bruts',
 'std.capacity': 'Capacité totale (calculée)',
 'loan.total': 'Dette totale',
 'loan.interest_total': 'Total des intérêts mensuels',
 'squad.avg': 'Moyenne de l’effectif – Cond. {c} · Tech. {t} · Forme {f}',
 'squad.extra_cols': 'Facteur\n'
                     'd’entraînement\n'
                     '(+14)|Index du\n'
                     'joueur\n'
                     '(+15)|Condition\n'
                     '(+16)|Technique\n'
                     '(+17)|Forme\n'
                     '(+18)|Fraîcheur\n'
                     '(+19)|Programme\n'
                     'd’entraînement\n'
                     '(+20)|Note du\n'
                     'match\n'
                     '(+21, i8)|Club\n'
                     'offrant\n'
                     '(+22)|Type de\n'
                     'blessure\n'
                     '(+23)|Négociation /\n'
                     'carrière\n'
                     '(+24)|Coordonnée\n'
                     'horizontale X\n'
                     '(i8, +25)|Profondeur\n'
                     'verticale Y\n'
                     '(u8, +26)|Octet +27\n'
                     '(inconnu)|Apparitions\n'
                     'championnat\n'
                     '(+28, u16)|Apparitions\n'
                     'coupe\n'
                     '(+30, u16)|Apparitions\n'
                     'Europe\n'
                     '(+32, u16)|Buts\n'
                     'championnat\n'
                     '(+34, u16)|Buts\n'
                     'coupe\n'
                     '(+36, u16)|Buts\n'
                     'Europe\n'
                     '(+38, u16)|Salaire\n'
                     'mensuel\n'
                     '(i32, +40–43)|Octets +44–47\n'
                     '(inconnus)|Pointeur de\n'
                     'notification\n'
                     '(i32, +48)',
 'pl.extra_cols': 'Moyenne\ninitiale\n(+27)|Préférence\nlatérale\n(+32)|Propriétaire /\nétat marché\n(+33)',
 'squad.extra_note': 'Salaire mensuel : entier signé sur 32 bits aux octets +40–43. Aucune fonction n’est '
                     'attribuée aux octets +44–47.',
 'pl.note': '+27 = moyenne initiale de condition, technique et forme ; ne suit pas les caractéristiques '
            'actuelles. +32 (0–6) = préférence latérale utilisée par la formation automatique pour choisir '
            'la colonne horizontale. +33 : 0–3 managers, 4 marché, 5 libre. Rôle +31 : 0–24 gardien, 25–49 '
            'défenseur, 50–74 milieu, 75–99 attaquant.',
 'pl.owner_market': 'Marché',
 'pl.owner_free': 'Libre',
 'mk.cols': 'Joueur|Poste|Offres\n'
            'refusées\n'
            '(+3)|Flags d’état\n'
            '(+9)|Prêt\n'
            '(+12)|Suspension /\n'
            'blessure\n'
            '(+13)|Facteur\n'
            'd’entraînement\n'
            '(+14)|Index du\n'
            'joueur\n'
            '(+15)|Condition\n'
            '(+16)|Technique\n'
            '(+17)|Forme\n'
            '(+18)|Fraîcheur\n'
            '(+19)|Programme\n'
            'd’entraînement\n'
            '(+20)|Note du match\n'
            '(i8, +21)|Club offrant\n'
            '(+22)|Type de\n'
            'blessure\n'
            '(+23)|Négociation /\n'
            'carrière\n'
            '(+24)|Octet +27\n'
            '(non mappé)|Valeur marché\n'
            '(i32, +40)|Octets +44–47\n'
            '(non mappés)|Pointeur de\n'
            'message\n'
            '(i32, +48)',
 'mk.count': '{n} joueurs sur la liste',
 'mk.note': 'Le marché utilise les emplacements 100–111. +40–43 = valeur économique (i32) ; +3 = offres '
            'refusées par manager ; +9 = indicateurs d’état ; +12 = prêt ; +13 = matchs de suspension ou '
            'semaines de blessure ; +22 = club offreur ; +23 = type de blessure ; +14 et +20 = entraînement '
            '; +21 = note du match ; +24 = état du contrat/de la carrière ; +27 et +44–47 = champs non '
            'identifiés ; +48–51 = pointeur de notification.',
 'xs.cols': 'Série A (b4–11)|Série B (b13–20)|?2|?3|?24|?25|?28|?29|?40|?41|?44|?45|?46|b32–37',
 'xs.note': 'Enregistrement complet du classement, 54 octets par club. Les deux séries hexadécimales '
            'contiennent deux valeurs de 4 bits par octet.',
 'cal.perm': 'Ordre du tirage au sort du calendrier (20 valeurs par ligue)',
 'cal.perm_note': 'Permutation des emplacements des équipes utilisée pour construire le calendrier (1re '
                  'ligue 0–19, 2e 20–39, 3e 40–59). La modifier change le calendrier des prochaines '
                  'journées.',
 'raw.block5': 'Reports de matchs : 20 enregistrements de 5 octets (5457–5556)',
 'raw.cols5': 'Identifiant\n(+0)|Index du jour\n(+1)|Journée\n(+2)|Ligue\n(+3)|Index du match\n(+4)',
 'raw.tail1': 'Zones de données non décodées 34063–34221',
 'raw.tail2': 'Calendrier et données finales 34226–34366',
 'raw.note': 'Les offsets sont des positions absolues dans le tampon décodé. L’octet 34367 est affiché dans '
             'la page Coupes ; les messages à partir de 34368 sont gérés dans la page Messages.',
 'std.home_games': 'Matchs joués à domicile',
 'std.avg_att': 'Affluence moyenne (calculée)',
 'prof.mgmt_items': 'Intensité des matchs (0–34)|Aides aux jeunes (0–34)|Ballons : condition|Ballons : '
                    'jeu|Ballons : tir|Ballons : tactique|Moral (0–40)|Matchs avec public|Intensité de '
                    'l’entraînement|Entraînement des gardiens|Entraînement de la défense|Entraînement du '
                    'milieu|Entraînement de l’attaque',
 'prof.portrait_id': 'Portrait (1–4)',
 'prof.extra': 'Autres champs',
 'prof.extra_item': 'Octet +{off}',
 'prof.extra_note': '+480 et +482 sont deux valeurs 16 bits distinctes. +480 est recalculé par le jeu ; +482 '
                    'n’a pas de fonction attribuée. Les autres champs n’ont pas de description disponible.',
 'stats.chart': 'Historique de l’affluence',
 'pg.options': 'Options de jeu',
 'opt.panel': 'Options du jeu (ACTIVÉ/DÉSACTIVÉ)',
 'opt.series': 'Ligue 1|Ligue 2|Ligue 3',
 'opt.items': 'Scores à la mi-temps|Résultats finaux|Classement',
 'opt.others': 'Actions de match|Coupe nationale|Coupes européennes|Matchs reportés|Journal|Fondus',
 'opt.other': 'Autres options',
 'opt.speed': 'Vitesse du jeu',
 'opt.speed_byte': 'Vitesse (0–70)',
 'opt.note': 'Les cases à cocher activent ou désactivent les options d’affichage correspondantes.',
 'info.version': 'Version',
 'info.unknown': 'inconnue',
 'info.edited': 'MODIFIÉ AVEC L’ÉDITEUR',
 'info.ingame': 'en jeu',
 'info.bmp_ita_mod': 'mod ITA sur EXE allemand',
 'raw.recovery_note': 'Les 20 enregistrements de cinq octets décrivent les matchs reportés : identifiant, '
                      'index du jour, journée, ligue et match.',
 'raw.unknown_area': 'Données supplémentaires et zones non identifiées (34063–34221)',
 'raw.unknown_34063': '34063–34064 · 2 octets non décodés',
 'raw.unknown_34065': '34065–34094 · 30 octets non décodés',
 'raw.unknown_34095': '34095–34098 · 4 octets non décodés',
 'raw.unknown_34215': '34215–34221 · 7 octets non décodés',
 'raw.calendar_title': 'Index et masque du calendrier des ligues (34226–34321)',
 'raw.calendar_index': 'Index courant (octet 34226)',
 'raw.calendar_index_note': 'Le jeu utilise cet octet comme index d’un élément de la table suivante. Ce '
                            'n’est pas le numéro de journée affiché.',
 'raw.calendar_mask': 'Masque de progression des trois ligues · 95 octets (34227–34321)',
 'raw.daily_words': 'Huit valeurs 16 bits modifiées pendant le cycle quotidien (34322–34337)',
 'raw.trailing_values': 'Autres valeurs du bloc final (34338–34366)',
 'raw.unknown_byte': 'Octet non décodé (34338)',
 'raw.offset': 'Offset',
 'raw.word_value': 'Valeur 16 bits',
 'raw.dword_value': 'Valeur 32 bits',
 'mark.name': 'TRICHEUR',
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
 'tip.series_unverified': 'Valeur de la séquence statistique du manager.',
 'tip.player_index': 'Index du joueur associé dans la table des 151 joueurs ; stocké à l’octet +15 de '
                     'l’emplacement d’effectif.',
 'tip.unknown_bytes42': 'Octets +42–43 de l’emplacement d’effectif ; fonction non identifiée.',
 'tip.player': 'Player name linked to this squad or transfer-market slot.',
 'tip.role_group': 'Role group derived from the player position code: goalkeeper, defender, midfielder or '
                   'forward.',
 'tip.shirt_number': 'Shirt number assigned to the player.',
 'tip.condition_current': 'Player current condition in the squad.',
 'tip.technique_current': 'Player current technique value.',
 'tip.form_current': 'Player current form.',
 'tip.freshness': 'Current freshness/fatigue value, stored separately from condition, technique and form.',
 'tip.monthly_wage': 'Salaire mensuel du joueur. Les routines opérationnelles de création et de contrat '
                     'lisent et écrivent le champ complet de 32 bits +40–43 ; records.ts expose un accesseur '
                     'u16 limité à +40–41. L’éditeur affiche la valeur i32 complète.',
 'tip.contract_seasons': 'Contract duration expressed in seasons.',
 'tip.suspension_injury': 'Remaining suspension matches or injury weeks. The event type is indicated by the '
                          'status flags.',
 'tip.yellow_cards': 'Number of yellow cards recorded for the player.',
 'tip.direct_reds': 'Number of direct red cards recorded for the player.',
 'tip.league_goals': 'Goals scored by the player in the league.',
 'tip.league_appearances': 'Player appearances in the league.',
 'tip.training_factor': 'Individual factor modifying training effectiveness; 50 is the neutral factor.',
 'tip.training_program': 'Programme d’entraînement codé en bits : durée restante, intensité et sens de '
                         'variation.',
 'tip.pitch_column': 'Coordonnée X horizontale stockée dans l’octet +25 de l’emplacement d’effectif. Le jeu '
                     'la traite comme int8 ; les formations automatiques partent des colonnes 0–6 et peuvent '
                     'échanger les colonnes selon la préférence latérale du joueur.',
 'tip.pitch_line': 'Coordonnée de profondeur Y stockée dans l’octet +26 (0–7) : 0 vers le but adverse, 7 '
                   'vers le vôtre. Les titulaires d’une même ligne partagent normalement la profondeur, avec '
                   'de petits décalages propres au système.',
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
 'tip.unknown_byte27': 'Octet +27 de l’emplacement d’effectif ; fonction non identifiée.',
 'tip.unknown_bytes44': 'Octets +44–47 de l’emplacement d’effectif ; fonction non identifiée.',
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
 'tip.preferred_side': 'Préférence latérale du joueur (0–6), utilisée par la formation automatique pour '
                       'choisir ou ajuster la colonne horizontale.',
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
 'tip.club_status': 'Code d’état du club.',
 'tip.external_series_a': '8-byte hexadecimal block associated with Series A; each byte contains two 4-bit '
                          'values.',
 'tip.external_series_b': '8-byte hexadecimal block associated with Series B; each byte contains two 4-bit '
                          'values.',
 'tip.club_record_unknown': 'Octet +{offset} de l’enregistrement club de 54 octets.',
 'tip.club_record_tail': 'Valeurs hexadécimales des octets +32–37 de l’enregistrement club.',
 'tip.raw_record_byte': 'Byte +{offset} of the raw 5-byte record shown in this table.',
 'tip.raw_block_values': 'Valeurs consécutives du bloc de données commençant à l’offset {start}.',
 'tip.series_column': 'Valeur {number} de la séquence statistique du club.',
 'tip.record': 'Name of the record held by the club.',
 'tip.record_value': 'Record value shown as a pair of numbers from 0 to 15 (a:b).',
 'tip.record_opponent': 'Opponent club associated with the record.',
 'tip.versus_home': 'One of the manager’s last 5 matches against this club, played at home. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'tip.versus_away': 'One of the manager’s last 5 matches against this club, played away. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'squad.hint': 'Positions enregistrées : +25 = X horizontal (i8) ; +26 = profondeur Y (0–7 : 0 vers le but '
               'adverse, 7 vers le vôtre). Les numéros 1–11 identifient les titulaires. Le système du '
               'manager est au byte 51 + 2 × indice du manager : 1 manuel, 2 = 4-4-2, 3 = 3-5-2, 4 = 3-4-3 ; '
               'l’octet suivant est la sauvegarde. Double-cliquez ou appuyez sur Entrée pour modifier une '
               'cellule ; Tab passe à la suivante.',
 'pl.hint': 'All players in the savegame. Headings describe the player master-record fields and current '
            'values.',
 'mk.hint': 'The transfer market uses slots 100–111. Hover over a heading to read the extended field '
            'description.',
 'tip.european_first_leg_goals': 'Goals from the first-leg matches in European competitions, stored in the '
                                 'cup-results block.',
 'squad.formation_info': 'Système enregistré : {active} · Sauvegarde : {backup}',
 'squad.system_manual': 'Manuel',
 'squad.system_unknown': 'Non reconnu ({value})',
 'opt.items_full': 'Scores à la mi-temps · Ligue 1|Résultats finaux · Ligue 1|Classement · Ligue 1|Scores à '
                   'la mi-temps · Ligue 2|Résultats finaux · Ligue 2|Classement · Ligue 2|Scores à la '
                   'mi-temps · Ligue 3|Résultats finaux · Ligue 3|Classement · Ligue 3|Scènes de but|Coupe '
                   'nationale|Coupes européennes|Matchs reportés|Journal|Fondus',
 'opt.option_name': 'Option',
 'opt.raw_byte': 'État',
 'tip.runtime_option': 'Commutateur d’affichage du menu Options.',
 'tip.runtime_option_value': 'État du commutateur d’affichage.',
 'opt.speed_value': 'Vitesse (0–70)',
 'opt.speed_note': 'Plage autorisée : 0–70. Valeur par défaut : 40.',
 'tip.speed_runtime': 'Valeur 16 bits de la vitesse du jeu (0–70).',
 'raw.game_type': 'Type et durée de partie (34063–34064)',
 'raw.end_year_code': 'Code type/durée (u16)',
 'raw.end_year_meaning': 'Interprétation',
 'raw.endyear_endless_historical': 'Partie sans fin · départ historique',
 'raw.endyear_endless': 'Partie sans fin · départ normal',
 'raw.endyear_one_historical': 'Partie d’un an · départ historique',
 'raw.endyear_one': 'Partie d’un an · départ normal',
 'raw.endyear_three_historical': 'Partie de trois ans · départ historique',
 'raw.endyear_three': 'Partie de trois ans · départ normal',
 'raw.endyear_other': 'Valeur non reconnue ({value})',
 'raw.rule_2026': 'Sélecteur des règles (34099)',
 'raw.rule_value': 'Règles',
 'raw.rules_original': 'Règles 1993',
 'raw.rules_2026': 'Règles 2026',
 'raw.poach_counts': 'Transferts entre managers (34100–34115)',
 'raw.manager_number': 'Manager {n}',
 'raw.poacher': 'Manager recruteur',
 'raw.owner_manager': 'Propriétaire {n}',
 'raw.poach_note': 'Nombre de transferts conclus pour chaque paire manager acheteur/manager propriétaire.',
 'raw.unknown_34116_label': 'Octet non décodé (+34116)',
 'raw.debt_mask': 'Masque de blocage des achats (+34117)',
 'raw.derby_stakes': 'Mise du derby par manager (34118–34121)',
 'raw.derby_levels': '50 000 DM|100 000 DM|250 000 DM|500 000 DM',
 'raw.manager': 'Manager',
 'raw.stake': 'Niveau de mise',
 'raw.youth_counts': 'Compteurs du centre de formation (34122–34129)',
 'raw.promotions': 'Jeunes promus en équipe première',
 'raw.youth_poached': 'Jeunes récemment promus débauchés',
 'raw.youth_note': 'Valeurs par manager : jeunes promus en équipe première et jeunes transférés vers un '
                   'autre manager. Les compteurs sont remis à zéro au changement de saison.',
 'raw.unknown_34130': '34130–34214 · 85 octets non décodés',
 'raw.stadium_lockout': 'Jours de blocage par type d’agrandissement du stade (34215–34221)',
 'raw.speed_snapshot': 'Mot de vitesse du jeu (34222–34223)',
 'raw.speed_value': 'Vitesse (0–70)',
 'tip.raw_34063': 'Valeur 16 bits identifiant le type et la durée de partie. Valeurs connues : 22222/22251 = '
                  'illimitée ; 1964/1993 = un an ; 1966/1995 = trois ans. Les variantes distinguent le '
                  'départ historique du départ normal.',
 'tip.raw_34065': 'Zone de 30 octets (34065–34094) sans fonction attribuée.',
 'tip.raw_34095': 'Quatre octets (34095–34098) précédant le sélecteur de règles ; fonction non identifiée.',
 'tip.rule_2026': '0 = règles 1993 ; 1 = règles 2026.',
 'tip.poach_count_row': 'Manager acheteur (ligne). Les quatre cellules indiquent le manager propriétaire.',
 'tip.poach_count': 'Nombre de transferts conclus pour cette paire acheteur/propriétaire.',
 'tip.debt_mask': 'Masque de blocage des achats pour endettement : un bit par manager. Seuil : solde '
                  'inférieur à −1 000 000 DM.',
 'tip.manager_index': 'Indice du manager, de 0 à 3.',
 'tip.derby_stake': 'Niveau de mise du derby : 0 = 50 000 DM, 1 = 100 000 DM, 2 = 250 000 DM, 3 = 500 000 '
                    'DM.',
 'tip.youth_promotions': 'Nombre de jeunes promus en équipe première cette saison pour ce manager.',
 'tip.youth_poach': 'Nombre de jeunes promus puis transférés à un autre manager pendant la saison.',
 'tip.raw_34130': 'Zone de 85 octets (34130–34214) sans fonction attribuée.',
 'tip.stadium_lockout': 'Sept compteurs de jours de blocage pour les types d’agrandissement du stade. Le '
                        'code original définit un blocage aléatoire de 15 à 55 jours après le refus d’une '
                        'offre. L’offset de base 34215 est connu ; la correspondance exacte des sept indices '
                        'avec les types reste à traiter avec prudence.',
 'raw.training_camps': 'Disponibilité des 8 camps d’entraînement (34322–34337)',
 'raw.camp_number': 'Camp',
 'raw.camp_status': 'Disponibilité',
 'raw.camp_counter': 'Compteur restant (i16)',
 'raw.camp_open_days': 'Ouvert · {days} jours',
 'raw.camp_closed_days': 'Fermé · {days} jours',
 'raw.camp_changeover': 'Changement d’état',
 'raw.camp_note': 'Huit valeurs signées sur 16 bits, une par terrain d’entraînement. Négatif = ouvert ; '
                  'positif = fermé. Le compteur avance chaque jour vers zéro ; à zéro, il repart avec le '
                  'signe opposé et une durée de 20 à 70 jours.',
 'tip.camp_number': 'Indice du terrain d’entraînement (1–8).',
 'tip.camp_status': 'Négatif = ouvert ; positif = fermé ; zéro = changement d’état. La valeur absolue '
                    'indique les jours restants.',
 'tip.camp_counter': 'Valeur signée 16 bits à l’offset 34322 + 2 × indice. Diminue d’un jour jusqu’à zéro, '
                     'puis repart avec le signe opposé et une durée de 20 à 70 jours.',
 'tip.daily_word': 'Compteur signé 16 bits de disponibilité d’un terrain d’entraînement.',
 'tip.recovery_marker': 'Octet +0 : identifiant de l’enregistrement du match reporté.',
 'tip.recovery_day_index': 'Octet +1 : indice du jour de calendrier associé au report.',
 'tip.recovery_matchday': 'Octet +2 : journée initiale du championnat.',
 'tip.recovery_league': 'Octet +3 : indice de la ligue (0, 1 ou 2).',
 'tip.recovery_fixture': 'Octet +4 : indice du match dans la journée.',
 'tip.raw_34215': 'Sept compteurs de jours de blocage des agrandissements du stade.',
 'tip.calendar_mask': 'Table binaire de 95 octets. L’indice +34226 sélectionne l’octet courant ; ses bits '
                      'indiquent quelles ligues passent à la journée suivante.',
 'raw.additional_fields': 'Autres champs supplémentaires (34116–34129)'}
