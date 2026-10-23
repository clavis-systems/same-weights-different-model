# Premessa — "Stessi pesi, modello diverso" (passo 0a: censimento dei metadati)

Scritta il 20/10/2026 prima di raccogliere i dati del censimento. Prova di funzionamento solo su 3 repository
(`openai-community/gpt2`, `Qwen/Qwen2.5-0.5B-Instruct`, `HuggingFaceTB/SmolLM2-1.7B-Instruct`), dichiarati qui.

## Domanda

Nei modelli di testo più scaricati su Hugging Face, quante volte, dopo il rilascio, cambiano i file che decidono il
comportamento (template di chat, parametri di generazione, token speciali) **mentre i pesi restano identici**? Chi
valuta lo "stesso modello" in date diverse può star misurando due modelli diversi.

## Popolazione

I primi 200 modelli `pipeline_tag=text-generation` ordinati per download, dall'API pubblica, al momento della corsa
(elenco e download salvati nel risultato). Nessun token: i repository riservati (gated) che rifiutano i metadati
vengono contati come "non accessibili", non esclusi in silenzio.

## Definizioni

- **File primari** (comportamento): `tokenizer_config.json`, `chat_template.jinja`, `chat_template.json`,
  `generation_config.json`, `special_tokens_map.json`.
- **File secondari**: `config.json`, `tokenizer.json` (cambiano anche per altri motivi; riportati a parte).
- **Pesi**: file nella cartella principale che finiscono in `.safetensors`, `.bin`, `.gguf`, `.pt`, `.pth`;
  impronta = oid git (per LFS l'oid del contenuto).
- **Rilascio**: primo commit in cui esiste almeno un file di pesi. Se non ne esistono mai: primo commit con un file
  primario (rilascio "approssimato", segnato).
- **Cambio post-rilascio**: commit successivo al rilascio in cui cambia (o compare, o sparisce) l'impronta di
  almeno un file primario o secondario.
- **"Stessi pesi"**: nel commit del cambio l'impronta dei pesi è identica a quella del commit precedente.

## Procedura

Storia dei commit del ramo `main` (API `commits`), elenco dei file per commit (API `tree`, solo cartella principale,
con impronte). I punti di cambio si trovano per bisezione: se due commit hanno la stessa impronta si assume che in
mezzo non sia cambiato nulla.

## Misure (descrittive, decise ora)

1. M1: quota di modelli con almeno un cambio post-rilascio di un file primario a pesi identici.
   M1b: lo stesso contando solo i cambi avvenuti più di 7 giorni dopo il rilascio (aggiunta dopo la prova sui 3
   repository dichiarati, prima della corsa: lì comparivano ritocchi del giorno stesso del rilascio). Il passo 0a non
   distingue i cambi che toccano il comportamento da quelli innocui (es. `model_max_length`): lo farà il passo 0b.
2. M2: lo stesso per singolo file primario.
3. M3: giorni fra rilascio e cambio (mediana, quartili).
4. M4: le stesse misure sul sottoinsieme delle organizzazioni grandi (google, meta-llama, Qwen, mistralai,
   microsoft, nvidia, deepseek-ai, openai, HuggingFaceTB, allenai, ibm-granite).

## Previsione (mia, prima dei dati)

M1 ≥ 25%. Il file più cambiato sarà `tokenizer_config.json`, poi `generation_config.json`.

## Aggiunta 20/10, 15:05 — passo 0c (scritta dopo i risultati di 0a e 0b, prima di 0c; commit d0d76a8 15:07)

Risultati già visti: 0a M1 54%; 0b: 248 cambi di file su 294 toccano chiavi di comportamento; modelli con almeno un
cambio di comportamento a pesi identici 94/189 (49,7%), grandi organizzazioni 63/89 (70,8%).

**Domanda 0c:** quanti cambi del template di chat cambiano davvero il testo che il modello riceve nell'uso normale?
Per ogni cambio con `chat_template` fra le chiavi cambiate (o file `chat_template.*`), si renderizzano template di
prima e di dopo con la funzione di `transformers` (5.5.4, sandbox Jinja ufficiale) su conversazioni fisse:
C1 un messaggio utente; C2 sistema + utente; C3 tre turni; C4 come C2 più la risposta, senza prompt di generazione;
C5 un messaggio utente con uno strumento dichiarato. Stessi token speciali `<s>`/`</s>` da entrambe le parti, così le
differenze vengono solo dal template. Classi: *uso normale* (cambia almeno una fra C1–C4), *solo con strumenti*
(cambia solo C5), *nessun cambio visibile*, *errore di rendering*, *non confrontabile* (manca la versione di prima nel
file scaricato). Misura: quota di cambi e di modelli nella classe *uso normale*, anche oltre 7 giorni dal rilascio.

## Aggiunta 20/10, 15:15 — passo 1: effetto sui punteggi (scritta prima di ogni generazione)

Verifica di novità indipendente (20/10): REFINE. Il vicino più stretto, "Silent Updates" (Sarvesh S R, 1/10/2026),
studia solo classificatori, trova 0 cambi di predizione per i cambi solo di config/tokenizer, esclude la generazione
di testo ("Generative models deserve separate study").

**Casi (scelti prima, tre casi di studio):**
- A `Qwen/Qwen2.5-0.5B-Instruct`, cambio di `tokenizer_config.json` del 18/9/2024 (+2 g): il messaggio di sistema
  predefinito diventa "You are Qwen, created by Alibaba Cloud. You are a helpful assistant."
- B `Qwen/Qwen2.5-1.5B-Instruct`, lo stesso cambio del 18/9/2024.
- C `deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B`, cambio di `tokenizer_config.json` del 9/2/2025 (+20 g): la risposta
  parte con `<think>\n`.
- Pesi: file locali; si verifica che lo sha256 sia uguale all'oid LFS del commit di prima e di dopo (API dei
  metadati). Se non è uguale, il caso si esclude e si dichiara.

