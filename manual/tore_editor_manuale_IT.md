# TORE Editor – Feature list e manuale d'uso

Editor visuale per le **scene dei gol** (file `.T`, `.V`, `.TE`, `.TJ`, `.VE`, `.VJ`, formato `BM-Ed1.x-WK`) di Bundesliga Manager. Una scena è un breve "film" di fotogrammi (frame) in cui 22 giocatori, arbitro, pallone e porte si muovono sul campo, con una finestra camera che scorre e fino a 4 effetti sonori.

---

# PARTE 1 – Feature list

**File e formato**
- Apri, crea, salva e salva con nome scene (`.T/.V` + varianti `E` rigore, `J` scherzo); compatibile con le firme `BM-Ed1.0-WK` e `BM-Ed1.3-WK`.
- "Save as numbered scene": salva come `N.ext` e aggiorna automaticamente il file `ANZAHL` (con backup `.bak`).
- Proprietà scena: autore (ERBAUER), versione file, esito (gol / occasione mancata), tipo (rigore / scherzo / nessuno).
- Elimina il file della scena dal disco.

**Visualizzazione**
- Campo 320×112 con grafica originale letta dai `.VGA` (26 campo, 27 sprite, 29 porte); segnaposto colorati se mancano.
- Zoom campo (1–6×) e zoom area (fino a 12×) con scrollbar, rotella e pan col tasto centrale.
- Riquadro camera (182×96), ID degli sprite, percorsi del selezionato o di tutti, "fantasmi" dei frame precedenti (4 modalità).
- Finestra Sprite sheet ridimensionabile per assegnare le pose con un clic.

**Modifica di sprite e frame**
- Selezione singola, multipla (Ctrl+clic, rettangolo, Ctrl+A) con "capogruppo"; ciclo tra sprite sovrapposti.
- Trascinamento, frecce (1 px, Shift = 5 px), pallone + ombra sempre uniti, altezza del pallone regolabile.
- Ambito di modifica: solo questo frame oppure questo + successivi.
- Aggiungi/elimina frame (max 256), elimina intero film, Undo/Redo (100 livelli).
- Specchia la scena (lato campo + colori squadra) o scambia solo i colori.

**Percorsi (movimento)**
- Percorso a mano libera (D) o a punti cliccati (P), con velocità fissa, durata fissa o tempo reale del disegno.
- "Perspective run": velocità coerente con la prospettiva del campo.
- Curve morbide, linea retta con Shift, percorso rapido dal menu tasto destro (a N frame, o arrivando a un frame preciso).
- Modifica del percorso "a corda": trascini un punto e i frame vicini lo seguono.
- Lisciatura, velocità uniforme, "Freeze", interpolazione tra due frame, spostamento dell'intero percorso.

**Animazione automatica degli sprite**
- Sprite di corsa scelti in automatico dalla direzione (8 direzioni, entrambi i colori, rotazione del pallone).
- Posa "ferma" automatica quando lo sprite si arresta.
- Azioni speciali (tuffo, colpo di testa, rovesciata, caduta, rialzarsi, esultanza, moonwalk, … configurabili) con ripresa automatica della corsa.
- Corsa manuale in una direzione fino a fine film, "stand", sequenze di pose programmate, specchio posa, blocco posa.

**Camera**
- Scroll manuale (trascinando il bordo ciano o con i campi X/Y), anche durante la riproduzione.
- Camera che segue uno sprite o il pallone (da qui o su tutto il film), con movimento ammorbidito.
- Interpolazione dello scroll e prolungamento fino a fine film.

**Timeline, riproduzione, suoni**
- Timeline con colori per corsa / fermo / azione speciale dello sprite selezionato.
- Riproduzione "tutto" o "da qui", loop, fps regolabili, intervallo di riproduzione con due marcatori.
- 4 eventi sonori (esultanza, fischio arbitro, disapprovazione, delusione) posizionabili su qualsiasi frame.

**Esportazione e dati**
- Esporta GIF animata (camera o campo intero, scala, fps, preset di qualità, palette condivisa, dithering, ecc.) con stima della dimensione.
- Dati configurabili in JSON: set di pose, azioni, animazioni di corsa/fermo, formazione di calcio d'inizio, tramite editor grafico integrato.

---

# PARTE 2 – Manuale

## 1. Concetti di base

