# I miei numeri, scritti PRIMA di aprire il codice, riassunto.json, classificazione_0b.json, rendering_0c.json e verifica_pesi.json dell'altra sessione

Scritto il 20/10/2026 (ora locale: vedi commit). Il solo materiale letto finora: PREMESSA.md, README.md, istantanea.json,
modelli.jsonl, piano_0b.json, file0b/ (file di configurazione), COORDINAMENTO.md (solo le prime 80 righe).

## 0a (da modelli.jsonl, codice mio: ricalcolo_0a.py)
- 200 righe: 10 non accessibili (401), 1 senza rilascio (unsloth/GLM-5.3-GGUF: nessun file di pesi mai) -> 189 analizzati.
- M1 = 102/189 = 54,0%; M1b (oltre 7 giorni) = 67/189 = 35,4%.
- Per file (modelli): tokenizer_config 81, chat_template.jinja 26, chat_template.json 2, generation_config 50, special_tokens_map 28.
- M3 (su tutti i 245 cambi-commit a pesi identici): mediana 5,05 g; quartili 0,74 / 5,05 / 36,02 (metodo esclusivo)
  oppure 0,74 / 5,05 / 32,98 (metodo inclusivo). Per il primo cambio di ogni modello: mediana 0,75 g (0,31 / 0,75 / 7,13).
- Grandi organizzazioni: 70/89 = 78,7%; oltre 7 giorni 45/89 = 50,6%.
- 294 cambi di file primari a pesi identici (245 commit).

## 0b (piano_0b.json + file0b/, codice mio: ricalcolo_0b.py; liste di chiavi MIE)
- 294 cambi di file confermati uno a uno contro modelli.jsonl.
- Versione stretta: 240 di comportamento, 52 innocui, 2 illeggibili (Hermes-3, JSON non valido). Modelli 94/189 = 49,7%; grandi 63/89 = 70,8%.
- Versione larga: 253 / 39 / 2. Modelli 95/189 = 50,3%; grandi 63/89.
- 8 cambi sono identici dopo aver letto il JSON (solo a capo finale, ordine delle chiavi, forma del token stringa/dizionario).

## 0c (renderizzazione con transformers 5.5.4, codice mio: ricalcolo_0c.py)
- 122 cambi (modello, commit) con cambio di template (132 se si contano i file); 9 oscurati da un chat_template.jinja non cambiato (API paths-info).
- Classi: uso normale 44, solo con strumenti 29, nessun cambio visibile 32, non confrontabile 15, oscurato 2, errore di rendering 0.
- Modelli con cambio d'uso normale: 35 (grandi 26), oltre 7 giorni 11.

## Misura 4 (ricalcolo_4.py)
- Mia definizione principale (template uso normale | eos modificato | campionamento): 58/189 = 30,7%, grandi 43/89 = 48,3%.
- Contando anche creazioni/cancellazioni di file come cambi del token di fine: 76/189 = 40,2%, grandi 52/89 = 58,4%.