**Dati e generazione:** GSM8K test (1.319 problemi, `openai/gsm8k`, MIT), risposta d'oro dopo `####`. Un solo
messaggio utente: domanda + "Please reason step by step, and put your final answer within \boxed{}.", nessun
messaggio di sistema (valgono i predefiniti del template). Template di prima/dopo resi con la funzione di
transformers; stesso tokenizer e stessa `generation_config` locale in tutte le condizioni (si isola il template).
Decodifica deterministica (greedy), bf16, gruppi da 32 con riempimento a sinistra; massimo 1.024 token nuovi per A e B,
2.048 per C. Punteggio: ultimo `\boxed{}`, altrimenti ultimo numero; uguaglianza numerica.

**Controllo del rumore:** per ogni modello una terza corsa con il template di prima e l'ordine dei problemi
rimescolato (seme 1), quindi gruppi diversi. Misura quante risposte cambiano solo per la numerica bf16.

**Ipotesi (per modello):** H1 accuratezza dopo ≠ prima, McNemar esatto bilaterale sulle coppie discordanti, Holm
sui 3 modelli, α 0,05. Il risultato vale come effetto del template solo se il controllo NON è significativo con lo
stesso test; se il controllo è significativo, il caso è "non interpretabile".
**Previsione mia:** A e B nessun effetto significativo (|Δ| < 2 punti: l'identità nel sistema non c'entra con la
matematica); C dopo > prima, significativo (il `<think>` forzato evita di saltare il ragionamento).
Descrittive: lunghezza media, risposte troncate, risposte senza `\boxed{}`, in C quante volte il ragionamento è vuoto.

**Regola di tempo (decisa ora, solo sui tempi):** se dopo i primi 64 problemi la stima per le tre corse di C supera
4 ore, C usa i primi 660 problemi in tutte e tre le sue corse.

## Deviazione 1 (20/10, 17:54, commit fda4dea) — caso C a gruppi da 16

Scritta prima di guardare qualsiasi accuratezza del caso C. Fatti: (1) la prima corsa di C (gruppi da 32) si è
fermata dopo circa 12 minuti con un errore CUDA "device-side assertion", senza scrivere risultati; (2) una
riproduzione su 32 problemi con `CUDA_LAUNCH_BLOCKING=1` è finita senza errori ma in 57 minuti (circa 107 s a
problema). Causa probabile: con 32 risposte lunghe fino a 2.048 token il picco di memoria (pesi 3,5 GB + cache
dinamica copiata mentre cresce) supera gli 8 GB della scheda e Windows sposta memoria nella RAM di sistema.
**Cambio:** il caso C usa gruppi da 16 in tutte e tre le sue corse (prima, dopo, controllo); A resta a 32, B a 32.
Il confronto dentro C resta appaiato e alla stessa dimensione dei gruppi. Le uscite di prova (2 + 32 problemi, in una
cartella a parte) sono scartate; di queste sono state lette solo 2 risposte, per controllo del formato. La regola di
tempo si applica come scritto, con la stima sui primi 64 problemi a gruppi da 16. Il caso A era già finito (16:41)
e la sua analisi è stata fatta prima di questa deviazione.

