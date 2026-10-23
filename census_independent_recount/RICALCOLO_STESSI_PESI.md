# Ricalcolo indipendente — "Stessi pesi, modello diverso"

Revisore: sessione Claude indipendente, 20/10/2026 (dalle 19:30 circa). Solo CPU, solo metadati pubblici di Hugging Face,
nessuna spesa. Codice mio, in questa cartella. I miei numeri 0a/0b/0c/4 sono stati scritti e committati (`5161a28`,
file `numeri_miei_prima_del_confronto.md`) **prima** di aprire `codice/`, `riassunto.json`, `classificazione_0b.json`,
`rendering_0c.json` e `verifica_pesi.json` dell'altra sessione. Quello che ho letto prima: `PREMESSA.md`, `README.md`,
`istantanea.json`, `modelli.jsonl`, `piano_0b.json`, i file in `file0b/` (solo come testo/JSON, con `python -I`),
le prime 80 righe di `COORDINAMENTO.md`.

> **Aggiornamento 21/10:** su richiesta del secondo controllo (Codex) ho riapplicato la regola di 0c alla lettera
> (punto 8 in fondo). **Nessun cambio passa di classe e nessuna cifra cambia.**

## 0. Esito in una tabella

| # | Numero dichiarato | Il mio ricalcolo | Esito |
|---|---|---|---|
| 1 | 0a: 189 analizzati, M1 102 (54%), M1b 67 (35,4%), per file 81/26/2/50/28, mediana 5,1 g (0,7/5,1/36,0), grandi 70/89 (78,7%), oltre 7 g 45/89 | identici in ogni cifra, e stesso elenco di 102 modelli | **coincide** (vedi i caveat di definizione al punto 1) |
| 2 | 0b: 294 cambi di file; 248 di comportamento, 46 innocui; modelli 94/189 (49,7%), grandi 63/89 (70,8%) | 294 identici uno a uno; **240** di comportamento + 52 innocui + 2 illeggibili (def. stretta), 253/39/2 (def. larga); modelli **94** (stessi 94) e **63** | **coincide** sui modelli; **differisce di 8** sui file, per definizione (punto 2) |
| 3 | 0c: 134 cambi; 39 uso normale, 30 solo strumenti, 34 nessun cambio, 8 errori, 23 non confrontabili; 33 modelli (9 oltre 7 g) | con le *loro* regole il mio codice riproduce **tutte** le cifre (34/39/30/8/23; 33; 9). Con regole corrette: 126 cambi (modello, commit): 44 uso normale / 32 solo strumenti / 33 nessun cambio / 0 errori / 8 non confrontabili / 9 senza effetto (oscurati); **35 modelli, 11 oltre 7 g** | **coincide** con le loro regole; **differisce** con regole corrette (punto 3: +2 modelli, 4 difetti) |
| 4 | Cambio reale 75/189 = 39,7%, grandi 52/89 = 58,4% | con il loro metodo: 75/189 e 52/89 esatti. Con la mia definizione (token di fine = solo *modifiche*): **58/189 = 30,7%**, grandi **43/89 = 48,3%** | **coincide** come calcolo; **differisce** come significato: 18 modelli entrano solo per creazione/cancellazione di file (punto 4) |
| 5 | Controllo della raccolta, 20 modelli a caso (seme 20261020) | storia commit per commit rifatta dall'API: stesso numero di commit 20/20, stesso rilascio 20/20, **55 cambi elencati = 55 trovati**, 0 mancanti, 0 in più, 0 disaccordi su file/pesi/data | **coincide** |
| 5+ | (in più, non richiesto) stessa verifica su **tutti i 189** | nessun cambio inventato (418/418 esistono, pesi come dichiarato), ma **34 cambi persi dalla bisezione** (14 modelli) e **2 rilasci sbagliati**: M1 = **103** (non 102), M1b = 67 uguale; con la condizione "pesi come al rilascio" M1 = **98 (51,9%)** | **differisce di poco**; difetto del codice (punto 5) |

**In una frase:** i numeri 0a e 0b coincidono; quelli di 0c e della misura 4 si riproducono ma dipendono da regole che
in 0c hanno 4 difetti (+2 modelli) e nella misura 4 contano cancellazioni/creazioni di file come cambi del token di fine
(18 modelli, tra cui 8 Qwen3 per cui è dimostrato falso). Il 39,7%/58,4% va letto come limite superiore; la stima difendibile è 31–36% (grandi 48–49%).

### Difetti trovati, dal più grave

**Alti** (cambiano una cifra o il suo significato):

