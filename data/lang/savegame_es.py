# -*- coding: utf-8 -*-

LANG_NAME = 'Español'

TEXTS_ES = {'grp.manager': 'Manager',
 'grp.squad': 'Equipo',
 'grp.economy': 'Economía',
 'grp.league': 'Campeonato',
 'grp.cups': 'Copas',
 'grp.clubs': 'Clubes',
 'grp.messages': 'Mensajes',
 'pg.profile': 'Perfil',
 'pg.history': 'Historial',
 'pg.stats': 'Estadísticas',
 'pg.roster': 'Plantilla',
 'pg.players': 'Jugadores',
 'pg.stadium': 'Estadio',
 'pg.loans': 'Préstamos',
 'pg.sponsors': 'Patrocinadores',
 'pg.standings': 'Clasificación',
 'pg.results': 'Resultados',
 'pg.calendar': 'Calendario',
 'pg.cup_state': 'Estado',
 'pg.cup_ties': 'Emparejamientos',
 'pg.clubs': 'Datos de clubes',
 'pg.series': 'Rachas actuales',
 'pg.records': 'Récords',
 'pg.versus': 'Enfrentamientos directos',
 'pg.messages': 'Mensajes',
 'err.too_short': 'Archivo demasiado corto: no es una partida guardada BMP.',
 'err.bad_sig': 'Firma no válida: no es una partida guardada BMP.',
 'err.chk1': 'Checksum 1 incorrecto.',
 'err.chk2': 'Checksum 2 incorrecto.',
 'err.truncated': 'Archivo dañado o truncado.',
 'err.verify': 'Ha fallado la verificación tras la relectura.',
 'err.page': 'Error en esta página: {error}',
 'pos.gk': 'POR',
 'pos.df': 'DEF',
 'pos.mf': 'MED',
 'pos.fw': 'DEL',
 'tb.savegame': 'Partida guardada:',
 'tb.folder': 'Carpeta…',
 'tb.open': 'Abrir archivo…',
 'tb.save': 'Guardar .MAN',
 'tb.save_as': 'Guardar como…',
 'tb.manager': 'Manager:',
 'ph.no_dir': 'No se ha seleccionado ninguna carpeta.\nUsa «Abrir archivo…» para abrir una partida .MAN.',
 'ph.none': 'No se ha encontrado ningún archivo .MAN en:\n{dir}',
 'ph.pick': 'Se han encontrado {n} archivo(s) .MAN.\n'
            'Selecciona una partida de la lista superior para abrirla.',
 'dlg.title': 'Editor de partidas guardadas',
 'dlg.folder': 'Carpeta de partidas .MAN',
 'dlg.open': 'Abrir partida',
 'dlg.save_as': 'Guardar partida como',
 'dlg.type_man': 'Partida BMP',
 'dlg.type_all': 'Todos los archivos',
 'dlg.discard': '{name} tiene cambios sin guardar. ¿Descartarlos?',
 'dlg.roundtrip': 'Al abrir el archivo, la recodificación NO era idéntica al original.\n'
                  '¿Guardar de todos modos?',
 'dlg.save_failed': 'No se ha podido guardar:\n{error}',
 'status.none': 'No hay ninguna partida cargada.',
 'status.loaded_ok': '{name}: checksum OK, recodificación idéntica: sí',
 'status.loaded_warn': '{name}: checksum OK, recodificación idéntica: NO – guardar con precaución',
 'status.saved': '{name} guardado, checksums recalculados{backup}.',
 'status.backup': ' (copia de seguridad .bak creada)',
 'status.dirty': '● Cambios sin guardar',
 'mgr.item': 'Manager {n}: {name}',
 'c.club': 'Club',
 'c.name': 'Nombre',
 'c.home': 'Casa',
 'c.away': 'Fuera',
 'c.away_full': 'Fuera',
 'c.home_team': 'Equipo local',
 'c.away_team': 'Equipo visitante',
 'lbl.league': 'Liga:',
 'lists.leagues': 'Primera liga|Segunda liga|Tercera liga',
 'lists.titles': 'Títulos de liga|Copa nacional|Copa de Campeones|Recopa de Europa|Copa de la UEFA',
 'lists.cups': 'Copa nacional|Copa de Campeones|Recopa de Europa|Copa de la UEFA',
 'lists.sizes': 'Ninguno|Pequeño|Mediano|Grande',
 'lists.grade_1': '1 – Insuficiente',
 'lists.grade_6': '6 – Excelente',
 'lists.records': 'Victorias en casa|Derrotas en casa|Goles a favor en casa|Goles en contra en '
                  'casa|Victorias fuera|Derrotas fuera|Goles a favor fuera|Goles en contra fuera',
 'prof.identity': 'Identidad y caja',
 'prof.name': 'Nombre del manager',
 'prof.cash': 'Caja',
 'prof.date': 'Fecha (d / m / año)',
 'prof.level': 'Nivel (1–5)',
 'prof.mgmt': 'Gestión del equipo',
 'prof.internal': 'Valores internos',
 'prof.internal_items': 'Liga (0/1/2)|Promoción (byte 265)|Indicador de temporada (byte 320)',
 'prof.note': 'Al cambiar de club también se actualiza la liga (0/1/2).',
 'hist.palmares': 'Palmarés',
 'hist.seasons_played': 'Temporadas jugadas',
 'hist.titles': 'Títulos: {name}',
 'hist.round': 'Ronda actual: {name}',
 'hist.balance': 'Balance global',
 'hist.balance_items': 'Puntos|Goles a favor|Goles en contra|Victorias|Derrotas|Empates|Partidos '
                       'jugados|?432 (con signo)',
 'hist.seasons': 'Temporadas',
 'hist.add': '+ Añadir temporada',
 'hist.remove': '− Eliminar la última',
 'hist.season_cols': 'Posición|Liga|Copa nac.|Europa',
 'hist.note': 'Máx. 50 temporadas; la nueva fila copia la anterior. Posición: 1–18 primera liga, 19–38 '
              'segunda, 39–58 tercera; 255 = aún no era manager. En las copas, el bit 7 (+128) indica la '
              'victoria.',
 'stats.positions': 'Posición en la clasificación por jornada',
 'stats.attendance': 'Espectadores por partido (miles)',
 'stats.series': 'Rachas récord del manager (21 valores)',
 'stats.note': 'Las rachas estadísticas incluyen siete categorías para el total, casa y fuera. Los bytes '
               '267–304 y 330–346 almacenan el historial por jornada.',
 'squad.cols': 'Jugador|Posición|Rojas\n'
               'directas (+0)|Tarjetas\n'
               'amarillas (+1)|Expulsiones por\n'
               '2.ª amarilla (+2)|Goles de liga\n'
               '(+3)|Goles de copa\n'
               'nacional (+4)|Goles en\n'
               'Europa (+5)|Partidos de liga\n'
               '(+6)|Partidos de copa\n'
               'nacional (+7)|Partidos en\n'
               'Europa (+8)|Flags de estado\n'
               '(+9)|N.º camiseta\n'
               '(+10)|Contrato\n'
               '(temporadas)\n'
               '(+11)|Cesión\n'
               '(+12)|Sanción /\n'
               'lesión\n'
               '(+13)',
 'squad.all99': 'Todos a 99 (Cond./Tec./Forma)',
 'squad.count': '{n} jugadores en plantilla',
 'squad.note': 'Condición, técnica y forma son los valores actuales de la plantilla; la frescura va de 50 a '
               '150. El contrato se expresa en temporadas. El contador +13 indica partidos para una sanción '
               'y semanas para una lesión. Doble clic o Intro para editar; Tab pasa a la siguiente celda.',
 'pl.search': 'Buscar:',
 'pl.club': 'Club:',
 'pl.all': 'Todos',
 'pl.cols': 'Nombre del\n'
            'jugador|Edad\n'
            '(años)|Condición\n'
            '(actual)|Técnica\n'
            '(actual)|Forma\n'
            '(actual)|Código de\n'
            'posición\n'
            '(0–99)|Grupo de\n'
            'posición|Goles de\n'
            'liga|Partidos de\n'
            'liga|Club\n'
            'actual',
 'pl.count': '{n} jugadores',
 'std.facilities': 'Instalaciones',
 'std.ticket': 'Precio de la entrada',
 'std.lights': 'Iluminación',
 'std.screen': 'Videomarcador',
 'std.condition_stadium': 'Estado del estadio',
 'std.comfort': 'Comodidad',
 'std.attendance': 'Asistencia',
 'std.season_att': 'Asistencia de la temporada',
 'std.record_att': 'Récord de asistencia',
 'std.record_opp': 'Rival del récord',
 'std.min_att': 'Asistencia mínima',
 'std.min_opp': 'Rival de la asistencia mínima',
 'std.expansions': 'Ampliaciones del estadio',
 'std.exp_items': 'Asientos|Plazas de pie|Plazas cubiertas|Iluminación|Videomarcador|Estado|Comodidad',
 'std.above': '(arriba)',
 'std.exp_cols': 'Elemento|Actual|En construcción|Días restantes',
 'std.note': 'La iluminación, el videomarcador, el estado y la comodidad se configuran en el apartado '
             '«Instalaciones».',
 'loan.bank': 'Banco',
 'loan.lender': 'Prestamista {n}',
 'loan.cols': 'De|Importe|Intereses/mes|Tipo %|Inicio|Vencimiento',
 'loan.note': 'Un importe igual a cero indica un préstamo inactivo. Fechas en formato DD/MM/AAAA. Al crear '
              'un préstamo, establece también los intereses (importe × tasa / 100).',
 'sp.shirt': 'Camiseta',
 'sp.board': 'Valla publicitaria',
 'sp.tv': 'TV',
 'sp.adcost': 'Gastos de publicidad',
 'sp.income': 'Ingresos publicitarios',
 'sp.item': 'Concepto',
 'sp.amount': 'Importe',
 'sp.contracts': 'Contratos activos',
 'sp.contract_cols': 'Espacio|Meses restantes|N.º de patrocinador',
 'sp.offers': 'Ofertas de patrocinio',
 'sp.offer_cols': 'Patrocinador|Camiseta: años|Camiseta: importe|Vallas: años|Vallas: importe',
 'sp.note': 'Los ingresos se guardan en la tabla publicitaria del mánager. Los campos de contrato y oferta '
            'se almacenan en el registro correspondiente.',
 'st.resort': 'Reordenar',
 'st.cols': 'Club|Puntos\n'
            'totales|Diferencia\n'
            'de goles|Puntos\n'
            'en casa|Puntos\n'
            'fuera|Goles a favor\n'
            'en casa|Goles a favor\n'
            'fuera|Goles en contra\n'
            'en casa|Goles en contra\n'
            'fuera|Partidos jugados\n'
            'en casa|Partidos jugados\n'
            'fuera|Victorias\n'
            'en casa|Victorias\n'
            'fuera|Derrotas\n'
            'en casa|Derrotas\n'
            'fuera|Puntos\n'
            'históricos',
 'st.note': 'Los puntos totales son la suma de los puntos en casa y fuera; la diferencia de goles equivale a '
            'goles a favor menos goles en contra. Las demás columnas muestran por separado los datos de casa '
            'y fuera. El orden se establece por puntos totales y después por diferencia de goles; '
            '«Reordenar» lo actualiza.',
 'res.round': 'Jornada {n}',
 'res.match': 'Partido',
 'res.note': 'La partida guarda solo los goles, no los equipos de las jornadas anteriores. 255 = no jugado; '
             '30 goles en casa = partido aplazado.',
 'cal.season': 'Temporada actual',
 'cal.day': 'Día de la temporada',
 'cal.next': 'Próxima jornada (liga {n})',
 'cal.matches': 'Partidos de la jornada actual',
 'cal.note': 'Haz doble clic en un equipo para seleccionarlo de la lista.',
 'cup.relegation': 'Promoción de descenso',
 'cup.first_leg': 'Ida',
 'cup.outcome': 'Resultado (1 = asciende)',
 'cup.round': 'Ronda actual',
 'cup.legs_played': 'Ida jugada',
 'cup.qualified': 'Clasificados alemanes para Europa (lista)',
 'cup.slots': 'Plazas europeas (3 × 6, 128 = libre)',
 'cup.label': 'Copa:',
 'cup.goals_h': 'Goles C',
 'cup.goals_a': 'Goles F',
 'cup.first_leg_goals': 'Idas de las copas europeas (goles, 3 × 32)',
 'cup.note': 'Goles de las rondas: +10 después de la prórroga, +20 después de los penaltis.',
 'cl.search': 'Buscar club:',
 'cl.cols': 'Base|C1|C2|C3|T1|T2|T3|F1|F2|F3|Estado',
 'cl.count': '{n} clubes',
 'cl.note': 'C = condición, T = técnica, F = forma (tres valores cada una). Índices 0–17 primera liga, 18–37 '
            'segunda, 38–57 tercera; el resto son clubes extranjeros.',
 'ser.note': 'La tabla contiene 21 valores de las rachas actuales del club.',
 'rec.none': 'No hay clubes.',
 'rec.cols': 'Récord|Valor (a:b)|Rival',
 'rec.note': 'Récords de los clubes y sus respectivos rivales. Cada byte contiene dos valores de 0 a 15, '
             'escritos como a:b.',
 'vs.note': 'Los últimos 5 partidos del manager contra cada club, como goles en contra:goles a favor (máx. '
            '15 por celda). Celda vacía = ningún partido.',
 'msg.manager': 'Manager {n} – {name}',
 'msg.none': 'No hay mensajes.',
 'msg.note': 'El signo ^ indica un salto de línea. Puedes cambiar el texto de los mensajes existentes (máx. '
             '240 caracteres); añadir o eliminar mensajes requiere actualizar también los punteros internos '
             'y no está permitido.',
 'grp.advanced': 'Avanzado',
 'pg.market': 'Mercado',
 'pg.ext_standings': 'Clasificación ampliada',
 'pg.raw': 'Bloques sin procesar',
 'std.capacity': 'Capacidad total (calculada)',
 'loan.total': 'Deuda total',
 'loan.interest_total': 'Intereses mensuales totales',
 'squad.avg': 'Media de la plantilla – Cond. {c} · Tec. {t} · Forma {f}',
 'squad.extra_cols': 'Factor de\n'
                     'entrenamiento\n'
                     '(+14)|Índice del\n'
                     'jugador\n'
                     '(+15)|Condición\n'
                     '(+16)|Técnica\n'
                     '(+17)|Forma\n'
                     '(+18)|Frescura\n'
                     '(+19)|Programa de\n'
                     'entrenamiento\n'
                     '(+20)|Valoración\n'
                     'del partido\n'
                     '(+21, i8)|Club que\n'
                     'oferta\n'
                     '(+22)|Tipo de\n'
                     'lesión\n'
                     '(+23)|Negociación /\n'
                     'retirada\n'
                     '(+24)|Coordenada\n'
                     'horizontal X\n'
                     '(i8, +25)|Profundidad\n'
                     'vertical Y\n'
                     '(u8, +26)|Byte +27\n'
                     '(desconocido)|Partidos\n'
                     'liga\n'
                     '(+28, u16)|Partidos\n'
                     'copa\n'
                     '(+30, u16)|Partidos\n'
                     'Europa\n'
                     '(+32, u16)|Goles\n'
                     'liga\n'
                     '(+34, u16)|Goles\n'
                     'copa\n'
                     '(+36, u16)|Goles\n'
                     'Europa\n'
                     '(+38, u16)|Salario\n'
                     'mensual\n'
                     '(i32, +40–43)|Bytes +44–47\n'
                     '(desconocidos)|Puntero de\n'
                     'notificación\n'
                     '(i32, +48)',
 'pl.extra_cols': 'Media\ninicial\n(+27)|Preferencia\nlateral\n(+32)|Propietario /\nestado mercado\n(+33)',
 'squad.extra_note': 'Sueldo mensual: entero con signo de 32 bits en los bytes +40–43. Los bytes +44–47 no '
                     'tienen una función asignada.',
 'pl.note': '+27 = media inicial de condición, técnica y forma; no sigue los atributos actuales. +32 (0–6) = '
            'preferencia lateral utilizada por la formación automática para elegir la columna horizontal. '
            '+33: 0–3 mánagers, 4 mercado, 5 libre. Rol +31: 0–24 portero, 25–49 defensa, 50–74 '
            'centrocampista, 75–99 delantero.',
 'pl.owner_market': 'Mercado',
 'pl.owner_free': 'Libre',
 'mk.cols': 'Jugador|Posición|Ofertas\n'
            'rechazadas\n'
            '(+3)|Flags de\n'
            'estado (+9)|Cesión\n'
            '(+12)|Sanción /\n'
            'lesión\n'
            '(+13)|Factor de\n'
            'entrenamiento\n'
            '(+14)|Índice de\n'
            'jugador\n'
            '(+15)|Condición\n'
            '(+16)|Técnica\n'
            '(+17)|Forma\n'
            '(+18)|Frescura\n'
            '(+19)|Programa de\n'
            'entrenamiento\n'
            '(+20)|Valoración\n'
            'del partido\n'
            '(i8, +21)|Club oferente\n'
            '(+22)|Tipo de\n'
            'lesión\n'
            '(+23)|Negociación /\n'
            'carrera\n'
            '(+24)|Byte +27\n'
            '(sin mapear)|Valor de\n'
            'mercado\n'
            '(i32, +40)|Bytes +44–47\n'
            '(sin mapear)|Puntero de\n'
            'mensaje\n'
            '(i32, +48)',
 'mk.count': '{n} jugadores en la lista',
 'mk.note': 'El mercado utiliza las posiciones 100–111. +40–43 = valor económico (i32); +3 = ofertas '
            'rechazadas por mánager; +9 = indicadores de estado; +12 = préstamo; +13 = partidos de sanción o '
            'semanas de lesión; +22 = club oferente; +23 = tipo de lesión; +14 y +20 = entrenamiento; +21 = '
            'valoración del partido; +24 = estado del contrato/carrera; +27 y +44–47 = campos sin '
            'identificar; +48–51 = puntero de notificación.',
 'xs.cols': 'Serie A (b4–11)|Serie B (b13–20)|?2|?3|?24|?25|?28|?29|?40|?41|?44|?45|?46|b32–37',
 'xs.note': 'Registro completo de clasificación de 54 bytes por club. Las dos series hexadecimales contienen '
            'dos valores de 4 bits por byte.',
 'cal.perm': 'Orden del sorteo del calendario (20 valores por liga)',
 'cal.perm_note': 'Permutación de las posiciones de los equipos utilizada para crear el calendario (1.ª liga '
                  '0–19, 2.ª 20–39, 3.ª 40–59). Modificarla cambia el calendario de las próximas jornadas.',
 'raw.block5': 'Partidos aplazados: 20 registros de 5 bytes (5457–5556)',
 'raw.cols5': 'Identificador\n(+0)|Índice día\n(+1)|Jornada\n(+2)|Liga\n(+3)|Índice partido\n(+4)',
 'raw.tail1': 'Áreas de datos sin descifrar 34063–34221',
 'raw.tail2': 'Calendario y datos finales 34226–34366',
 'raw.note': 'Los offsets son posiciones absolutas en el búfer decodificado. El byte 34367 se muestra en la '
             'página Copas; los mensajes desde 34368 se gestionan en la página Mensajes.',
 'std.home_games': 'Partidos jugados en casa',
 'std.avg_att': 'Media de espectadores (calculada)',
 'prof.mgmt_items': 'Intensidad del partido (0–34)|Subvenciones juveniles (0–34)|Balones: condición|Balones: '
                    'juego|Balones: disparo|Balones: táctica|Moral (0–40)|Partidos con público|Intensidad '
                    'del entrenamiento|Entrenamiento de porteros|Entrenamiento de defensa|Entrenamiento de '
                    'centrocampistas|Entrenamiento de delanteros',
 'prof.portrait_id': 'Retrato (1–4)',
 'prof.extra': 'Otros campos',
 'prof.extra_item': 'Byte +{off}',
 'prof.extra_note': '+480 y +482 son valores de 16 bits independientes. +480 se recalcula durante el juego; '
                    '+482 no tiene una función asignada. Los demás campos no tienen una descripción '
                    'disponible.',
 'stats.chart': 'Historial de asistencia',
 'pg.options': 'Opciones de juego',
 'opt.panel': 'Opciones del juego (ACT/DES)',
 'opt.series': 'Liga 1|Liga 2|Liga 3',
 'opt.items': 'Resultados al descanso|Resultados finales|Clasificación',
 'opt.others': 'Acciones de partido|Copa nacional|Copas europeas|Partidos aplazados|Periódico|Fundidos',
 'opt.other': 'Otras opciones',
 'opt.speed': 'Velocidad del juego',
 'opt.speed_byte': 'Velocidad (0–70)',
 'opt.note': 'Las casillas activan o desactivan las opciones de visualización correspondientes.',
 'info.version': 'Versión',
 'info.unknown': 'desconocida',
 'info.edited': 'MODIFICADO CON EL EDITOR',
 'info.ingame': 'en el juego',
 'info.bmp_ita_mod': 'mod ITA sobre EXE alemán',
 'raw.recovery_note': 'Los 20 registros de cinco bytes describen partidos aplazados: identificador, índice '
                      'del día, jornada, liga y partido.',
 'raw.unknown_area': 'Datos adicionales y áreas sin identificar (34063–34221)',
 'raw.unknown_34063': '34063–34064 · 2 bytes sin descifrar',
 'raw.unknown_34065': '34065–34094 · 30 bytes sin descifrar',
 'raw.unknown_34095': '34095–34098 · 4 bytes sin descifrar',
 'raw.unknown_34215': '34215–34221 · 7 bytes sin descifrar',
 'raw.calendar_title': 'Índice y máscara del calendario de las ligas (34226–34321)',
 'raw.calendar_index': 'Índice actual (byte 34226)',
 'raw.calendar_index_note': 'El juego usa este byte como índice de un elemento de la tabla siguiente. No es '
                            'el número de jornada mostrado.',
 'raw.calendar_mask': 'Máscara de avance de las tres ligas · 95 bytes (34227–34321)',
 'raw.daily_words': 'Ocho valores de 16 bits que cambian durante el ciclo diario (34322–34337)',
 'raw.trailing_values': 'Otros valores del bloque final (34338–34366)',
 'raw.unknown_byte': 'Byte sin descifrar (34338)',
 'raw.offset': 'Offset',
 'raw.word_value': 'Valor de 16 bits',
 'raw.dword_value': 'Valor de 32 bits',
 'mark.name': 'TRAMPOSO',
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
 'tip.series_unverified': 'Valor de la secuencia estadística del mánager.',
 'tip.player_index': 'Índice del jugador vinculado en la tabla de 151 registros; guardado en el byte +15 del '
                     'espacio de plantilla.',
 'tip.unknown_bytes42': 'Bytes +42–43 de la posición de plantilla; función sin identificar.',
 'tip.player': 'Player name linked to this squad or transfer-market slot.',
 'tip.role_group': 'Role group derived from the player position code: goalkeeper, defender, midfielder or '
                   'forward.',
 'tip.shirt_number': 'Shirt number assigned to the player.',
 'tip.condition_current': 'Player current condition in the squad.',
 'tip.technique_current': 'Player current technique value.',
 'tip.form_current': 'Player current form.',
 'tip.freshness': 'Current freshness/fatigue value, stored separately from condition, technique and form.',
 'tip.monthly_wage': 'Salario mensual del jugador. Las rutinas operativas de creación y contrato leen y '
                     'escriben el campo completo de 32 bits +40–43; records.ts expone un acceso u16 limitado '
                     'a +40–41. El editor muestra el valor i32 completo.',
 'tip.contract_seasons': 'Contract duration expressed in seasons.',
 'tip.suspension_injury': 'Remaining suspension matches or injury weeks. The event type is indicated by the '
                          'status flags.',
 'tip.yellow_cards': 'Number of yellow cards recorded for the player.',
 'tip.direct_reds': 'Number of direct red cards recorded for the player.',
 'tip.league_goals': 'Goals scored by the player in the league.',
 'tip.league_appearances': 'Player appearances in the league.',
 'tip.training_factor': 'Individual factor modifying training effectiveness; 50 is the neutral factor.',
 'tip.training_program': 'Programa de entrenamiento codificado en bits: duración restante, intensidad y '
                         'dirección del cambio.',
 'tip.pitch_column': 'Coordenada horizontal X guardada en el byte +25 del puesto de plantilla. El juego la '
                     'interpreta como int8; las formaciones automáticas parten de las columnas 0–6 y pueden '
                     'intercambiarlas según la preferencia lateral del jugador.',
 'tip.pitch_line': 'Coordenada de profundidad Y guardada en el byte +26 (0–7): 0 hacia la portería rival, 7 '
                   'hacia la propia. Los titulares de una misma línea suelen compartir profundidad, con '
                   'pequeños desplazamientos según la formación.',
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
 'tip.unknown_byte27': 'Byte +27 del registro de plantilla; función sin identificar.',
 'tip.unknown_bytes44': 'Bytes +44–47 del registro de plantilla; función sin identificar.',
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
 'tip.preferred_side': 'Preferencia lateral del jugador (0–6), utilizada por la formación automática para '
                       'elegir o ajustar la columna horizontal.',
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
 'tip.club_status': 'Código de estado del club.',
 'tip.external_series_a': '8-byte hexadecimal block associated with Series A; each byte contains two 4-bit '
                          'values.',
 'tip.external_series_b': '8-byte hexadecimal block associated with Series B; each byte contains two 4-bit '
                          'values.',
 'tip.club_record_unknown': 'Byte +{offset} del registro de club de 54 bytes.',
 'tip.club_record_tail': 'Valores hexadecimales de los bytes +32–37 del registro del club.',
 'tip.raw_record_byte': 'Byte +{offset} of the raw 5-byte record shown in this table.',
 'tip.raw_block_values': 'Valores consecutivos del bloque de datos que comienza en el offset {start}.',
 'tip.series_column': 'Valor {number} de la secuencia estadística del club.',
 'tip.record': 'Name of the record held by the club.',
 'tip.record_value': 'Record value shown as a pair of numbers from 0 to 15 (a:b).',
 'tip.record_opponent': 'Opponent club associated with the record.',
 'tip.versus_home': 'One of the manager’s last 5 matches against this club, played at home. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'tip.versus_away': 'One of the manager’s last 5 matches against this club, played away. The score is '
                    'encoded as goals conceded:goals scored by the manager.',
 'squad.hint': 'Posiciones guardadas: +25 = X horizontal (i8); +26 = profundidad Y (0–7: 0 hacia la portería '
               'rival, 7 hacia la propia). Los dorsales 1–11 identifican a los titulares. El sistema del '
               'mánager está en el byte 51 + 2 × índice de mánager: 1 manual, 2 = 4-4-2, 3 = 3-5-2, 4 = '
               '3-4-3; el byte siguiente es la copia de respaldo. Doble clic o Intro para editar una celda; '
               'Tab pasa a la siguiente.',
 'pl.hint': 'All players in the savegame. Headings describe the player master-record fields and current '
            'values.',
 'mk.hint': 'The transfer market uses slots 100–111. Hover over a heading to read the extended field '
            'description.',
 'tip.european_first_leg_goals': 'Goals from the first-leg matches in European competitions, stored in the '
                                 'cup-results block.',
 'squad.formation_info': 'Sistema guardado: {active} · Respaldo: {backup}',
 'squad.system_manual': 'Manual',
 'squad.system_unknown': 'No reconocido ({value})',
 'opt.items_full': 'Resultados al descanso · Liga 1|Resultados finales · Liga 1|Clasificación · Liga '
                   '1|Resultados al descanso · Liga 2|Resultados finales · Liga 2|Clasificación · Liga '
                   '2|Resultados al descanso · Liga 3|Resultados finales · Liga 3|Clasificación · Liga '
                   '3|Escenas de gol|Copa nacional|Copas europeas|Partidos aplazados|Periódico|Fundidos',
 'opt.option_name': 'Opción',
 'opt.raw_byte': 'Estado',
 'tip.runtime_option': 'Interruptor de visualización del menú de opciones.',
 'tip.runtime_option_value': 'Estado del interruptor de visualización.',
 'opt.speed_value': 'Velocidad (0–70)',
 'opt.speed_note': 'Rango permitido: 0–70. Valor predeterminado: 40.',
 'tip.speed_runtime': 'Valor de 16 bits de la velocidad del juego (0–70).',
 'raw.game_type': 'Tipo y duración de la partida (34063–34064)',
 'raw.end_year_code': 'Código de tipo/duración (u16)',
 'raw.end_year_meaning': 'Interpretación',
 'raw.endyear_endless_historical': 'Partida infinita · inicio histórico',
 'raw.endyear_endless': 'Partida infinita · inicio normal',
 'raw.endyear_one_historical': 'Partida de 1 año · inicio histórico',
 'raw.endyear_one': 'Partida de 1 año · inicio normal',
 'raw.endyear_three_historical': 'Partida de 3 años · inicio histórico',
 'raw.endyear_three': 'Partida de 3 años · inicio normal',
 'raw.endyear_other': 'Valor no reconocido ({value})',
 'raw.rule_2026': 'Selector de reglas (34099)',
 'raw.rule_value': 'Reglamento',
 'raw.rules_original': 'Reglas 1993',
 'raw.rules_2026': 'Reglas 2026',
 'raw.poach_counts': 'Transferencias entre mánagers (34100–34115)',
 'raw.manager_number': 'Mánager {n}',
 'raw.poacher': 'Mánager que ficha',
 'raw.owner_manager': 'Propietario {n}',
 'raw.poach_note': 'Número de transferencias completadas para cada pareja de mánager comprador y mánager '
                   'propietario.',
 'raw.unknown_34116_label': 'Byte sin descifrar (+34116)',
 'raw.debt_mask': 'Máscara de bloqueo de compras (+34117)',
 'raw.derby_stakes': 'Apuesta del derbi por mánager (34118–34121)',
 'raw.derby_levels': '50.000 DM|100.000 DM|250.000 DM|500.000 DM',
 'raw.manager': 'Mánager',
 'raw.stake': 'Nivel de apuesta',
 'raw.youth_counts': 'Contadores de cantera (34122–34129)',
 'raw.promotions': 'Canteranos ascendidos al primer equipo',
 'raw.youth_poached': 'Canteranos recién ascendidos fichados por otro',
 'raw.youth_note': 'Valores por mánager: juveniles ascendidos al primer equipo y juveniles transferidos a '
                   'otro mánager. Los contadores se reinician al cambiar de temporada.',
 'raw.unknown_34130': '34130–34214 · 85 bytes sin descifrar',
 'raw.stadium_lockout': 'Días de bloqueo por tipo de ampliación del estadio (34215–34221)',
 'raw.speed_snapshot': 'Palabra de velocidad del juego (34222–34223)',
 'raw.speed_value': 'Velocidad (0–70)',
 'tip.raw_34063': 'Valor de 16 bits que identifica el tipo y la duración de la partida. Valores conocidos: '
                  '22222/22251 = ilimitada; 1964/1993 = un año; 1966/1995 = tres años. Las variantes '
                  'distinguen el inicio histórico del normal.',
 'tip.raw_34065': 'Área de 30 bytes (34065–34094) sin función asignada.',
 'tip.raw_34095': 'Cuatro bytes (34095–34098) anteriores al selector de reglas; función sin identificar.',
 'tip.rule_2026': '0 = reglas de 1993; 1 = reglas de 2026.',
 'tip.poach_count_row': 'Mánager comprador (fila). Las cuatro celdas indican el mánager propietario.',
 'tip.poach_count': 'Número de transferencias completadas para esta pareja comprador/propietario.',
 'tip.debt_mask': 'Máscara de bloqueo de compras por deuda: un bit por mánager. Umbral: saldo inferior a '
                  '−1.000.000 DM.',
 'tip.manager_index': 'Índice del mánager, de 0 a 3.',
 'tip.derby_stake': 'Nivel de apuesta del derbi: 0 = 50.000 DM, 1 = 100.000 DM, 2 = 250.000 DM, 3 = 500.000 '
                    'DM.',
 'tip.youth_promotions': 'Número de juveniles ascendidos al primer equipo esta temporada por este mánager.',
 'tip.youth_poach': 'Número de juveniles ascendidos que fueron transferidos a otro mánager durante la '
                    'temporada.',
 'tip.raw_34130': 'Área de 85 bytes (34130–34214) sin función asignada.',
 'tip.stadium_lockout': 'Siete contadores de días de bloqueo para tipos de ampliación del estadio. El código '
                        'original establece un bloqueo aleatorio de 15–55 días al rechazar una oferta de '
                        'ampliación. Se conoce la base 34215; la correspondencia exacta entre los siete '
                        'índices y los tipos debe tratarse con cautela.',
 'raw.training_camps': 'Disponibilidad de los 8 campos de entrenamiento (34322–34337)',
 'raw.camp_number': 'Campo',
 'raw.camp_status': 'Disponibilidad',
 'raw.camp_counter': 'Contador restante (i16)',
 'raw.camp_open_days': 'Abierto · {days} días',
 'raw.camp_closed_days': 'Cerrado · {days} días',
 'raw.camp_changeover': 'Cambio de estado',
 'raw.camp_note': 'Ocho valores con signo de 16 bits, uno por campo de entrenamiento. Negativo = abierto; '
                  'positivo = cerrado. El contador avanza un día hacia cero; al llegar a cero se reinicia '
                  'con el signo opuesto y una duración de 20–70 días.',
 'tip.camp_number': 'Índice del campo de entrenamiento (1–8).',
 'tip.camp_status': 'Negativo = abierto; positivo = cerrado; cero = cambio de estado. El valor absoluto '
                    'indica los días restantes.',
 'tip.camp_counter': 'Valor con signo de 16 bits en el offset 34322 + 2 × índice. Disminuye un día hasta '
                     'cero y luego se reinicia con el signo opuesto y una duración de 20–70 días.',
 'tip.daily_word': 'Contador con signo de 16 bits para la disponibilidad de un campo de entrenamiento.',
 'tip.recovery_marker': 'Byte +0: identificador del registro del partido aplazado.',
 'tip.recovery_day_index': 'Byte +1: índice del día del calendario asociado al aplazamiento.',
 'tip.recovery_matchday': 'Byte +2: jornada original de la liga.',
 'tip.recovery_league': 'Byte +3: índice de la liga (0, 1 o 2).',
 'tip.recovery_fixture': 'Byte +4: índice del partido dentro de la jornada.',
 'tip.raw_34215': 'Siete contadores de días de bloqueo de ampliaciones del estadio.',
 'tip.calendar_mask': 'Tabla binaria de 95 bytes. El índice +34226 selecciona el byte actual; sus bits '
                      'indican qué ligas avanzan a la siguiente jornada.',
 'raw.additional_fields': 'Otros campos adicionales (34116–34129)'}
