"""Ricalcolo indipendente del passo 0c: i cambi di template di chat cambiano il testo che il modello riceve?

Due fasi:
  python -I ricalcolo_0c.py prepara <cartella corsa1> <lavori.json>
      costruisce, per ogni (modello, commit) con un cambio di template, il template "di prima" e "di dopo"
      (precedenza di transformers 5: chat_template.jinja > chiave chat_template di tokenizer_config.json;
      chat_template.json e' il formato legacy dei processor, usato solo se manca il resto)
  python -I ricalcolo_0c.py renderizza <lavori.json> <risultati.json>
      renderizza con transformers.utils.chat_template_utils.render_jinja_template (sandbox Jinja ufficiale)
      cinque conversazioni fisse. Va lanciato con l'interprete dell'ambiente che ha transformers 5.5.4.
  python -I ricalcolo_0c.py riassumi <cartella corsa1> <lavori.json> <risultati.json> [<oscurati.json> [<classi.json>]]
I template sono DATI NON FIDATI: vengono solo letti come testo e passati al sandbox Jinja di transformers.
"""
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
          "HuggingFaceTB", "allenai", "ibm-granite"]

UTENTE = "Hello, how are you?"
SISTEMA = "You are a helpful assistant."
STRUMENTO = {"type": "function", "function": {
    "name": "get_weather", "description": "Get the current weather for a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string", "description": "City name"}},
                   "required": ["city"]}}}
CONVERSAZIONI = {
    "C1": dict(messages=[{"role": "user", "content": UTENTE}], tools=None, gen=True),
    "C2": dict(messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": UTENTE}],
               tools=None, gen=True),
    "C3": dict(messages=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello! How can I help?"},
                         {"role": "user", "content": "Name a European capital."}], tools=None, gen=True),
    "C4": dict(messages=[{"role": "system", "content": SISTEMA}, {"role": "user", "content": UTENTE},
                         {"role": "assistant", "content": "I am fine, thank you."}], tools=None, gen=False),
    "C5": dict(messages=[{"role": "user", "content": "What is the weather in Rome?"}], tools=[STRUMENTO], gen=True),
}


def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def leggi(cartella, voce, lato):
    if voce["byte_" + lato] is None:
        return None
    p = f"{cartella}/file0b/{voce['repo'].replace('/', '__')}/{voce[lato]}/{voce['file']}"
    with open(p, "rb") as f:
        return f.read().decode("utf-8")


def sorgente_tc(testo):
    """chat_template da un tokenizer_config.json: (stato, valore). stato: ok / assente_file / illeggibile"""
    if testo is None:
        return "assente_file", None
    try:
        j = json.loads(testo)
        v = j.get("chat_template")
    except Exception:
        return "illeggibile", None
    if isinstance(v, list):        # [{"name": "...", "template": "..."}]
        d = {x.get("name"): x.get("template") for x in v if isinstance(x, dict)}
        v = d.get("default", next(iter(d.values()), None))
    elif isinstance(v, dict):
        v = v.get("default", next(iter(v.values()), None))
    return "ok", v


def sorgente_cj(testo):
    if testo is None:
        return "assente_file", None
    try:
        v = json.loads(testo).get("chat_template")
    except Exception:
        return "illeggibile", None
    if isinstance(v, list):
        d = {x.get("name"): x.get("template") for x in v if isinstance(x, dict)}
        v = d.get("default", next(iter(d.values()), None))
    return "ok", v


def prepara(cartella, dest):
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        rows = {r["repo"]: r for r in map(json.loads, f)}
    with open(cartella + "/piano_0b.json", encoding="utf-8") as f:
        piano = json.load(f)["voci"]
    gruppi = defaultdict(dict)
    for v in piano:
        gruppi[(v["repo"], v["dopo"])][v["file"]] = v
    lavori = []
    for (repo, commit), files in gruppi.items():
        sorg = {}   # nome -> (stato_prima, valore_prima, stato_dopo, valore_dopo)
        if "chat_template.jinja" in files:
            v = files["chat_template.jinja"]
            sorg["jinja"] = (leggi(cartella, v, "prima"), leggi(cartella, v, "dopo"))
        if "chat_template.json" in files:
            v = files["chat_template.json"]
            sp, vp = sorgente_cj(leggi(cartella, v, "prima"))
            sd, vd = sorgente_cj(leggi(cartella, v, "dopo"))
            sorg["json"] = (vp, vd, sp, sd)
        if "tokenizer_config.json" in files:
            v = files["tokenizer_config.json"]
            sp, vp = sorgente_tc(leggi(cartella, v, "prima"))
            sd, vd = sorgente_tc(leggi(cartella, v, "dopo"))
            sorg["tc"] = (vp, vd, sp, sd)
        # c'e' un cambio di template in questo commit?
        cambia = False
        if "jinja" in sorg and sorg["jinja"][0] != sorg["jinja"][1]:
            cambia = True
        if "json" in sorg and sorg["json"][0] != sorg["json"][1]:
            cambia = True
        if "tc" in sorg and (sorg["tc"][0] != sorg["tc"][1] or "illeggibile" in (sorg["tc"][2], sorg["tc"][3])):
            cambia = True
        if not cambia:
            continue
        data = next(iter(files.values()))["data"]
        rel = rows[repo]["rilascio"]["data"]
        giorni = (t(data) - t(rel)).total_seconds() / 86400
        # template effettivo prima/dopo, con la precedenza di transformers
        def effettivo(lato):
            """lato 0=prima, 1=dopo. restituisce (testo|None, nota)"""
            if "jinja" in sorg:
                if sorg["jinja"][lato] is not None:
                    return sorg["jinja"][lato], "jinja"
                # jinja assente in questo lato: vale il resto (se noto)
            if "json" in sorg and sorg["json"][lato] is not None:
                return sorg["json"][lato], "json"
            if "tc" in sorg:
                st = sorg["tc"][2 + lato]
                if st == "illeggibile":
                    return None, "illeggibile"
                if sorg["tc"][lato] is not None:
                    return sorg["tc"][lato], "tc"
            return None, "ignoto"
        tp, np_ = effettivo(0)
        td, nd = effettivo(1)
        # quali sorgenti NON abbiamo (non sono state scaricate perche' non cambiate)?
        note = []
        if "jinja" not in sorg:
            note.append("jinja_non_scaricato")
        if "tc" not in sorg:
            note.append("tc_non_scaricato")
        lavori.append({"repo": repo, "commit": commit, "data": data, "giorni": giorni, "file": sorted(files),
                       "sorgenti": sorted(sorg), "prima": tp, "dopo": td, "origine_prima": np_,
                       "origine_dopo": nd, "note": note})
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(lavori, f, ensure_ascii=False, indent=1)
    print("gruppi (modello,commit) con un cambio di template:", len(lavori))
    print("unita' per file:", sum(len(l["sorgenti"]) for l in lavori))


