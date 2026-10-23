# Ricalcolo indipendente del passo 1 ("stessi pesi, modello diverso")

Revisore indipendente, 22/10/2026. Ho rifatto l'analisi da zero con codice mio (`ricalcolo.py`, solo libreria standard,
`python -X utf8 ricalcolo.py`, percorsi relativi al file) partendo solo dalle regole della PREMESSA (passo 1 + deviazioni
1, 1b, 1c, 1d, 1e) e dalle risposte grezze `{A,B,C}_{prima,dopo,controllo}.jsonl`. I miei numeri sono stati salvati in
`miei_numeri.json` **prima** di aprire `analisi.json` ed `effetto.py` (stesso file ricalcolato dopo: stesso hash). Quello che
ho calcolato dopo il confronto sta a parte, in `miei_numeri_aggiunte.json`. Non ho modificato nessun file esistente e non ho
fatto commit.

## Verdetto: CONFERMATO CON RISERVE

- **Il calcolo e' confermato.** Tutti i numeri descrittivi coincidono (troncate, senza `\boxed{}`, token medi), i
  confronti di controllo sono identici, il caso C e' identico (accuratezze, b, c, p; cambia solo il Holm, riportato da A),
  B ha lo stesso p di McNemar (0,0709) e lo stesso Holm (0,2128). I verdetti sono gli stessi: A, B, C = "nessun effetto dimostrato", controlli non significativi.
- Le uniche differenze sono 8 risposte su 9.894 (0,08%), tutte in scatole `\boxed{}` che non contengono un numero puro
  (5 problemi). Spostano le accuratezze di un problema al massimo e il p di A da 0,4507 a 0,4918. Nessun verdetto cambia.
- Le **riserve** riguardano l'interpretazione, non l'aritmetica: (1) il contrasto di C e' nullo per costruzione e rumoroso;
  (2) la potenza e' bassa, quindi "nessun effetto dimostrato" non vuol dire "nessun effetto"; (3) in C la
  classificazione dipende da come si trattano le risposte troncate.

## Tabella: miei numeri contro ufficiali

Regola mia = quella della PREMESSA ("ultimo `\boxed{}`, altrimenti ultimo numero") con le mie scelte di dettaglio (sotto).
Ufficiale = `analisi.json`. In "diff." il segno e' dopo meno prima, in punti percentuali.

| | A (n 1.319) mio | A uff. | B (n 1.319) mio | B uff. | C (n 660) mio | C uff. |
|---|---|---|---|---|---|---|
| prima corrette | 618 (46,85%) | 618 (0,4685) | 937 (71,04%) | **938** (0,7111) | 495 (75,00%) | 495 (0,75) |
| dopo corrette | 605 (45,87%) | **606** (0,4594) | 963 (73,01%) | **964** (0,7309) | 488 (73,94%) | 488 (0,7394) |
| controllo corrette | 619 (46,93%) | 619 (0,4693) | 943 (71,49%) | **944** (0,7157) | 481 (72,88%) | 481 (0,7288) |
| prima giusta/dopo sbagliata (b) | 133 | **134** | 83 | 83 | 55 | 55 |
| prima sbagliata/dopo giusta (c) | 120 | **122** | 109 | 109 | 48 | 48 |
| diff. dopo-prima, IC95 (Wald) | -0,99 [-3,35; +1,38] | (non c'e') | +1,97 [-0,09; +4,03] | (non c'e') | -1,06 [-4,07; +1,95] | (non c'e') |
| p McNemar dopo/prima | 0,4507 | **0,4918** | 0,0709 | 0,0709 | 0,5546 | 0,5546 |
| p Holm | 0,9013 | **0,9837** | 0,2128 | 0,2128 | 0,9013 | **0,9837** |
| controllo b / c | 63 / 64 | 63 / 64 | 34 / 40 | 34 / 40 | 60 / 46 | 60 / 46 |
| diff. controllo-prima, IC95 | +0,08 [-1,60; +1,75] | | +0,45 [-0,82; +1,73] | | -2,12 [-5,17; +0,93] | |
| p McNemar controllo/prima | 1,0000 | 1,0000 | 0,5614 | 0,5614 | 0,2065 | 0,2065 |
| controllo significativo? | no | no | no | no | no | no |
| verdetto | nessun effetto dimostrato | uguale | nessun effetto dimostrato | uguale | nessun effetto dimostrato | uguale |

(In grassetto le celle diverse.) Il p Holm di C differisce solo perche' Holm riporta in avanti il p corretto di A
(passo successivo): stessi p grezzi, stesso verdetto.

