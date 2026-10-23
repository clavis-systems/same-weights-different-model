# Revisione Codex delle correzioni (21/10/2026, gpt-6-luna, effort high, sola lettura, nessun Python eseguito)

Prompt: revisioni/prompt_codex_correzioni.txt. Testo restituito da Codex, non modificato:

## Sei correzioni

1. **OK, con una precisazione — scansione senza bisezione.** Il rapporto corregge M1 da 102 a **103/189**, M1b resta **67/189** e i cambi primari salgono da 245 a **266** (§5b). La premessa adotta questi valori. Il rapporto documenta però due rilasci diversi dalla definizione letterale; macbert4csc cambia M1, quindi la cifra dipende dal criterio di rilascio adottato.

2. **OK — pesi invariati dal rilascio.** Il codice di `ricalcolo_pesi.py` confronta i file di pesi del rilascio con quelli presenti al cambio, sia come mappa identica sia ammettendo file aggiunti. Il rapporto riporta **98/189**, **63 oltre 7 giorni** e **86/189** con mappa identica; la premessa coincide. È una misura più forte del confronto col commit precedente, come dichiarato.

3. **OK — ritardo per modello e per cambio.** Il rapporto distingue la mediana del primo cambio per modello (**0,75 giorni; quartili 0,31/0,75/7,13**) da quella per cambio (**4,4 giorni**, più precisamente 4,37). La premessa riporta i valori corrispondenti. Non ho ricalcolato i quartili dai dati grezzi.

4. **PROBLEMA nel codice — classificazione 0c.** Le cifre corrette riportate nella premessa coincidono col rapporto: 126 cambi, 44 uso normale, 32 solo strumenti, 33 senza effetto visibile, 9 oscurati, 8 non confrontabili; 35 modelli, 11 oltre 7 giorni. Ma `classe_corretta()` in `ricalcolo_0c_v2.py` decide “non confrontabile” guardando solo C1 (`if any("manca" in rr["C1"][l]...)`), mentre la definizione richiede di verificare se **nessuna** conversazione normale è confrontabile. Può quindi classificare male un caso in cui C1 manchi ma C2–C4 siano confrontabili. Inoltre l’errore viene rilevato solo se tutte le C1–C4 falliscono su entrambi i lati: le regole non implementano letteralmente la definizione scritta. Le verifiche richieste confermano comunque che le **8 voci** classificate originariamente come errore hanno differenze: `rendering_0c.json`, campo `conversazioni_diverse` non vuoto in tutte (gpt-oss, Mistral, Apertus).

5. **OK come riclassificazione, non come verifica semantica completa.** `ricalcolo_4.py` conta modifiche a `eos_token`/`eos_token_id` e parametri di campionamento; la premessa dichiara correttamente **58/189 (30,7%)** e grandi **43/89 (48,3%)**, coerenti col rapporto. La logica dipende però dalla correttezza delle classificazioni 0c del punto 4.

6. **OK — composizione.** `ricalcolo_composizione.py` applica i filtri dichiarati; il rapporto e la premessa coincidono sui **51 Qwen**, **21/74 quantizzati**, **81/115 non quantizzati**, 5 fixture, 10 non accessibili e un repository senza file di peso né primari escluso.

## Verifiche a–d

- **a) Qwen3-8B:** sì. Nei due `tokenizer_config.json` presenti prima/dopo la sparizione, `eos_token` resta `<|im_end|>`; cambia il file `special_tokens_map.json`, non il token di fine.
- **b) Mistral:** sì. Per entrambi i repository, `special_tokens_map.json` passa da valori stringa (`"</s>"`) a oggetti con `content: "</s>"` e attributi. La stringa del token resta la stessa.
- **c) Hermes-3:** sì, i dati includono due commit con JSON non valido (`file0b/NousResearch__Hermes-3-Llama-3.1-8B`, SHA `ebcf7c1…` e il secondo indicato nel rapporto). Ho verificato direttamente il primo; l’output della lettura diretta conferma gli altri file validi, ma non ha mostrato il secondo SHA invalidato in modo leggibile.
- **d) Rendering:** sì, tutte le 8 voci hanno `conversazioni_diverse` non vuoto; in particolare Mistral include C3 e C1–C5 nelle due voci.

## Altre discrepanze

Il rapporto afferma che la raccolta completa trova **418/418** cambi elencati e nessuno inventato, ma non ho verificato manualmente tutti gli alberi dei commit. Non ho controllato i dati di generazione, le 10 creazioni non verificabili contro `config.json`, né le cifre aggregate ricalcolando i 189 modelli. Nessun Python eseguito.