1. **Misura 4 conta creazioni/cancellazioni di file come cambi del token di fine** (18 modelli; 8 Qwen3 dimostrati falsi): 39,7% → 31–36%, grandi 58,4% → 48–49% (punto 4).
2. **0c: un errore di rendering nasconde una differenza visibile** (8 voci, 6 cambi, 4 modelli): "uso normale" 33 → 35 modelli, oltre 7 giorni 9 → 11 (punto 3, D1).
3. **"Stessi pesi" significa "uguali al commit prima", non "uguali al rilascio".** Con i file del rilascio invariati M1 = 98/189 (51,9%), non 102 (54%); 8 modelli hanno un file di pesi sostituito prima del ritocco (punto 5c).
4. **La popolazione è dominata da Qwen:** 51/189 modelli, 90% con cambio; senza `Qwen/*` M1 = 40,6% e M1b = 26,1%. Il 54% non descrive "i modelli più scaricati" in generale (punto 1).

**Medi:**

5. 0c ignora i template con nome (`tool_use`): 3 cambi di Hermes-3 sono "solo con strumenti", non "nessun cambio" (D2).
6. 0c conta per file, non per commit: 134 voci = 126 cambi; 8 migrazioni `tokenizer_config.json` → `chat_template.jinja` risultano "non confrontabili" benché il lato mancante sia nello stesso commit (D3).
7. 0c ignora l'oscuramento (un `chat_template.jinja` immutato ha la precedenza: 9 cambi senza effetto) e tratta `chat_template.json` (formato dei processor) come template del modello di testo (D4).
8. La premessa non contiene l'elenco delle chiavi di "comportamento" di 0b; l'elenco è solo nel codice. Due cambi di sola forma del token e 4 di sola definizione di token aggiunti spostano 248 ↔ 240 (punto 2). 8 cambi di sola formattazione (a capo, ordine delle chiavi) sono dentro il 54% di 0a.
9. **La bisezione perde cambi:** 34 (14 modelli), 21 dei quali di file primari a pesi identici; e sbaglia 2 rilasci (pesi cancellati e ricaricati). Effetto: M1 +1, M3 +8% (punto 5b).
10. M3 è calcolata sui cambi, non sui modelli (mediana 5,1 g contro 0,75 g per il primo cambio di ogni modello); il metodo del quartile non è dichiarato (Q3 36,0 oppure 33,0).

**Bassi:** 11. un modello escluso senza dirlo (`unsloth/GLM-5.3-GGUF`); i 10 riservati sono tutti "grandi". 12. I due Hermes con JSON non valido sono "comportamento" solo per accidente del codice. 13. `.bin`/`.pt` catturano `training_args.bin`, `lfstest.bin` (nessun effetto). 14. `scarica` tronca a 5 MB senza avvisare (nessun file ci arriva). 15. L'indice dei commit è a base 0 e non è scritto da nessuna parte.

**Taglia dei numeri (regola del 16/10):** 189 modelli è un campione adeguato per M1/M1b, ma le classi di 0c sono di 30–44 cambi e i casi "visibili oltre 7 giorni" sono 9–11 modelli (uno è una fixture di test): per quella cifra è solo un indizio, non un risultato.

## 1. Passo 0a (da `modelli.jsonl`, codice `ricalcolo_0a.py`)

**Coincide al 100%.** 200 righe = 10 non accessibili (401) + **1 senza rilascio** (`unsloth/GLM-5.3-GGUF`: nessun file di
pesi né primario in tutta la storia) + 189 analizzati. M1 102 (54,0%), M1b 67 (35,4%); per file (modelli):
tokenizer_config 81, chat_template.jinja 26, chat_template.json 2, generation_config 50, special_tokens_map 28;
grandi 70/89 (78,65%), oltre 7 giorni 45/89 (50,6%); 245 cambi-commit e 294 cambi di file primari a pesi identici.
M3: mediana 5,05 g, quartili 0,74 / 5,05 / 36,02 (metodo "esclusivo" di Python). Con il metodo "inclusivo" (quello di
NumPy/Excel) il terzo quartile è **33,0**, non 36,0: la cifra dipende dal metodo e il metodo non è dichiarato.

Difetti di definizione/riporto trovati (nessuno cambia le cifre):

- **Esclusione silenziosa:** "189 analizzati (10 non accessibili)" non spiega gli 11 mancanti: 200 − 10 = 190. L'undicesimo
  (`unsloth/GLM-5.3-GGUF`) è fuori senza che nessun file lo dica. La premessa promette "non esclusi in silenzio".
- **L'unità di M3 è il cambio, non il modello.** La mediana 5,1 g e i quartili sono su 245 cambi-commit di 102 modelli:
  i modelli con molti ritocchi pesano di più. Per modello (primo cambio) la mediana è **0,75 g** (quartili 0,31/0,75/7,13).
  Le due cose dicono storie diverse ("un ritocco a metà settimana" contro "il primo ritocco arriva nel giro di un giorno")
  e vanno dichiarate entrambe.
- **I 10 non accessibili sono tutti di organizzazioni "grandi"** (meta-llama ×8, google ×2): la stima delle grandi (89 su 99)
  esclude proprio i modelli più noti. Direzione del bias ignota; va scritto.