Descrittive, tutte uguali alle ufficiali: troncate A 7/7/7, B 2/1/3, C 175/178/185 (prima/dopo/controllo); senza
`\boxed{}` A 22/55/19, B 2/8/3, C 161/165/175; token medi A 316,0/315,8/313,8, B 312,6/308,8/312,4, C 1326,2/1326,5/1346,1;
ragionamento vuoto 0 ovunque (questo l'ho ricalcolato dopo il confronto, con la stessa definizione della premessa).
Controlli di base: l'`oro` coincide con la colonna `answer` di GSM8K nel parquet locale in tutte le 9 condizioni (0 righe
diverse); le righe del controllo (ordine rimescolato) corrispondono ai problemi giusti (circa 98% delle risposte riporta
i numeri della domanda, come nelle altre condizioni).

## Ogni differenza e la sua causa

Letto `effetto.py` dopo il confronto. La sua `estrai()` prende il **primo** numero dentro la scatola (dopo aver tolto
virgole, `$`, `%`); io prendo l'**ultimo** e calcolo le frazioni. Differiscono solo le scatole non numeriche pure. Una
regola alternativa che replica la loro (`primo_numero_scatola`, in `miei_numeri_aggiunte.json`) riproduce esattamente le
loro cifre: A 618/606/619, b 134, c 122, p 0,4918, Holm 0,9837; B 938/964/944, p 0,0709.

| Problema (i) | Scatola | Oro | Chi sbaglia | Dove |
|---|---|---|---|---|
| 1033 | `\frac{2}{3}` | 2 | **ufficiale** (conta il numeratore 2: falso positivo) | A prima, A controllo |
| 1169 | `\frac{2}{5}R` | 2 | **ufficiale** (numeratore: falso positivo) | A dopo |
| 726 | `\frac{10}{9}` | 10 | **ufficiale** (numeratore: falso positivo) | B dopo |
| 906 | `4 \text{ blue}, 6 \text{ red}, 10` | 10 | ambiguo: io prendo l'ultimo (il totale, 10) e conto giusta; loro il primo (4) e contano sbagliata | A prima, A controllo |
| 1001 | `2:00 \text{ PM}` | 2 | **io** (ultimo numero = "00"); loro prendono 2 e hanno ragione | B prima, B controllo |