### 1.1 Struttura di una scena
- Una scena ha da **1 a 256 frame**.
- Ogni frame contiene **27 sprite**: 11 rossi, 11 blu, 1 arbitro, l'ombra del pallone, il pallone, la porta sinistra e la porta destra. **Gli sprite non si possono né aggiungere né eliminare**, solo spostare e cambiare di posa.
- Le porte non sono selezionabili: seguono la x del pallone e vengono riallineate automaticamente al salvataggio.
- L'ordine di sovrapposizione (chi sta davanti) è automatico, in base alla posizione verticale.

### 1.2 Coordinate e limiti
| Elemento | Valore |
|---|---|
| Campo | 320 × 112 px |
| Finestra camera | 182 × 96 px |
| Scroll camera | X 0–137, Y 0–15 |
| Sprite giocatore | 12 × 11 px |
| Pallone / ombra | 4 px di larghezza |
| Frame massimi | 256 |
| Annulla | 100 livelli |

Le coordinate mostrate nella barra di stato sono `x` e `y(sprite)`; la y è misurata dall'alto del campo giocabile (offset 35 px già sottratto).

### 1.3 Numerazione degli sprite (ID)
| ID | Contenuto |
|---|---|
| 0–58 | Giocatori rossi (0–33 guardano a Est, 34–58 a Ovest) |
| 59–117 | Giocatori blu (= ID rosso + 59) |
| 118–141 | Arbitro (118–128 a Est, 129–141 a Ovest) |
| 142–144 | Pallone (fasi di rotazione) |
| 145 | Ombra del pallone |

Spuntando **View ▸ Show sprite ids** (o "Sprite IDs") vedi l'ID sopra ogni sprite.

### 1.4 Colori nell'interfaccia
- **Giallo**: sprite selezionato (capogruppo). **Ciano tratteggiato**: altri sprite del gruppo.
- **Ciano pieno**: riquadro camera; fuori dalla camera il campo è scurito.
- **Percorso**: puntini colorati per squadra (palla gialla, arbitro grigio, rossi, blu), personalizzabili in *Path / Camera ▸ Paths color*.

## 2. Avvio e file necessari

### 2.1 Cartella PIC (grafica)
L'editor cerca la cartella `PIC` (con `26.VGA`, `27.VGA`, `29.VGA`) vicino alla scena aperta o all'eseguibile. Se non la trova, usa segnaposto (rettangoli colorati) e lo segnala nella barra di stato. Puoi sceglierla manualmente con **File ▸ PIC folder…**. Se manca solo un file, la barra indica quale.

### 2.2 File dati JSON (cartella `data`, accanto allo script/eseguibile)
- `tore_actions.json` – azioni, animazioni di corsa e di pausa.
- `tore_pose_sets.json` – categorie di pose per rossi/blu, arbitro e pallone.
- `tore_kickoff.json` – formazione di calcio d'inizio usata da *New scene*.

Vengono letti all'avvio. Se un file è mancante o non valido compare un avviso e le funzioni relative risultano non disponibili (senza azioni e pose non si possono usare corsa automatica e azioni; senza kickoff non si può creare una nuova scena). Dopo modifiche a mano usa **Data ▸ Reload data files**.

## 3. L'interfaccia

Dall'alto verso il basso:
1. **Menu**: File, Edit, Sprite, Path / Camera, View, Data, ?.
2. **Barra strumenti**: Select move (V), Path (D / P), Camera (H), Sprite sheet, Undo, Redo.
3. **Riquadro Options**: cambia in base allo strumento attivo.
4. **Riga "Changes apply to"**: ambito, altezza pallone, fantasmi, interruttori di visualizzazione.
5. **Campo** (con scrollbar dello zoom area), barra di riproduzione, **timeline** e barra di stato.
6. **Pannello destro**: elenco sprite (x, y, pose) e schede **Poses**, **Actions**, **Sound**.

### 3.1 Ambito delle modifiche ("Changes apply to")
- **this frame**: la modifica vale solo per il frame corrente.
- **this + following frames**: vale dal frame corrente fino alla fine. Influenza spostamenti, cambio posa, scroll e altezza del pallone.

Molte funzioni di percorso, azioni e corsa agiscono comunque "dal frame corrente in avanti" (lo dice il nome del comando).

## 4. File