- **La popolazione è molto raggruppata.** 51 dei 189 sono `Qwen/*` e 46 di questi 51 (90%) hanno un cambio. Senza `Qwen/`:
  M1 = 56/138 = **40,6%**, M1b = 36/138 = **26,1%**; grandi senza Qwen: 24/38 = **63,2%** (M1) e 14/38 = 36,8% (M1b).
  Cinque modelli sono fixture di test (`trl-internal-testing/tiny-*`, `peft-internal-testing/*`, `llamafactory/tiny-random-*`),
  tutti e 5 con cambio; senza di loro M1 = 97/184 = 52,7%. I 74 derivati quantizzati (AWQ/GPTQ/FP8/GGUF…) hanno
  M1 = 21/74 = 28,4%, i 115 non quantizzati 81/115 = 70,4%. Le cifre vere sono giuste, ma "54% dei modelli più scaricati"
  è soprattutto "i modelli Qwen e i loro derivati": 28 organizzazioni distinte fra i 102 modelli con cambio.
  (Script: `ricalcolo_composizione.py`.)
- **Definizione di "pesi identici" più debole del titolo:** vedi punto 5.
- Due rilasci "approssimati" (`kindlingai/glm-5.3-exlr8-k2-k3-k4`, indice 668 su 676 commit; `FastFlowLM/GPT-OSS-20B-NPU2`, 1 su 12):
  nessun file di pesi nella cartella principale in tutta la storia, quindi il "rilascio" è il primo file primario. Per il primo
  cade quasi in fondo alla storia: 8 commit di osservazione post-rilascio, contato comunque tra i 189.

## 2. Passo 0b (codice `ricalcolo_0b.py`)

I 294 cambi di file di `piano_0b.json` coincidono uno a uno con quelli ricavabili da `modelli.jsonl` (stessi repo/commit/file,
conteggi per file 149/70/39/32/4), e la dimensione di ognuna delle 526 versioni su disco coincide con `byte_prima/byte_dopo`.

**La premessa non contiene l'elenco delle chiavi di "comportamento"** (cita solo `model_max_length` come innocuo):
l'elenco sta solo nel codice dell'altra sessione. Ho fissato un elenco mio in base al ruolo delle chiavi in transformers,
senza guardare il loro, in due versioni:

| | comportamento | innocuo | illeggibile |
|---|---|---|---|
| **loro** | 248 | 46 | – |
| mia *stretta* (template, token bos/eos/pad/unk e id, campionamento/lunghezza) | 240 | 52 | 2 |
| mia *larga* (stretta + definizione dei token speciali e opzioni di tokenizzazione) | 253 | 39 | 2 |

Le 8 differenze con la stretta sono tutte spiegate:

1. **2 cambi di sola forma del token** (`mistralai/Mistral-7B-Instruct-v0.2` e `unsloth/mistral-7b-v0.3-bnb-4bit`,
   `special_tokens_map.json`): `"</s>"` diventa `{"content": "</s>", "lstrip": false, …}`. Stesso token. Il loro classificatore
   confronta i valori grezzi, quindi li conta come cambio di comportamento.
2. **4 cambi di sola definizione dei token aggiunti** (`added_tokens_decoder`/`additional_special_tokens`:
   `trl-internal-testing/tiny-Qwen3ForCausalLM` ×2, `swiss-ai/Apertus-8B-Instruct-2509` ×2): sono nella loro lista, non
   nella mia stretta (sono nella larga).
3. **2 file con JSON non valido** (`NousResearch/Hermes-3-Llama-3.1-8B`, `tokenizer_config.json`, commit `ebcf7c1a` e
   `48983928`, 3 minuti l'uno dall'altro): il commit `ebcf7c1a` introduce una parentesi sbagliata nel template "tool_use" e
   il successivo la ripara. Per il loro codice sono "comportamento" per un caso: il file illeggibile diventa `{"_testo": …}`
   e quindi *tutte* le chiavi risultano cambiate (infatti l'elenco "chiavi cambiate" dell'esito include `_testo`, `eos_token`,
   `bos_token`… anche se nessuno le ha toccate). La classe è difendibile ma per accidente; andrebbe dichiarata "illeggibile".

**I modelli coincidono esattamente:** i 94 modelli con almeno un cambio di comportamento sono gli stessi nelle due versioni,
63/89 le grandi. La cifra della premessa/pubblicazione (49,7% e 70,8%) regge a queste differenze di definizione; la versione
larga dà 95/189 (50,3%) e 63/89.

Altri difetti:

- **8 cambi sono identici dopo aver letto il JSON** (solo a capo finale: `Qwen/Qwen3-0.6B` ×2, `Qwen/Qwen2.5-Coder-14B-Instruct`;
  riordino delle chiavi: `unsloth/Llama-3.2-1B-Instruct`, `facebook/opt-125m`, `NousResearch/Hermes-3…/67bf4aca`; forma del token:
  i due Mistral sopra). Sono contati come "cambio post-rilascio" in 0a (e quindi dentro il 54%) perché 0a guarda l'oid del file.
  I 102 − 94 = 8 modelli di differenza fra M1 e 0b sono in parte questo.
- **Creazione/cancellazione di un file = "tutte le chiavi sono cambiate".** Se il file non esiste (prima o dopo) l'altro
  lato diventa `{}`. Questo gonfia il passo 4 (punto 4).