Effetto netto: A dopo +1 (loro), B ognuna +1 (loro), A prima e controllo si compensano. Con la mia regola corretta per gli
orari (`principale_orari`) B diventa 938/963/944, b 84, c 109, p 0,0838 (Holm 0,2514): sempre "nessun effetto dimostrato".
Nota per chi mantiene `effetto.py` (non l'ho toccato): conviene trattare le frazioni a parte; non cambia nessun verdetto.

## Riserve di metodo

**1. Quanto dipende dall'estrazione.** Ho provato cinque regole (p dopo/prima | p controllo/prima):

| Regola | A | B | C |
|---|---|---|---|
| principale | 0,451 \| 1,000 | 0,071 \| 0,561 | 0,555 \| 0,207 |
| scatola solo se numero puro | 0,490 \| 1,000 | 0,071 \| 0,561 | 0,555 \| 0,207 |
| scatola, se non numerica ripiega sul testo | 0,451 \| 1,000 | 0,071 \| 0,561 | 0,555 \| 0,207 |
| solo scatola (senza scatola = sbagliata) | 0,258 \| 1,000 | 0,097 \| 0,561 | 0,562 \| **0,039** |
| ignora la scatola, ultimo numero del testo | 0,487 \| 0,929 | 0,261 \| 0,734 | 0,555 \| 0,566 |

Sulle risposte singole: tra "principale" e "scatola pura" cambia 0-1 risposte per file; ripiegare sul testo non cambia
nulla; "solo scatola" cambia 0-8 risposte in A e B ma **25, 25 e 33 in C**; ignorare la scatola ne cambia 25-26 in A,
31-40 in B, 13-22 in C. I verdetti restano uguali in tutte le regole **tranne una**: con "solo scatola" il controllo di C
diventa significativo (p 0,039; prima 470, controllo 448) e C passerebbe a "non interpretabile". La regola ufficiale
(ripiego sull'ultimo numero) e' quella della premessa, quindi il verdetto di C resta, ma e' fragile.

**2. Il caso C: 175-185 troncate su 660 cambia la lettura.**
- Il 26,5-28,0% delle risposte arriva al limite di 2.048 token, senza `\boxed{}`. Sono punteggiate con l'ultimo numero del
  testo di un ragionamento interrotto: 25, 25 e 33 risposte "giuste" (3,8-5,0 punti di accuratezza) vengono solo da li'.
- Sui 383 problemi mai troncati in nessuna condizione l'accuratezza e' 96,6/96,3/96,6% e le coppie discordanti sono 7
  (p 1,0). Delle 103 coppie discordanti prima/dopo, 96 hanno almeno una risposta troncata (99 su 106 nel controllo).
  Quindi C misura soprattutto "il ragionamento finisce entro 2.048 token?", che cambia da una corsa all'altra
  (troncate solo in prima 60, solo in dopo 63, p 0,86).
- **Il contrasto di C e' nullo per costruzione.** In prima e controllo 660/660 risposte iniziano da sole con
  `<think>\nOkay`; in dopo il template mette `<think>\n` nel prompt e 660/660 risposte iniziano con `Okay`. Il modello
  riceve gli stessi token: la differenza e' solo numerica (lunghezza del prompt, riempimento). Lo conferma il rumore: le
  uscite identiche sono 14/660 prima-dopo contro 50/660 prima-controllo (anche a template uguale quasi nessuna uscita si
  ripete), e il prefisso comune mediano e' 533 caratteri sia prima-dopo sia prima-controllo (in A e' 125 contro 530, in B
  105 contro 632). Le coppie discordanti sono 103 (dopo) contro 106 (controllo). La previsione "C dopo > prima,
  significativo" e' quindi fallita non per sfortuna ma perche' il modello non saltava il pensiero in questo compito
  (ragionamento vuoto: 0 su 660 in tutte e tre le condizioni). "Nessun effetto dimostrato" in C e' vero ma poco informativo.
- Il controllo di C non e' pulito: -2,12 punti, IC [-5,17; +0,93], piu' grande dell'effetto -1,06. Con questa potenza
  "controllo non significativo" non dimostra che il rumore sia piccolo.

**3. Il caso B (+1,97 punti, p 0,0709).** Va detto "nessun effetto dimostrato", non "nessun effetto": IC95 [-0,09;
+4,03], Holm 0,21, e con la regola "ignora la scatola" p 0,26. Il dato e' compatibile con zero e con +4 punti. La previsione
"|Δ| < 2" regge solo di un soffio sulla stima puntuale (1,97) e non e' supportata dall'intervallo. Il segno e'
opposto a quello di A (-0,99): niente da leggere in questa differenza.

**4. Potenza (a posteriori, condizionata alle coppie discordanti osservate; McNemar esatto).**

| Caso | coppie discordanti dopo/prima | differenza minima significativa (alfa 0,05 / alfa 0,0167) | potenza a 1 / 2 / 3 punti (alfa 0,05) | potenza a 2 punti con alfa 0,0167 |
|---|---|---|---|---|
| A | 253 | 2,5 / 3,1 punti | 12% / 36% / 69% | 19% |
| B | 192 | 2,3 / 2,7 punti | 13% / 43% / 78% | 27% |
| C | 103 | 3,2 / 4,1 punti | 10% / 25% / 49% | 10% |

Con il solo rumore di fondo (discordanti del controllo: A 127, B 74, C 106) le soglie scendono a 1,9 / 1,4 / 3,3 punti.
Conclusione: l'esperimento vede effetti di circa 3 punti o piu' (4 in C); differenze di 1-2 punti passano inosservate nella
maggior parte dei casi. "Nessun effetto dimostrato" e' il massimo che il disegno permette.

**5. Nessun effetto netto non e' nessun cambiamento.** In A e B il template cambia le uscite quasi sempre (identiche
prima/dopo: 53/1.319 e 19/1.319, contro 452 e 535 nel controllo) e raddoppia o triplica i problemi che cambiano esito
(A 253 contro 127, B 192 contro 74) ma con segno simmetrico. Osservazione esplorativa, non nella premessa: in A le risposte
senza `\boxed{}` salgono da 22 a 55 (controllo 19), McNemar esatto p 0,000013 (12 solo in prima, 45 solo in dopo); in B da 2
a 8 (p 0,11). La metrica ufficiale lo attutisce con il ripiego sull'ultimo numero (8 delle 55 risposte comunque giuste).

**6. Cio' che i dati grezzi non permettono di verificare.** Che la cache (dinamica per A, statica per B e C),
la dimensione dei gruppi, il seme del rimescolamento, i template resi e i pesi (sha256) siano quelli dichiarati nelle
deviazioni; le tre condizioni di C sono state generate in sessioni diverse con ripartenze. Mi fido della premessa su questi
punti. Il test e' sulle 1.319 (660) istanze di GSM8K test come popolazione fissa: l'intervallo di Wald e' approssimato.

## File

Cartella `strumenti/risultati/stessi_pesi/effetto/controllo_ricalcolo/`:
- `ricalcolo.py`: il mio codice (nessuna dipendenza esterna).
- `miei_numeri.json`: numeri scritti prima del confronto (principale, 4 regole alternative, descrittive, troncate, potenza).
- `miei_numeri_aggiunte.json`: calcoli fatti dopo il confronto (regola che replica `effetto.py`, orari, ragionamento vuoto, inizio risposte di C).
- `ricalcolo_stdout.txt`: uscita a video dell'ultima esecuzione.
