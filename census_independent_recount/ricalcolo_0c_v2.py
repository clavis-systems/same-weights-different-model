"""Ricalcolo 0c, versione 2: stessa renderizzazione, ma con due insiemi di REGOLE di classificazione.

  regole "loro"     = quelle descritte dalla premessa e dal comportamento osservato nei risultati dell'altra
                      sessione: un'unita' per FILE, per ogni file si confronta solo quel file, un template con nome
                      vale solo "default" (o il primo), qualunque errore in qualunque conversazione => "errore".
                      Serve a verificare che il MIO rendering riproduca i loro numeri quando uso le loro regole.
  regole "corrette" = unita' (modello, commit); template effettivo con la precedenza di transformers 5
                      (chat_template.jinja > chiave di tokenizer_config.json); template con nome (C5 usa "tool_use"
                      se esiste, come transformers); un errore non nasconde una differenza visibile; cambi
                      oscurati da un jinja non cambiato (controllo via API) non contano.

Uso:
  python -I ricalcolo_0c_v2.py renderizza <cartella corsa1> <uscita.json> [oscurati.json]
Il rendering usa transformers 5.5.4 (ambiente registro-env). I template sono dati non fidati: solo testo nel sandbox.
"""
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
          "HuggingFaceTB", "allenai", "ibm-granite"]

UTENTE = "Hello, how are you?"
SISTEMA = "You are a helpful assistant."
# due varianti dello strumento: completa (con descrizione del parametro) e "povera" (senza), come quella
# usata dall'altra sessione, per vedere quanto pesa la scelta sugli errori
STRUMENTO_COMPLETO = {"type": "function", "function": {
    "name": "get_weather", "description": "Get the current weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "City name"}},
                   "required": ["city"]}}}
STRUMENTO_POVERO = {"type": "function", "function": {
    "name": "get_weather", "description": "Get the current weather in a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}


def conversazioni(strumento):
    return {
        "C1": dict(messages=[{"role": "user", "content": UTENTE}], tools=None, gen=True),
        "C2": dict(messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": "What is 2+2?"}],
                   tools=None, gen=True),
        "C3": dict(messages=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello! How can I help?"},
                             {"role": "user", "content": "Name a European capital."}], tools=None, gen=True),
        "C4": dict(messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": "What is 2+2?"},
                             {"role": "assistant", "content": "4"}], tools=None, gen=False),
        "C5": dict(messages=[{"role": "user", "content": "What is the weather in Rome?"}], tools=[strumento], gen=True),
    }


NORMALI = ("C1", "C2", "C3", "C4")


def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def grande(repo):
    return repo.split("/")[0] in GRANDI


def leggi(cartella, voce, lato):
    if voce["byte_" + lato] is None:
        return None
    p = f"{cartella}/file0b/{voce['repo'].replace('/', '__')}/{voce[lato]}/{voce['file']}"
    with open(p, "rb") as f:
        return f.read().decode("utf-8")


def nomi(v):
    """valore della chiave chat_template -> dict nome->testo (stringa => {'default': testo})"""
    if v is None:
        return None
    if isinstance(v, str):
        return {"default": v}
    if isinstance(v, list):
        return {x.get("name"): x.get("template") for x in v if isinstance(x, dict)}
    if isinstance(v, dict):
        return dict(v)
    return None


def da_json(testo):
    """(stato, dict nome->testo) da tokenizer_config.json o chat_template.json"""
    if testo is None:
        return "file_assente", None
    try:
        j = json.loads(testo)
    except Exception:
        return "illeggibile", None
    return "ok", nomi(j.get("chat_template")) if isinstance(j, dict) else None


def sorgenti_del_commit(cartella, files):
    """per un gruppo (modello, commit): sorgenti[nome] = (stato_prima, T_prima, stato_dopo, T_dopo)"""
    s = {}
    if "chat_template.jinja" in files:
        v = files["chat_template.jinja"]
        a, b = leggi(cartella, v, "prima"), leggi(cartella, v, "dopo")
        s["jinja"] = ("ok" if a is not None else "file_assente", None if a is None else {"default": a},
                      "ok" if b is not None else "file_assente", None if b is None else {"default": b})
    for nome, fl in (("json", "chat_template.json"), ("tc", "tokenizer_config.json")):
        if fl in files:
            v = files[fl]
            sp, tp = da_json(leggi(cartella, v, "prima"))
            sd, td = da_json(leggi(cartella, v, "dopo"))
            s[nome] = (sp, tp, sd, td)
    return s