- `scarica` tronca a 5 MB in silenzio (nessun file ci arriva: il più grande è molto più piccolo, e ho verificato che tutte
  le 526 dimensioni su disco coincidono con quelle dichiarate).

## 3. Passo 0c (codice `ricalcolo_0c.py`, `ricalcolo_0c_v2.py`, `ricalcolo_oscurati.py`)

Rendering con `render_jinja_template` di transformers 5.5.4, mie cinque conversazioni equivalenti (C1–C5; il mio strumento
ha anche la descrizione del parametro, il loro no: ho provato entrambe).

**1) Il rendering coincide.** Dove i due insiemi sono confrontabili (101 voci) l'insieme delle conversazioni che cambiano è
**identico in 101 casi su 101**: il rendering delle due sessioni concorda; le differenze qui sotto vengono dalle regole di classificazione.

**2) Con le loro regole riproduco le loro cifre esatte** (`ricalcolo_0c_v2.py`, regole "loro": un'unità per file, template con
nome → solo "default", un errore in qualunque conversazione → "errore di rendering"): 134 voci = 34 nessun cambio visibile /
39 uso normale / 30 solo strumenti / 8 errore di rendering / 23 non confrontabile; 33 modelli con un cambio d'uso normale,
9 oltre 7 giorni.

**3) Ma le regole hanno quattro difetti**, che cambiano le cifre (unità: cambio = (modello, commit): 126 invece di 134 voci,
perché 8 commit toccano due file insieme):

| Classe | loro (134 voci) | corretto (126 cambi) | cosa è successo |
|---|---|---|---|
| uso normale | 39 | **44** | +8 voci "errore" (= 6 cambi) avevano differenze visibili in C1–C4; −1 oscurato |
| solo con strumenti | 30 | **32** | +3 Hermes (template "tool_use"); −1 oscurato |
| nessun cambio visibile | 34 | **33** | −3 Hermes (ora "solo strumenti"), −1 doppione di commit, +3 migrazioni risolte |
| errore di rendering | 8 | **0** | le 8 voci hanno differenze reali in C1–C4 |
| non confrontabile | 23 | **8** | 8 voci erano migrazioni tokenizer_config ↔ jinja nello stesso commit; 7 hanno un jinja immutato che ha la precedenza (senza effetto) |
| oscurato (nessun effetto) | – | **9** | un `chat_template.jinja` immutato ha la precedenza sulla chiave modificata: 2 erano "uso normale"/"solo strumenti", 7 "non confrontabili" |
| **modelli con "uso normale"** | **33** | **35** | + `mistralai/Mistral-7B-Instruct-v0.2`, + `swiss-ai/Apertus-8B-Instruct-2509` |
| di cui oltre 7 giorni | 9 | **11** | gli stessi due modelli |

I quattro difetti:

- **D1, un errore nasconde una differenza.** Se una qualunque conversazione dà errore da un lato, la voce diventa "errore di
  rendering" anche se `conversazioni_diverse` mostra differenze di testo in C1–C4. Le 8 voci "errore" sono: gpt-oss-20b e -120b
  (C5: lo strumento di prova non ha `description` nel parametro → `UndefinedError`), Mistral-7B-Instruct-v0.2 (il template vieta
  il ruolo "system" → errore in C2/C4 prima e/o dopo), Apertus (C5). Sono errori del *banco di prova* o del template in sé,
  non del cambio, e in tutte e 8 le voci C1–C4 cambiano davvero. Sono 6 commit e 4 modelli, due dei quali (Mistral, Apertus) non
  compaiono in nessun'altra voce "uso normale" → **33 → 35 modelli**.
- **D2, il template con nome viene ignorato.** transformers sceglie `tool_use` se si passano strumenti (`get_chat_template`,
  tokenization_utils_base.py riga 3216). Hermes-3 ha 4 voci (aggiunta e tre modifiche del template "tool_use"): per il loro codice
  sono "nessun cambio visibile", ma 3 di loro cambiano C5 (con strumenti).
- **D3, l'unità è il file, non il commit.** Lo stesso commit tocca spesso due file che sono lo stesso template (gpt-oss: jinja +
  json; Qwen3-Coder, Nemotron, unsloth/Llama-3.2, tiny-Qwen*: template spostato da `tokenizer_config.json` a
  `chat_template.jinja`). 134 voci sono 126 cambi. Per le migrazioni il loro confronto "file per file" non trova il lato mancante
  e scrive "non confrontabile" (8 voci), mentre l'altro file dello *stesso commit* lo contiene: per il template effettivo sono
  5 "nessun cambio visibile" e 3 "solo con strumenti" (Qwen3-Coder).