## Deviazione 1b (20/10, 18:07, commit 518a9a6) — caso C con cache statica

Scritta prima di guardare qualsiasi accuratezza del caso C. Anche a gruppi da 16 la memoria saliva (3,9 → 7,2 GB in
2,5 minuti) per la cache che cresce e si frammenta: la corsa è stata fermata prima che finisse un gruppo (nessuna
riga scritta). **Cambio:** il caso C usa la cache KV statica (`cache_implementation="static"`, compilazione spenta
perché Triton manca su Windows) e libera la memoria dopo ogni gruppo, in tutte e tre le sue corse. Prova su 32
problemi in una cartella a parte: memoria ferma a 4,75 GB, 416 s; di quella prova sono stati guardati solo memoria e
tempi, non le risposte; le uscite sono scartate. La stima per tre corse complete supera di molto 4 ore, quindi per
la regola di tempo C userà i primi 660 problemi; le tre corse possono richiedere due sessioni (il PC si spegne la
sera): la ripresa riparte dal primo problema mancante, con lo stesso codice.

## Deviazione 1c (20/10, 21:25) — ripartenza automatica dopo errori CUDA intermittenti

Scritta prima di guardare qualsiasi accuratezza del caso C. Con la cache statica la condizione "prima" è finita (660
problemi), mentre "dopo" si è fermata a 272 e "controllo" a 64, entrambe con un errore CUDA "device-side assertion";
memoria stabile (4,9 GB), nessun evento del driver NVIDIA in quei minuti (l'unico, alle 17:58, coincide con l'arresto
della corsa che sconfinava). I due gruppi falliti non hanno problemi in comune. Il gruppo fallito di "dopo" (problemi
272-287) è stato rieseguito con `CUDA_LAUNCH_BLOCKING=1` ed è finito senza errori (16 righe aggiunte al file; l'opzione
cambia solo la sincronizzazione, non i calcoli). **Cambio di esecuzione:** ogni condizione viene rilanciata
automaticamente (al massimo 10 volte) finché tutti i problemi sono scritti; la ripresa salta i problemi già scritti e il
gruppo interrotto si rifà da capo. I registri completi degli errori sono conservati. Dato descrittivo già visto (non
un'accuratezza): in "prima" 175 risposte su 660 arrivano al limite di 2.048 token.

## Deviazione 1d (21/10, 15:52, commit 2a3ba31) — ripresa dopo lo spegnimento e ripartenza automatica anche per B

Scritta prima di eseguire qualsiasi corsa del caso B e prima di guardare accuratezze di C. Il PC è stato spento il
20/10 dopo le 23:00: C "controllo" si è fermato a 336 problemi su 660 (il resto riparte dal primo mancante, stesso
codice, stessa macchina). La ripartenza automatica della deviazione 1c (al massimo 10 volte, il gruppo interrotto si
rifà da capo) si applica anche alle tre corse di B, che per il resto restano come da premessa (gruppi da 32, cache
dinamica, 1.319 problemi, massimo 1.024 token). Se la memoria della GPU superasse 7,5 GB durante B, la corsa si ferma e
si dichiara una deviazione prima di continuare.

## Deviazione 1e (21/10, 21:34) — caso B rifatto da capo con cache statica

Scritta prima di guardare qualsiasi accuratezza del caso B; decisione di Emanuele del 21/10 sera ("va bene la tua
opzione raccomandata"). Fatti: B "prima" è finito alle 18:35 con la cache dinamica (1.319 problemi); B "dopo" si è
fermato alle 18:38 con 0 righe perché la memoria della GPU ha superato 7,5 GB mentre un programma di un altro progetto
(Blender) usava la scheda, come previsto dalla deviazione 1d; ripartito alle 19:27 a GPU libera, è stato interrotto
alle 19:44 a 864 righe su 1.319. Con la cache dinamica la memoria oscillava fra 3,6 e 5,1 GB
(`effetto/memoria_21-10.log`). **Cambio:** tutte e tre le corse di B (prima, dopo, controllo) si rifanno da zero con la
cache KV statica (`--cache-statica`, come C) e gruppi da 32, così il confronto appaiato usa la stessa impostazione in
tutte e tre le condizioni e la memoria resta fissa. I file `B_prima.jsonl` (1.319 righe) e `B_dopo.jsonl` (864 righe)
e i loro registri sono spostati in `effetto/scartati_1e/` senza leggerne le risposte né calcolarne l'accuratezza.
Restano come prima: 1.319 problemi, massimo 1.024 token, ripartenza automatica (1c), guardia a 7,5 GB (1d). Durante B
nessun altro programma usa la GPU. Esecuzione: `catena_B_1e.sh` in questa cartella.

## Correzioni dopo il ricalcolo indipendente (21/10, scritte prima di guardare l'effetto di B e di C)

Un revisore indipendente (sessione Claude separata, codice proprio, numeri scritti prima di leggere il nostro codice;
rapporto `strumenti/esperimenti_ricalcolo/RICALCOLO_STESSI_PESI.md`, ramo `claude/beautiful-varahamihira-b35730`,
commit `f7df2eb`) conferma 0a e i modelli di 0b, e trova difetti di definizione. Si adottano come **cifre principali**
quelle corrette qui sotto (le originali restano nel registro come prima versione). Sono correzioni dopo i dati,
dichiarate come tali; un secondo controllo (Codex) verifica le correzioni prima della pubblicazione.

1. **Raccolta senza bisezione:** storia commit per commit per tutti i 189 modelli. M1 = 103/189 (54,5%), M1b = 67
   (35,4%), grandi 70/89 e 45/89; 266 cambi di file primari a pesi identici (la bisezione ne aveva persi 21).
2. **"Stessi pesi" nella versione forte:** i file di pesi del rilascio tutti presenti e invariati: **98/189 (51,9%)**,
   oltre 7 giorni 63 (33,3%), grandi 68/89; con mappa dei pesi identica al rilascio 86/189 (45,5%).
3. **Ritardo per modello oltre che per cambio:** primo cambio di ogni modello, mediana 0,75 giorni (quartili
   0,31/0,75/7,13); per cambio mediana 4,4 giorni. Metodo dei quartili dichiarato.
4. **0c con regole corrette** (unità = commit; errore di rendering solo se nessuna conversazione normale è
   confrontabile; template con nome per gli strumenti; precedenza di `chat_template.jinja`; `chat_template.json` = formato
   dei processor): 126 cambi = 44 uso normale / 32 solo con strumenti / 33 nessun cambio visibile / 9 senza effetto
   (oscurati) / 8 non confrontabili; **35 modelli con un cambio d'uso normale, 11 oltre 7 giorni** (indizio: sotto i
   30–40 casi).
5. **Cambio reale** (template d'uso normale corretto, oppure *modifica* del token di fine o di un parametro di
   campionamento nello stesso file prima e dopo; creazioni e cancellazioni di file non contano): **58/189 = 30,7%,
   grandi 43/89 = 48,3%**. Limite superiore se si contano anche le creazioni non verificabili: 68/189 (36,0%), 44/89.
6. **Composizione dichiarata:** 51/189 sono `Qwen/*` (senza Qwen M1 = 40,6%, M1b = 26,1%); quantizzati 21/74 (28,4%)
   contro non quantizzati 81/115 (70,4%); 5 fixture di test; 10 non accessibili tutti di grandi organizzazioni; un
   modello escluso perché senza pesi né file primari (`unsloth/GLM-5.3-GGUF`).

## Limiti dichiarati

- I ritorni A→B→A dentro un tratto con estremi uguali sfuggono alla bisezione: M1 è un limite inferiore.
- Solo la cartella principale e solo `main`.
- Il passo 0a dice *quando* cambia un file, non *cosa* cambia né quanto pesa sui punteggi. Il passo 0b (scaricare
  le versioni prima e dopo dei soli file cambiati, pochi KB ciascuno) richiede l'OK esplicito dell'utente con
  l'elenco dei file e la dimensione totale.