def renderizza(lavori_path, dest):
    # import tardivo: serve l'ambiente con transformers
    from transformers.utils.chat_template_utils import render_jinja_template
    with open(lavori_path, encoding="utf-8") as f:
        lavori = json.load(f)
    comuni = dict(bos_token="<s>", eos_token="</s>", unk_token="<unk>", pad_token="<pad>")

    def rendi(template, conv):
        try:
            out, _ = render_jinja_template([conv["messages"]], tools=conv["tools"], chat_template=template,
                                           add_generation_prompt=conv["gen"], **comuni)
            return {"ok": out[0]}
        except Exception as e:
            return {"errore": type(e).__name__ + ": " + str(e)[:200]}

    risultati = []
    for i, l in enumerate(lavori):
        r = {"i": i, "prima": {}, "dopo": {}}
        for lato in ("prima", "dopo"):
            tpl = l[lato]
            for nome, conv in CONVERSAZIONI.items():
                r[lato][nome] = None if tpl is None else rendi(tpl, conv)
        risultati.append(r)
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(risultati, f, ensure_ascii=False, indent=1)
    print("renderizzati", len(risultati))


def confronta(r):
    """classe di un lavoro, dal solo risultato dei rendering"""
    p, d = r["prima"], r["dopo"]
    if p["C1"] is None or d["C1"] is None:
        return "non confrontabile", {}
    diff = {}
    for nome in CONVERSAZIONI:
        a, b = p[nome], d[nome]
        diff[nome] = (a != b)    # stringhe diverse, oppure una sola con errore, oppure errori diversi
    tutti_errori = all(("errore" in p[n] and "errore" in d[n]) for n in ("C1", "C2", "C3", "C4"))
    if tutti_errori:
        return "errore di rendering", diff
    if any(diff[n] for n in ("C1", "C2", "C3", "C4")):
        return "uso normale", diff
    if diff["C5"]:
        return "solo con strumenti", diff
    return "nessun cambio visibile", diff


def grande(repo):
    return repo.split("/")[0] in GRANDI


def motivo_non_confrontabile(l, r):
    out = []
    for lato in ("prima", "dopo"):
        if r[lato]["C1"] is None:
            out.append(f"{lato}: {l['origine_' + lato]}")
    return "; ".join(out)


def riassumi(cartella, lavori_path, ris_path, oscurati_path=None, dest=None):
    with open(lavori_path, encoding="utf-8") as f:
        lavori = json.load(f)
    with open(ris_path, encoding="utf-8") as f:
        ris = json.load(f)
    oscurati = {}
    if oscurati_path:
        with open(oscurati_path, encoding="utf-8") as f:
            oscurati = json.load(f)
    schede = []
    for l, r in zip(lavori, ris):
        c, diff = confronta(r)
        chiave = f"{l['repo']}@{l['commit']}"
        c_eff = c
        if oscurati.get(chiave) == "oscurato" and c in ("uso normale", "solo con strumenti"):
            c_eff = "nessun cambio effettivo (oscurato)"
        schede.append({"repo": l["repo"], "commit": l["commit"], "giorni": l["giorni"], "sorgenti": l["sorgenti"],
                       "classe_grezza": c, "classe": c_eff, "diff": diff,
                       "motivo_nc": motivo_non_confrontabile(l, r) if c == "non confrontabile" else ""})
    print("cambi (modello,commit):", len(schede))
    print("classi grezze :", dict(Counter(s["classe_grezza"] for s in schede)))
    print("classi con oscuramento:", dict(Counter(s["classe"] for s in schede)))
    print("motivi non confrontabile:", dict(Counter(s["motivo_nc"] for s in schede if s["motivo_nc"])))
    for nome, chiave in (("grezza", "classe_grezza"), ("con oscuramento", "classe")):
        um = [s for s in schede if s[chiave] == "uso normale"]
        modelli_um = {s["repo"] for s in um}
        modelli_7 = {s["repo"] for s in um if s["giorni"] > 7}
        print(f"[{nome}] modelli con cambio d'uso normale: {len(modelli_um)} | oltre 7 giorni: {len(modelli_7)} | "
              f"grandi: {sum(1 for m in modelli_um if grande(m))}")
    if dest:
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(schede, f, indent=1, ensure_ascii=False)
    return schede


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "prepara":
        prepara(sys.argv[2], sys.argv[3])
    elif cmd == "renderizza":
        renderizza(sys.argv[2], sys.argv[3])
    elif cmd == "riassumi":
        riassumi(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else None,
                 sys.argv[6] if len(sys.argv) > 6 else None)