def effettivo(s, lato):
    """template effettivo (dict nome->testo) e origine. lato 1=prima, 3=dopo (indici nella tupla)"""
    for nome in ("jinja", "json", "tc"):
        if nome in s:
            stato, valore = s[nome][lato - 1], s[nome][lato]
            if stato == "illeggibile":
                return None, "illeggibile"
            if valore is not None:
                return valore, nome
    return None, "ignoto"


def scegli(templ, conv_nome, strumenti):
    """sceglie il template con la logica di transformers (get_chat_template)"""
    if templ is None:
        return None
    if strumenti and "tool_use" in templ:
        return templ["tool_use"]
    return templ.get("default")


def renderizza(cartella, dest, oscurati_path=None):
    from transformers.utils.chat_template_utils import render_jinja_template
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        rel = {r["repo"]: r["rilascio"]["data"] for r in map(json.loads, f) if r.get("rilascio")}
    with open(cartella + "/piano_0b.json", encoding="utf-8") as f:
        piano = json.load(f)["voci"]
    oscurati = {}
    if oscurati_path:
        with open(oscurati_path, encoding="utf-8") as f:
            oscurati = json.load(f)
    comuni = dict(bos_token="<s>", eos_token="</s>")
    cache = {}

    def rendi(template, conv):
        chiave = (template, json.dumps(conv, sort_keys=True))
        if chiave in cache:
            return cache[chiave]
        if template is None:
            r = {"manca": True}
        else:
            try:
                out, _ = render_jinja_template([conv["messages"]], tools=conv["tools"], chat_template=template,
                                               add_generation_prompt=conv["gen"], **comuni)
                r = {"ok": out[0]}
            except Exception as e:
                r = {"errore": type(e).__name__}
        cache[chiave] = r
        return r

    gruppi = defaultdict(dict)
    for v in piano:
        gruppi[(v["repo"], v["dopo"])][v["file"]] = v
    risultati = []
    for (repo, commit), files in gruppi.items():
        data = next(iter(files.values()))["data"]
        giorni = (t(data) - t(rel[repo])).total_seconds() / 86400
        s = sorgenti_del_commit(cartella, files)
        # ---- 1) regole "loro": una unita' per file ----
        loro = []
        for fl, v in files.items():
            if not (fl.startswith("chat_template.") or fl == "tokenizer_config.json"):
                continue
            nome = {"chat_template.jinja": "jinja", "chat_template.json": "json", "tokenizer_config.json": "tc"}[fl]
            sp, tp, sd, td = s[nome]
            # per tc: l'unita' esiste solo se la chiave chat_template risulta cambiata o il file e' illeggibile
            cambiata = (tp != td) or "illeggibile" in (sp, sd)
            if fl == "tokenizer_config.json" and not cambiata:
                continue
            if fl.startswith("chat_template.") and (tp == td):
                pass
            # loro: "default" oppure il primo
            def uno(d):
                if d is None:
                    return None
                return d.get("default", next(iter(d.values()), None))
            loro.append({"file": fl, "prima": uno(tp), "dopo": uno(td), "unita_valida": True})
        # ---- 2) regole "corrette": un'unita' per commit ----
        tp_, op = effettivo(s, 1)
        td_, od = effettivo(s, 3)
        cambia = False
        for nome in s:
            sp, tpv, sd, tdv = s[nome]
            if tpv != tdv or "illeggibile" in (sp, sd):
                cambia = True
        if not cambia:
            continue
        risultati.append({"repo": repo, "commit": commit, "data": data, "giorni": giorni,
                          "sorgenti": sorted(s), "origine_prima": op, "origine_dopo": od,
                          "oscurato": oscurati.get(f"{repo}@{commit}") == "oscurato",
                          "loro": loro, "eff_prima": tp_, "eff_dopo": td_})
    # rendering
    for r in risultati:
        for var, strum in (("completo", STRUMENTO_COMPLETO), ("povero", STRUMENTO_POVERO)):
            convs = conversazioni(strum)
            r["corrette_" + var] = {}
            for nome, conv in convs.items():
                tpl_p = scegli(r["eff_prima"], nome, conv["tools"])
                tpl_d = scegli(r["eff_dopo"], nome, conv["tools"])
                r["corrette_" + var][nome] = {"prima": rendi(tpl_p, conv), "dopo": rendi(tpl_d, conv)}
            # per le regole loro: ogni unita' di file
            r["loro_" + var] = []
            for u in r["loro"]:
                rr = {}
                for nome, conv in convs.items():
                    rr[nome] = {"prima": rendi(u["prima"], conv), "dopo": rendi(u["dopo"], conv)}
                r["loro_" + var].append({"file": u["file"], "r": rr})
    for r in risultati:
        del r["eff_prima"], r["eff_dopo"], r["loro"]
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False)
    print("gruppi:", len(risultati))