| Comando | Scorciatoia | Descrizione |
|---|---|---|
| New scene | Ctrl+N | Scena di 1 frame con tutti i 27 sprite in formazione di calcio d'inizio (da `tore_kickoff.json`). |
| Open… | Ctrl+O | Apre `.t .v .te .tj .ve .vj`. Verifica la firma e che il file non sia troncato. |
| Save | Ctrl+S | Salva usando l'estensione definita dalle proprietà (vedi sotto). |
| Save As… | Ctrl+Shift+S | Salva con nome. |
| Save as numbered scene… | – | Salva come `N.estensione` nella cartella della scena e aggiorna `ANZAHL`. |
| Export animated GIF… | – | Vedi §13. |
| PIC folder… | – | Sceglie la cartella grafica. |
| Delete file… | – | **Cancella definitivamente** dal disco il file della scena aperta. |
| Exit | – | Chiede conferma se ci sono modifiche non salvate. |

**Estensione:** è determinata da *Edit ▸ Scene properties*: `T` = gol, `V` = occasione mancata, con suffisso `E` (rigore) o `J` (scherzo). Se cambi tipo e salvi, il file viene salvato con la nuova estensione (con richiesta di conferma se esiste già).

**Save as numbered scene:** scegli tipo, variante e numero. Il numero proposto è l'ultimo noto in `ANZAHL` + 1. Se il numero supera il massimo registrato per quella variante, `ANZAHL` (riga `MAXSZENE:a|b|c`) viene aggiornato e viene creata una copia `ANZAHL.bak` (solo la prima volta). Se `ANZAHL` non viene trovato, la scena viene salvata ma il file non viene toccato.

Il titolo della finestra mostra nome file, asterisco `*` se ci sono modifiche e il numero del frame corrente.

## 5. Edit

| Comando | Scorciatoia | Descrizione |
|---|---|---|
| Undo / Redo | Ctrl+Z / Ctrl+Y | Annulla/ripristina (frame, suoni, autore). Non annulla le modifiche ai file dati. |
| Select all players | Ctrl+A | Seleziona tutti i giocatori (non arbitro/pallone). |
| Insert frame (copy) | Ins | Duplica il frame corrente subito dopo; i suoni successivi si spostano. |
| Delete current frame | Del | Elimina il frame (ne serve almeno uno). |
| Delete entire film… | – | Elimina tutti i frame tranne quello corrente. |
| Mirror scene | – | Specchia posizioni e pose da sinistra a destra **e** scambia i colori delle squadre; scambia le porte; riflette la camera. |
| Swap team colors only | – | Rossi ↔ blu senza specchiare il campo. |
| Scene properties… | – | Autore, versione file (`BM-Ed1.3-WK` / `1.0`), esito (T/V) e tipo (E/J/nessuno). |

## 6. Strumenti e mouse

Cambia strumento dalla barra o con i tasti **V**, **D**, **P**, **H**. Ogni strumento mostra solo le proprie opzioni.

### 6.1 Select move (V)
- **Clic** su uno sprite: lo seleziona. **Ctrl+clic**: aggiunge/toglie dal gruppo.
- **Trascina uno sprite**: lo sposta (con tutto il gruppo selezionato). Pallone e ombra si muovono sempre insieme.
- **Trascina nel vuoto**: selezione a rettangolo (con Ctrl aggiunge alla selezione).
- **Clic nel vuoto**: deseleziona.
- **Sprite sovrapposti**: ripeti il clic nello stesso punto per scorrerli in ciclo, oppure tasto destro ▸ *Select under cursor*.
- **Capogruppo (leader)**: in un gruppo, clicca uno sprite già selezionato (o tasto destro ▸ *Make leader*) per renderlo capogruppo. Per default è lo sprite più in alto. Il capogruppo determina quale ID/percorso viene mostrato e quale pose-set compare nel pannello.
- **Trascina un puntino del percorso** (giallo/colorato): modifica il percorso "a corda" (§7.4).
- **Trascina il bordo ciano** del riquadro camera: sposta lo scroll.
- **Frecce**: spostano di 1 px lo sprite selezionato (**Shift** = 5 px); il canvas deve avere il focus.

Opzioni dello strumento: *Rope softness* (quanti frame vicini vengono trascinati), *Pin selected sprite*, *Move whole path with sprite*.