- **D4, oscuramento.** In transformers 5 (`tokenization_utils_base.py`, riga ~1776) `chat_template.jinja` ha la precedenza sulla
  chiave `chat_template` di `tokenizer_config.json`. Per gli 87 cambi in cui nessun `chat_template.jinja` è tra i file cambiati ho chiesto
  all'API (`paths-info`, solo metadati) se nel commit esisteva un `chat_template.jinja`: in **9** sì. Per tutti e 9 il
  cambio della chiave non ha alcun effetto sull'uso: 2 erano contati come cambi veri (OBLITERATUS/Qwen3.8-27B-OBLITERATED "uso
  normale"; Qwen3-Coder-480B "solo con strumenti"), 7 come "non confrontabili" (gpt-oss ×2, Nemotron-3-Nano-4B, Laguna ×3,
  Qwen3-Coder-480B). `chat_template.json` è invece il formato legacy dei *processor* e non è letto dal tokenizer di testo:
  le 4 voci (gpt-oss ×2 commit) sono cambi del processor, non del modello di testo.

Il "non confrontabile" residuo (**8** cambi) è di tre tipi, che con i soli metadati non si possono confrontare (servirebbe scaricare
altri file, e non l'ho fatto): **5** in cui il lato "prima" non ha un template, cioè *aggiunta del primo template*
(tiny-Qwen2, tiny-Qwen3, unsloth/Llama-3.2-1B-Instruct — per questi tre l'API conferma che non c'era nemmeno un jinja —,
PrimeIntellect/Qwen3-0.6B e 0bserverx, dove il jinja nasce nel commit); **1** in cui il jinja viene cancellato
(Qwen3-Coder-480B, commit 61868e40); **2** Hermes con JSON non valido. "Aggiunta del template" è un cambio vero, di natura
diversa da "il testo cambia": la premessa non ha una classe per questo.

**Sulla taglia dei numeri:** "9 oltre 7 giorni" (o 11) sono 9–11 modelli, 5–6% dei 189, e uno degli 11 è una fixture di test
(`llamafactory/tiny-random-Llama-3`). Sotto i 30–40 casi (regola del 16/10) è un indizio, non un risultato. I 35 modelli con
cambio d'uso normale sono sul bordo di quella soglia e 18 sono `Qwen/*` (51%); degli 11 oltre 7 giorni, 3 sono `Qwen/*`.

## 4. Misura 4 — "cambio reale" (codice `ricalcolo_4.py`)

**Il calcolo coincide:** con le loro classificazioni (template "uso normale" di `rendering_0c.json` ∪ chiavi `eos_token`/`eos_token_id`
cambiate ∪ chiavi di campionamento cambiate) ottengo 75/189 = 39,7% e 52/89 = 58,4% esatti.

**Il significato no.** La parte "token di fine" conta come cambio *anche la creazione o la cancellazione di un file*
(`{}` contro `{eos_token: …}`). I modelli che entrano nei 75 *soltanto* per questo sono **18** (8 sono Qwen3 "grandi"):

- `Qwen/Qwen3-{0.6B,1.7B,4B,8B,14B,30B-A3B,32B,235B-A22B}`: **cancellazione di `special_tokens_map.json`**. Verificato sui loro
  file: il file cancellato diceva `eos_token = <|im_end|>`, `pad_token = <|endoftext|>`; il `tokenizer_config.json` dello stesso
  repository dice la stessa cosa. Il token di fine non è cambiato.
- altri 10, **non verificabili** senza `config.json` (che non ho): creazione di `generation_config.json` (gpt2, gpt2-large,
  distilgpt2, GLM-4.5-Air) o dei file del tokenizer in un repository che non li aveva (gpt-neo-125m, pythia-70m-deduped,
  SmolLM2-135M — l'unico "grande" —, PrimeIntellect/Qwen3-0.6B, peft tiny-random-OPT, unsloth/mistral-7b-v0.3-bnb-4bit). Il valore
  dell'eos di solito è già in `config.json`, ma non l'ho verificato.

Se si contano come cambio del token di fine solo le *modifiche* (stesso file presente prima e dopo) e il template "uso normale"
corretto di cui sopra (35 modelli): **58/189 = 30,7%**, grandi **43/89 = 48,3%**. Le creazioni non verificabili possono
riportarlo fino a 68/189 (36,0%) e 44/89 (49,4%), non oltre. Il dato dichiarato (39,7%/58,4%) è quindi **un limite superiore**,
non una stima: dire "tra il 31% e il 36% (grandi 48–49%)" è difendibile; "39,7%" no. Per riferimento la versione "campionamento
con creazioni, eos con creazioni, template corretto" dà 76/189 (40,2%), 52/89.

Nota minore: la loro lista "campionamento" include `max_new_tokens`/`max_length` (limiti di lunghezza, non campionamento);
non cambia nessuna cifra (provato con e senza).

## 5. Controllo della raccolta

**5a. Il campione richiesto.** Seme **20261020**: `random.Random(20261020).sample(<189 modelli ordinati per nome>, 20)`.
Per ognuno ho scaricato dall'API (solo metadati, 0,4 s fra le richieste, nessun token) l'elenco dei commit di `main` e l'albero
della cartella principale di **ogni** commit, senza bisezione, e ho ricostruito rilascio e cambi con il mio codice
(`ricalcolo_campione.py`). I 20: EleutherAI/pythia-14m, HuggingFaceTB/SmolLM3-3B, IlyaGusev/saiga_llama3_8b,
LiquidAI/LFM2.5-230M-GGUF, NousResearch/Hermes-3-Llama-3.1-8B, Qwen/Qwen2.5-32B-Instruct-GPTQ-Int4,
Qwen/Qwen2.5-Coder-7B-Instruct-GPTQ-Int4, Qwen/Qwen3-0.6B-Base, Qwen/Qwen3-1.7B-Base, Qwen/Qwen3-32B-AWQ,
RadixArk/Kimi-K3-DSpark, RedHatAI/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-FP8, empero-ai/Qwen3.8-2B-Distill-GGUF,
llamafactory/tiny-random-Llama-3, nvidia/Gemma-4-31B-IT-NVFP4, nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16,
nvidia/NVIDIA-Nemotron-3.5-Lightning-30B-A3B-BF16, openbmb/MiniCPM5-2B-DSpark, prism-ml/Bonsai-27B-mlx-1bit,
sakamakismile/Qwen3.8-27B-MTP-NVFP4 (8 di loro non hanno nessun cambio elencato: servono a cercare i cambi *mancati*).

Esito: stesso numero di commit in 20/20; stesso rilascio (commit e indice) in 20/20; **55 cambi elencati in `modelli.jsonl` =
55 trovati**, nessuno mancante, nessuno in più; per tutti e 55 coincidono commit, indice, data, file primari/secondari
cambiati e flag `pesi_cambiati` (calcolato da me con le impronte LFS di tutti i file `.safetensors/.bin/.gguf/.pt/.pth`);
M1 = 12/20 nelle due ricostruzioni. Dei 55, 40 sono cambi di file primari a pesi identici (44 file) e 3 hanno pesi cambiati
nello stesso commit. **I cambi elencati esistono davvero e i pesi non cambiano in quel commit.** (L'indice dei commit in
`modelli.jsonl` è a base 0: il primo commit è 0; la premessa non lo dice.)

**5b. Tutti i 189, non richiesto ma a costo zero** (≈4.300 chiamate agli alberi, circa un'ora entro il limite di 500 richieste per
5 minuti). Stesso metodo, stesso codice:

| Controllo | Esito |
|---|---|
| numero di commit | 188/189 uguali (`AtomicChat/Qwen3.8-Flash-Next-GGUF` ha un commit nuovo dopo il censimento: 31 contro 30) |
| rilascio | 187/189 uguali. Due diversi: `shibing624/macbert4csc-base-chinese` (pesi caricati al commit 6, cancellati al 13, ricaricati al 16: la bisezione dà 16, la definizione letterale 6) e `JonathanColetti/Qwen3.8-27B-Uncensored-GGUF` (un `_uploadtest.gguf` al commit 2, cancellato al 3: bisezione 7, letterale 2) |
| cambi elencati che esistono davvero | **418/418**, nessuno inventato, nessun disaccordo su file, pesi, data |
| cambi che la bisezione ha **perso** | **34** in 14 modelli (A→B→A: un ritocco e il suo annullamento a pochi minuti o ore). Di questi 21 sono cambi di file primari a pesi identici: 245 → **266** cambi |
| M1 | **103** (non 102): il modello in più è macbert4csc, per il rilascio sbagliato |
| M1b | **67**, uguale |
| M2 (modelli per file) | 82 / 26 / 2 / 50 / 28 (tokenizer_config 82 invece di 81, per macbert) |
| M3 sui 266 cambi | mediana **4,37 g**, quartili 0,74 / 4,37 / 34,5 (dichiarati: 5,1; 0,7/5,1/36,0) |
| Grandi | 70/89 e 45/89 invariati; 164 cambi (invece di 148), mediana 2,08 g (invece di 2,4) |

La premessa lo prevedeva ("M1 è un limite inferiore"): qui lo si quantifica. Per i **modelli** (M1, M1b) l'effetto è quasi nullo
(+1); per i **cambi** (M3) è l'8%. La bisezione assume che i pesi, una volta comparsi, restino: macbert e Jonathan sono due
casi in cui non è vero (`censimento.py`, `primo_indice`).

**5c. "A pesi identici": rispetto a cosa?** La definizione della premessa confronta i pesi con quelli del **commit
precedente**, non con quelli del rilascio. Con la scansione completa ho misurato la versione forte (`ricalcolo_pesi.py`):

| Condizione sui pesi | M1 | M1b | grandi M1 |
|---|---|---|---|
| uguali al commit prima (premessa) | 103 (54,5%) | 67 (35,4%) | 70/89 (78,7%) |
| i file di pesi del rilascio sono tutti ancora lì e invariati (si ammettono file aggiunti) | **98 (51,9%)** | **63 (33,3%)** | 68/89 (76,4%) |
| mappa dei pesi identica a quella del rilascio (esclude anche le quantizzazioni aggiunte) | 86 (45,5%) | 55 (29,1%) | 64/89 (71,9%) |

Cinque modelli hanno cambi di configurazione solo dopo che un file di pesi era già stato sostituito (`saiga_llama3_8b`,
`microsoft/phi-2`, `NVIDIA-Nemotron-3.5-Lightning-30B-A3B-NVFP4`, `macbert4csc`, un GGUF di 0bserverx). In totale 8 modelli hanno
un file di pesi *sostituito* (stesso nome, impronta diversa) prima di un cambio di configurazione. Il titolo "stessi pesi" regge
al **98/189 (51,9%)**, non al 54%; la differenza è piccola ma andava dichiarata. In totale 66 modelli hanno almeno un commit
che cambia i pesi senza toccare la configurazione (871 eventi, in gran parte repository GGUF che aggiungono quantizzazioni).

**5d. Piccoli difetti di definizione dei "pesi".** `.bin` e `.pt` catturano file che non sono pesi: `training_args.bin`
(SmolLM2-135M-Instruct, TinyLlama-1.1B-Chat-v1.0), `lfstest.bin` (un GGUF di BoldingBuilds), `mp_rank_00_model_states.pt`
(pythia-14m). Nessun effetto sulle cifre (ricalcolando il rilascio senza questi file cambia un solo modello, di qualche
ora e senza conseguenze su M1/M1b).

**5e. La popolazione.** Ho rifatto la query `pipeline_tag=text-generation&sort=downloads&limit=200` il 20/10 sera:
**200/200 repository identici**, stesse cifre di download, stesso ordine nei primi 20.


## 6. Cosa NON ho potuto controllare

- **Non ho scaricato nessun contenuto** (oltre ai file già in `file0b/`). Per questo non ho potuto: risolvere gli 8 "non
  confrontabili" (servono i `tokenizer_config.json`/`chat_template.jinja` dei commit vicini, pochi KB: richiedono l'OK dell'utente);
  verificare le 10 creazioni di `generation_config.json`/tokenizer del punto 4 contro `config.json`; leggere `config.json` e
  `tokenizer.json` (file "secondari", mai analizzati nel contenuto).
- **L'effetto sui punteggi** (passo 1, `effetto.py`) è fuori dal mio incarico e non l'ho toccato.
- **I 10 repository riservati** (401) non sono ricontrollabili senza token: restano non accessibili anche per me.
- **I cambi dentro le sottocartelle** (la premessa guarda solo la cartella principale) non li ho visti.
- **Il contenuto semantico dei template e dei token**: ho verificato che il testo renderizzato cambia, non che il cambio sia
  "migliore" o "peggiore", né che cambi i punteggi.
- **Il contenuto dei file nei commit persi dalla bisezione** (i 34 del punto 5b): ne ho visto solo i metadati.
- **Le licenze dei 506 file di terze parti in `file0b/`** non sono state riviste (la regola del progetto dice di mostrare la lista
  dei file prima di qualunque pubblicazione: ricordarsene prima di rendere pubblico il repository).
- Non ho rieseguito `effetto.py` né i test unitari dell'altra sessione.

## 7. File e come riprodurre

Tutti in `strumenti/esperimenti_ricalcolo/`. Interprete: `registro-env/Scripts/python.exe -I`.

| File | Cosa fa | Dati |
|---|---|---|
| `ricalcolo_0a.py` | M1–M4 da `modelli.jsonl` | `<corsa1>` |
| `ricalcolo_0b.py` | classificazione stretta/larga dei 294 cambi | `<corsa1>` + `file0b/` |
| `ricalcolo_0c.py`, `ricalcolo_0c_v2.py` | rendering, regole "loro" e "corrette" (dal 21/10 la regola è applicata alla lettera) | idem |
| `ricalcolo_oscurati.py`, `hf_api.py` | jinja che oscura la chiave (API `paths-info`) | rete, solo metadati |
| `ricalcolo_4.py` | misura 4 | uscite dei precedenti |
| `ricalcolo_composizione.py` | sensibilità a Qwen/fixture/quantizzati | `<corsa1>` |
| `ricalcolo_campione.py`, `ricalcolo_completo.py` | storia commit per commit da API, confronto (20 o 189 modelli) | rete, solo metadati |
| `ricalcolo_pesi.py` | quanto regge "a pesi identici" (rilascio vs commit prima) | cache della raccolta |
| `numeri_miei_prima_del_confronto.md` | i miei numeri prima di aprire il codice altrui | – |

## 8. Aggiornamento del 21/10 — regola 0c alla lettera (nessuna cifra cambia)

**Richiesta** (secondo controllo, Codex, in sola lettura): `classe_corretta()` in `ricalcolo_0c_v2.py` decideva "non confrontabile"
guardando solo C1 ed "errore di rendering" solo se *tutte* le C1–C4 fallivano su entrambi i lati, mentre la regola adottata
(premessa, "Correzioni dopo il ricalcolo", punto 4) dice: errore / non confrontabile solo se **nessuna** conversazione normale
(C1–C4) è confrontabile.

**Correzione** (stesso file, nuova funzione `classe_corretta`; la vecchia resta come `classe_corretta_20_10` per poter elencare i
passaggi di classe). Regola applicata alla lettera, in quest'ordine:

1. *oscurato (nessun effetto)*: un `chat_template.jinja` non cambiato dal commit ha la precedenza (invariato rispetto al 20/10);
2. una conversazione normale Ci (i = 1…4) è **confrontabile** se entrambi i lati la rendono senza errore (il lato mancante conta
   come non confrontabile);
3. **uso normale** se almeno una Ci confrontabile differisce;
4. altrimenti **solo con strumenti** se C5, confrontabile, differisce;
5. altrimenti **nessun cambio visibile** se almeno una Ci è confrontabile;
6. se nessuna Ci è confrontabile e non ci sono altre differenze: **non confrontabile** (manca un lato) oppure **errore di rendering**
   (i template ci sono ma non si renderizzano).

**Esito, 126 cambi (modello, commit)** — identico alla versione del 20/10, con lo strumento di prova completo e con quello povero:

| Classe | 20/10 (solo C1) | 21/10 (alla lettera) |
|---|---|---|
| uso normale | 44 | **44** |
| solo con strumenti | 32 | **32** |
| nessun cambio visibile | 33 | **33** |
| oscurato (nessun effetto) | 9 | **9** |
| non confrontabile | 8 | **8** |
| errore di rendering | 0 | **0** |
| modelli con "uso normale" (grandi) | 35 (26) | **35 (26)** |
| di cui oltre 7 giorni | 11 | **11** |

**Misura 4** (`ricalcolo_4.py` rilanciato con le classi del 21/10): **58/189 = 30,7%, grandi 43/89 = 48,3%** (invariate). Anche le
altre varianti sono invariate: con "solo con strumenti" 64/189 (33,9%) e 49/89; con le creazioni di file contate come token di fine 76/189 (40,2%) e
52/89 (limite superiore); il valore con il loro metodo resta 75/189 e 52/89. (Nota: nel rapporto del 20/10 la misura 4 era stata
calcolata con le classi del primo script di 0c, `ricalcolo_0c.py`, che non gestiva i template con nome; i modelli con "uso normale"
sono gli stessi 35, quindi nulla cambia.)

**Cambi che passano di classe: nessuno (0).** Perché: il caso che temeva Codex — C1 non confrontabile ma C2–C4 sì — **non esiste**
in questi dati. Il numero di conversazioni normali confrontabili per cambio è:

| Normali confrontabili | Cambi | Classe |
|---|---|---|
| 4 su 4 | 109 | 42 uso normale, 32 solo strumenti, 33 nessun cambio, 2 oscurati |
| 2 su 4 (C1, C3) | 2 | uso normale: `mistralai/Mistral-7B-Instruct-v0.2` commit `1296dc8f` (C2 e C4 danno `TemplateError` — ruolo "system" vietato — prima *e* dopo; C3 differisce) e `250544c9` (C2 e C4 errore solo *prima*; C1 e C3 differiscono) |
| 0 su 4 | 15 | 8 non confrontabili (manca un lato) + 7 oscurati |

Gli 8 "non confrontabili" hanno tutti un lato mancante (nessun template prima o dopo, oppure JSON non valido: tiny-Qwen2, tiny-Qwen3,
unsloth/Llama-3.2-1B-Instruct, PrimeIntellect/Qwen3-0.6B, 0bserverx/Qwen3.8-27B-…, Qwen3-Coder-480B commit `61868e40`, Hermes-3 ×2)
e quindi nessuna C5 confrontabile: non hanno "altre differenze". Nessun cambio ha i template presenti su entrambi i lati e
nessuna Ci confrontabile, quindi **"errore di rendering" resta a 0 cambi** (le 8 voci "errore" del 20/10 nel loro codice erano
tutte differenze reali). I due Laguna (commit `3ff0d451`, `4f8aa297`) hanno il template "prima" che non si renderizza
(`TypeError`, il template usa `include`/`import` che il sandbox non carica), ma sono "oscurati" da un jinja immutato e non contano comunque.

**Informazione:** le conversazioni normali con errore su *un solo* lato (escluse dal confronto dalla regola alla lettera) sono 2, nello
stesso cambio (`Mistral-7B-Instruct-v0.2` `250544c9`, C2 e C4: errore prima, ok dopo). Contarle come differenza non cambia la classe,
che è già "uso normale" per C1 e C3.

**Riproduzione:** `python -I ricalcolo_0c_v2.py renderizza <corsa1> <render_v2.json> <oscurati.json>` poi
`python -I ricalcolo_0c_v2.py riassumi <render_v2.json> <classi_0c_v2_21_10.json>` e
`python -I ricalcolo_4.py <corsa1> <mio_0b.json> <classi_0c_v2_21_10.json>`. Solo CPU, nessun download nuovo (nessuna chiamata all'API:
il file `oscurati.json` del 20/10 è riusato).