def diverso(x):
    return x["prima"] != x["dopo"]


def classe_loro(rr):
    """regole dell'altra sessione, riapplicate da me"""
    p = [x["prima"] for x in rr.values()]
    d = [x["dopo"] for x in rr.values()]
    if any("manca" in x for x in p + d):
        return "non confrontabile", []
    err = any("errore" in x for x in p + d)
    diverse = [n for n, x in rr.items() if diverso(x)]
    if err:
        return "errore di rendering", diverse
    if any(n in NORMALI for n in diverse):
        return "uso normale", diverse
    return ("solo con strumenti" if diverse else "nessun cambio visibile"), diverse


def classe_corretta_20_10(rr, oscurato):
    """versione del 20/10 (superata): decideva "non confrontabile" guardando solo C1 e "errore" solo se TUTTE le
    C1-C4 fallivano su entrambi i lati. Resta per poter elencare i cambi che cambiano classe."""
    # se esiste un chat_template.jinja non cambiato dal commit, ha la precedenza: il cambio non ha effetto,
    # anche se un lato (tokenizer_config.json) non si puo' renderizzare
    if oscurato:
        return "oscurato (nessun effetto)", []
    if any("manca" in rr["C1"][l] for l in ("prima", "dopo")):
        return "non confrontabile", []
    diverse = [n for n, x in rr.items() if diverso(x)]
    if all("errore" in rr[n][l] for n in NORMALI for l in ("prima", "dopo")):
        return "errore di rendering", diverse
    if any(n in NORMALI for n in diverse):
        return "uso normale", diverse
    return ("solo con strumenti" if diverse else "nessun cambio visibile"), diverse


def confrontabile(rr, n):
    """una conversazione e' confrontabile se entrambi i lati la rendono senza errore"""
    return "ok" in rr[n]["prima"] and "ok" in rr[n]["dopo"]


def classe_corretta(rr, oscurato):
    """Regola scritta alla lettera (premessa, "Correzioni dopo il ricalcolo", punto 4; 21/10):
      - oscurato: un chat_template.jinja non cambiato dal commit ha la precedenza -> nessun effetto;
      - "uso normale" se almeno una conversazione NORMALE (C1-C4) confrontabile differisce;
      - "solo con strumenti" se nessuna normale differisce ma C5, confrontabile, differisce;
      - "nessun cambio visibile" se almeno una normale e' confrontabile e nessuna differenza;
      - se NESSUNA normale e' confrontabile e non ci sono altre differenze: "non confrontabile" (manca un lato)
        oppure "errore di rendering" (i template ci sono ma non si renderizzano)."""
    if oscurato:
        return "oscurato (nessun effetto)", []
    conf = [n for n in NORMALI if confrontabile(rr, n)]
    diverse = [n for n in conf if rr[n]["prima"]["ok"] != rr[n]["dopo"]["ok"]]
    if confrontabile(rr, "C5") and rr["C5"]["prima"]["ok"] != rr["C5"]["dopo"]["ok"]:
        diverse_c5 = ["C5"]
    else:
        diverse_c5 = []
    if diverse:
        return "uso normale", diverse + diverse_c5
    if diverse_c5:
        return "solo con strumenti", diverse_c5
    if conf:
        return "nessun cambio visibile", []
    manca = any("manca" in rr[n][l] for n in NORMALI for l in ("prima", "dopo"))
    return ("non confrontabile" if manca else "errore di rendering"), []