### 6.2 Path (D / P)
Vedi §7.

### 6.3 Camera (H)
Trascina il campo per spostare lo scroll (funziona anche durante la riproduzione). Il clic su uno sprite lo seleziona. Opzioni: campi Scroll X/Y, *Camera follows selected sprite*, *whole film*.

### 6.4 Altri comandi del mouse
- **Rotella**: cambia frame. **Ctrl+rotella**: zoom area nel punto del cursore.
- **Tasto centrale + trascinamento**: sposta l'area ingrandita (Windows/Linux).
- **Tasto destro**: menu contestuale (§6.5).
- **Doppio clic** (strumento P): termina il percorso.

### 6.5 Menu contestuale (tasto destro sul campo)
- **Su uno sprite**: elenco sprite sotto il cursore, leader/rimuovi dal gruppo, *Action here*, *Run*, mirror/lock pose, auto-sprite, smooth, even speed, freeze, "Camera follows this sprite/ball".
- **Su un punto del percorso**: vai al frame, smooth, even speed, "Straighten: interpolate to frame N…".
- **Su un punto libero** (con uno sprite selezionato): percorso dritto fino qui, *Path to here in N frames…*, *Path to here, arriving at frame…*, *Move here* (teletrasporto entro l'ambito attivo), passa a Draw/Click path.
- Nello strumento P, con un percorso in corso, il tasto destro lo conclude.

## 7. Percorsi: far muovere gli sprite

Un **percorso** converte un movimento nel campo in una sequenza di posizioni, una per frame, a partire dal frame corrente. I frame mancanti vengono creati automaticamente (fino al limite di 256). Il movimento si applica a tutto il gruppo selezionato (e a pallone + ombra insieme), mantenendo gli scarti relativi.

### 7.1 Opzioni comuni (strumento Path)
| Opzione | Effetto |
|---|---|
| **speed** (px/frame) | Il numero di frame deriva dalla lunghezza del percorso. |
| **duration** (frames) | Il percorso occupa esattamente N frame. |
| **Realtime drawing** (solo Draw) | Il tempo reale con cui disegni diventa il ritmo del movimento (usa gli fps correnti). |
| **Perspective run** (solo Click) | Compensa la prospettiva: lo sprite impiega lo stesso tempo a percorrere il lato lontano (corto) e quello vicino (lungo). Qui la *speed* è riferita alla linea y=39. |
| **smooth curves** | Arrotonda gli angoli (Chaikin per Draw, Catmull-Rom per Click). |
| **auto run sprites** | Imposta automaticamente le pose di corsa/fermo lungo il percorso. |
| **diagonal sprites** | Usa le 8 direzioni; se disattivo solo 4 (N/S/E/W). |
| **later frames follow** | Dopo il termine del percorso, i frame successivi già esistenti vengono traslati dello stesso scarto, per conservare la continuità. |

La velocità consigliata di default è 3 px/frame (8 per il pallone).

### 7.2 Disegnare un percorso (D – Draw)
1. Premi **D**.
2. Seleziona lo sprite (o premi direttamente su di esso).
3. Tieni premuto il mouse e disegna; rilascia per "cuocere" il percorso nei frame successivi.
4. **Shift** mentre disegni = linea retta. **Esc** = annulla.

### 7.3 Percorso a punti (P – Click)
1. Premi **P** e seleziona lo sprite.
2. Clicca i punti di passaggio. **Backspace** toglie l'ultimo punto, **Esc** annulla.
3. Termina con **Invio**, doppio clic o tasto destro.

### 7.4 Modificare un percorso "a corda"
Con lo strumento Select, trascina qualunque puntino del percorso: i frame vicini vengono tirati con una curva gaussiana. *Rope softness* regola quanti frame coinvolge; **Shift** sposta solo quel punto. *Pin selected sprite* tiene fermo il frame corrente, mentre *Move whole path with sprite* fa sì che trascinare lo sprite sposti l'intero percorso. A fine trascinamento le pose vengono ricalcolate (se *auto run sprites* è attivo) e la camera si riallinea.

### 7.5 Comandi del menu *Path / Camera*
| Comando | Descrizione |
|---|---|
| Smooth path (from this frame) | Media mobile del tratto in movimento. |
| Even speed (from this frame) | Ridistribuisce i punti a velocità costante. |
| Freeze here (stop sprite) | Ferma lo sprite da qui alla fine. |
| Interpolate position to frame… | Interpolazione lineare fino a un frame finale a scelta. |
| Paths color | Cambia i colori dei percorsi (palla, arbitro, rossi, blu) o li ripristina. |

## 8. Pose, corsa e azioni

### 8.1 Scheda Poses
Scegli una **categoria** nel menu a tendina e clicca una miniatura per assegnare la posa. Vale per tutto il gruppo (le pose vengono convertite automaticamente tra rosso e blu). L'ambito segue *Changes apply to*. I tasti **[** e **]** passano alla posa precedente/successiva della categoria. Le categorie vengono da `tore_pose_sets.json`.

### 8.2 Sprite sheet
Il pulsante **Sprite sheet** apre una finestra ridimensionabile con tutta la tavola degli sprite; un clic assegna quello sprite (per ID) al selezionato.

### 8.3 Scheda Actions
Applica un'azione a partire dal frame corrente al giocatore selezionato (o a tutto il gruppo). Il colore squadra è automatico. Ogni azione ha direzione **E** o **W** (frecce `E >` / `< W`); alcune sono "senza direzione" (*Go*). Per il *moonwalk* la direzione indica il verso di marcia, mentre lo sprite guarda dall'altra parte.

L'opzione **then resume running automatically** fa riprendere la corsa/posa ferma subito dopo l'azione, in base al movimento dei frame successivi. Se i frame non bastano, vengono aggiunti.

Le azioni disponibili sono quelle definite in `tore_actions.json` (di serie: tuffo, colpo di testa, rovesciata, caduta per scontro, rialzarsi, esultanza, moonwalk).

### 8.4 Direzioni di corsa (rosa dei venti nella scheda Actions)
Ogni pulsante (NW, N, NE, W, E, SW, S, SE) applica il ciclo di corsa in quella direzione dal frame corrente a fine film. **stand** mette la posa "fermo" rivolta nell'ultima direzione di movimento. Per l'arbitro e il pallone valgono i rispettivi cicli.

### 8.5 Menu *Sprite*
| Comando | Descrizione |
|---|---|
| Action here | Come la scheda Actions (sottomenu). |
| Run (sprites only, to end of film) | Ciclo di corsa in una direzione. |
| Auto-sprites along path (from this frame / whole film) | Ricalcola le pose dal movimento effettivo, **preservando le pose speciali** (azioni). |
| Mirror pose (E ↔ W) | Specchia la posa del selezionato. |
| Lock pose (clear animation from here) | Mantiene fissa la posa corrente fino alla fine. |
| Program pose sequence… | Chiede una lista di ID separati da virgola, ripetuta ciclicamente dal frame corrente alla fine. |

### 8.6 Pallone e ombra
Pallone e ombra sono sempre mossi insieme. **Ball height (px)** regola la distanza verticale pallone–ombra (positivo = pallone in alto); vale nell'ambito attivo. Le rotazioni del pallone in corsa seguono il ciclo definito nei dati.

## 9. Camera

La camera è la finestra 182×96 che il gioco mostra durante la scena.

- **Manuale**: campi *Scroll X/Y* (nello strumento Camera), oppure trascina il bordo ciano / il campo con lo strumento H, anche mentre scorre la riproduzione.
- **Camera follows selected sprite** (checkbox, o menu *Path / Camera*, o tasto destro ▸ *Camera follows this sprite*): genera keyframe di scroll che inseguono lo sprite con movimento ammorbidito (max 6 px/frame in X, 2 in Y). Con **whole film** attivo parte dal frame 1, altrimenti dal frame corrente.
- Una **nuova scena** parte già con la camera che segue il pallone.
- Quando modifichi percorsi o posizioni la camera "inseguitrice" si ricalcola da sola; se sposti manualmente lo scroll, l'inseguimento si disattiva.
- **Interpolate scroll to frame…**: interpolazione lineare dello scroll fino a un frame.
- **Continue current scroll to end of film**: copia lo scroll attuale sui frame successivi.

## 10. Timeline, riproduzione e suoni

### 10.1 Barra di riproduzione
`|<` primo frame · `<` indietro · **Play all** (dall'inizio dell'intervallo) · **Play from here** (barra spaziatrice) · `>` avanti · `>|` ultimo · **+ Frame** / **– Frame** · **Loop** · **fps** (1–60).

### 10.2 Timeline
- Clic o trascinamento sulla fascia superiore: va al frame.
- Fascia colorata sotto i numeri (per lo sprite selezionato): **verde** = corsa, **grigio** = fermo, **arancione** = posa speciale.
- **Marcatori di intervallo** (frecce in basso, rosso = inizio, viola = fine): trascinali per definire l'intervallo di Play e della GIF "play range". Il tasto destro offre *Set loop start/end here* e *Reset loop range*.
- **Triangoli colorati**: eventi sonori.
- Tasto destro: menu con riproduzione, intervallo, inserisci/elimina frame e suono.

### 10.3 Suoni
Scheda **Sound**: scegli *none* o uno dei quattro suoni e verrà assegnato al frame corrente. Ogni suono può stare su un solo frame; assegnarlo altrove lo sposta.

| Suono | Colore |
|---|---|
| Goal celebration | verde |
| Referee whistle | giallo |
| Disapproval whistles | arancione |
| Missed-goal disappointment | blu |

## 11. View

| Voce | Effetto |
|---|---|
| Show path / Show all paths | Percorso dello sprite selezionato / di tutti (tranne pallone). |
| Show camera view | Riquadro camera e oscuramento dell'esterno. |
| Show sprite ids | ID sopra ogni sprite. |
| Field size +/– (Ctrl +/–) | Ingrandimento del campo 1–6×. |
| Zoom area in/out/reset | Ingrandisce una porzione del campo (fino a 12×). Si può anche usare il campo *Zoom area*, il tasto **1:1**, le scrollbar. |

**Ghosts** (menu a tendina): *None*, *Selected: previous frame*, *Selected: all previous frames*, *All sprites: all previous frames* – mostra trasparenze dei frame precedenti per giudicare la fluidità.

## 12. Data

| Comando | Descrizione |
|---|---|
| Edit pose sets, actions & path animation… | Editor grafico dei dati (§12.1). |
| Reload data files | Rilegge i JSON dopo modifiche manuali. |
| Save current frame as kick-off formation | Salva sprite, posizioni e scroll del frame corrente in `tore_kickoff.json`, usato da *New scene*. Richiede esattamente 11 rossi, 11 blu, arbitro, ombra, pallone e 2 porte. |

### 12.1 Editor dei dati
Tre schede; le modifiche restano in memoria finché non premi **Save to files** (che scrive i JSON e applica subito i cambiamenti). Alla chiusura con modifiche pendenti viene chiesto se salvare.

**Pose sets** – Categorie di pose per gruppo *red* (ID 0–58, blu = +59 automatico), *referee* (118–141) o *ball* (142–145). Seleziona un set a sinistra, modifica *Name* e *IDs* (accetta `3,4,5`, `15-20`, `43-38` discendente). La striscia di sprite è sincronizzata col campo IDs: clic su uno sprite = scegli da tavola, **+** = aggiungi, tasto destro = rimuovi. Pulsanti *Add new*, *Delete*, *Up*, *Down*.

**Actions** – Elenco azioni (chiave minuscola/cifre/underscore, etichetta, sequenza **E** e sequenza **W**). Se W è vuota viene calcolata come specchio di E (`k → 58−k`). Si possono ripetere ID per mantenere una posa più frame. Opzioni: *No direction (single entry)* e *E/W is the direction of travel*.

**Path animation** – Per ciascuna direzione (e gruppo red / referee / ball) si definisce la posa **IDLE** (riquadro a sinistra, prima del ciclo) e il resto del ciclo di corsa. Per il pallone c'è il ciclo di *Rotation*. Le pose da fermo non si definiscono nelle Actions ma qui.

## 13. Esporta GIF animata (File ▸ Export animated GIF…)

| Sezione | Opzioni |
|---|---|
| **Content** | Frame: intero film / intervallo di play / da qui in poi. Area: finestra camera (segue lo scroll) o intero campo. |
| **Size and speed** | Scala 1–8×, scalatura morbida, fps 1–50, mantenimento ultimo frame (ms), loop infinito. |
| **Quality** | Preset (*Smallest file*, *Small*, *Balanced*, *High quality*, *Maximum quality*, *Custom*), numero colori 2–256, ogni N-esimo frame, palette condivisa, dithering, ottimizzazione. |

*Calculate size* stima peso, dimensioni e durata senza salvare; *Export…* chiede il percorso del file. L'operazione ha una barra di avanzamento e può essere annullata. Con palette condivisa e senza dithering si ottengono i file più piccoli. Le impostazioni vengono ricordate finché l'editor resta aperto.

## 14. Scorciatoie da tastiera

| Tasto | Azione |
|---|---|
| **V / D / P / H** | Select / Draw / Click path / Camera |
| **Spazio** | Play da qui / stop |
| **Frecce** | Sposta 1 px (Shift = 5 px) |
| **PgUp / PgDn**, **, / .**, rotella | Frame precedente / successivo |
| **Home / End** | Primo / ultimo frame |
| **[ / ]** | Posa precedente / successiva |
| **Ins / Del** | Inserisci / elimina frame |
| **Invio / Backspace / Esc** | Termina percorso / toglie punto / annulla o deseleziona |
| **Ctrl+Z / Ctrl+Y** | Annulla / ripristina |
| **Ctrl+A** | Seleziona tutti i giocatori |
| **Ctrl+N / O / S / Shift+S** | Nuova / apri / salva / salva con nome |
| **Ctrl + / Ctrl –** | Zoom campo |
| **Ctrl+rotella** | Zoom area |

I tasti di strumento e lo spazio vengono ignorati mentre scrivi in un campo di testo.

## 15. Flussi di lavoro consigliati

**Creare una scena da zero**
1. *File ▸ New scene*. Il frame 1 mostra la formazione di calcio d'inizio.
2. Imposta *Scene properties* (esito, tipo, autore).
3. Seleziona un giocatore, premi **D** o **P** e traccia il movimento: i frame vengono creati e le pose di corsa assegnate da sole.
4. Ripeti per gli altri sprite; per il pallone seleziona pallone o ombra.
5. Aggiungi azioni (tiro, tuffo, esultanza) dalla scheda *Actions* nel frame giusto.
6. Controlla con *Ghosts* e *Play all*; correggi i percorsi a corda e usa *Smooth* / *Even speed*.
7. Imposta la camera (*Camera follows…*) e assegna i suoni sui frame desiderati.
8. *Save as numbered scene…*

**Riutilizzare una scena per l'altra squadra**: apri, *Edit ▸ Mirror scene*, salva con altro numero.

**Anteprima da condividere**: *Export animated GIF…* con preset *Balanced*, area *camera window*.

## 16. Note e risoluzione problemi

- **"Graphics not found"** → usa *File ▸ PIC folder…* e scegli la cartella con `26.VGA`, `27.VGA`, `29.VGA`.
- **Avviso "Data files" all'avvio** → controlla che la cartella `data` accanto all'eseguibile contenga i tre JSON validi. Con una build PyInstaller `--onefile` il percorso va ricavato da `sys.executable`, non da `__file__`.
- **New scene non funziona** → `tore_kickoff.json` mancante o incompleto: usa *Save current frame as kick-off formation* su un frame valido.
- **Il percorso si ferma prima** → hai raggiunto 256 frame o il bordo del campo (gli sprite vengono limitati al campo).
- **Le frecce non muovono lo sprite** → clicca prima sul campo per dargli il focus.
- **ANZAHL non aggiornato** → il file deve essere nella cartella della scena o in quella superiore; il numero deve superare il massimo già registrato.
- **Pose che non cambiano** → verifica che lo sprite selezionato non sia una porta e che l'ambito (*frame* / *this + following*) sia quello voluto.
- Le categorie di pose contrassegnate **(?)** nei dati sono ancora da verificare.
- La modifica ai dati (JSON) **non** è annullabile con Undo.

## Appendice – Formato del file scena (riassunto)
- 12 byte di firma: `BM-Ed1.0-WK\0` o `BM-Ed1.3-WK\0`.
- 4 byte: frame degli eventi sonori (255 = nessuno).
- 1 byte: numero di frame − 1.
- Per ogni frame, 164 byte: scroll (X basso, Y alto) + 27 record da 3 word (x, y, ID sprite) nell'ordine di disegno.
- In coda: byte di lunghezza + nome autore in codepage 437, terminato da `\0`.
- Le porte hanno ID speciali (1000 sinistra, oltre 1000 destra) e x uguale a quella del pallone.