def riassumi(path, dest_classi=None):
    with open(path, encoding="utf-8") as f:
        ris = json.load(f)
    print("=== REGOLE LORO (file per file), strumento povero (come l'altra sessione) ===")
    unita = [(r, u["file"], classe_loro(u["r"])) for r in ris for u in r["loro_povero"]]
    print("unita':", len(unita), dict(Counter(c for _, _, (c, _) in unita)))
    um = {r["repo"] for r, _, (c, _) in unita if c == "uso normale"}
    um7 = {r["repo"] for r, _, (c, _) in unita if c == "uso normale" and round(r["giorni"], 1) > 7}
    print("modelli uso normale:", len(um), "| oltre 7 giorni:", len(um7))
    print("=== REGOLE LORO, strumento completo ===")
    unita2 = [(r, u["file"], classe_loro(u["r"])) for r in ris for u in r["loro_completo"]]
    print("unita':", len(unita2), dict(Counter(c for _, _, (c, _) in unita2)))
    schede = {}
    for var in ("povero", "completo"):
        print(f"=== REGOLE CORRETTE, strumento {var} ===")
        vecchie = [(r, classe_corretta_20_10(r["corrette_" + var], r["oscurato"])) for r in ris]
        nuove = [(r, classe_corretta(r["corrette_" + var], r["oscurato"])) for r in ris]
        for nome, cl in (("20/10 (solo C1)", vecchie), ("21/10 (alla lettera)", nuove)):
            um = {r["repo"] for r, (c, _) in cl if c == "uso normale"}
            um7 = {r["repo"] for r, (c, _) in cl if c == "uso normale" and r["giorni"] > 7}
            print(f"  {nome}: {len(cl)} cambi {dict(Counter(c for _, (c, _) in cl))}")
            print(f"     modelli uso normale {len(um)} | oltre 7 giorni {len(um7)} | grandi {sum(1 for m in um if grande(m))}")
        passano = [(r, v[0], n[0]) for (r, v), (_, n) in zip(vecchie, nuove) if v[0] != n[0]]
        print(f"  cambi che passano di classe: {len(passano)}")
        for r, v, n in passano:
            rr = r["corrette_" + var]
            print(f"     {r['repo']} {r['commit'][:8]} {v} -> {n}"
                  f" | normali confrontabili: {[x for x in NORMALI if confrontabile(rr, x)]}"
                  f" | prima: {[ (x, 'ok' if 'ok' in rr[x]['prima'] else ('manca' if 'manca' in rr[x]['prima'] else 'ERR')) for x in NORMALI]}"
                  f" | dopo: {[ (x, 'ok' if 'ok' in rr[x]['dopo'] else ('manca' if 'manca' in rr[x]['dopo'] else 'ERR')) for x in NORMALI]}")
        schede[var] = [{"repo": r["repo"], "commit": r["commit"], "giorni": r["giorni"], "classe": n[0],
                        "classe_20_10": v[0], "diverse": n[1]} for (r, v), (_, n) in zip(vecchie, nuove)]
        # informazione: errore su un solo lato in una normale (non confrontabile ma potenzialmente un cambio vero)
        asimm = [(r["repo"], r["commit"][:8], x) for r in ris for x in NORMALI
                 if ("errore" in r["corrette_" + var][x]["prima"]) != ("errore" in r["corrette_" + var][x]["dopo"])
                 and "manca" not in r["corrette_" + var][x]["prima"] and "manca" not in r["corrette_" + var][x]["dopo"]]
        print(f"  info: conversazioni normali con errore su UN SOLO lato (escluse dal confronto): {len(asimm)} in "
              f"{len({(a, b) for a, b, _ in asimm})} cambi: {sorted({(a, b) for a, b, _ in asimm})}")
    if dest_classi:
        with open(dest_classi, "w", encoding="utf-8") as f:
            json.dump(schede["completo"], f, indent=1, ensure_ascii=False)
    return ris


if __name__ == "__main__":
    if sys.argv[1] == "renderizza":
        renderizza(sys.argv[2], sys.argv[3], sys.argv[4] if len(sys.argv) > 4 else None)
    else:
        riassumi(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
