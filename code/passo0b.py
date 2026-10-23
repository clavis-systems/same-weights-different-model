"""Passo 0b di "stessi pesi, modello diverso": COSA cambia nei file di comportamento.

  stima     solo metadati: per ogni cambio di un file primario a pesi identici trovato dal censimento elenca le due
            versioni (prima/dopo) e la loro dimensione. Non scarica contenuti.
  scarica   scarica SOLO i file elencati da `stima` (serve l'OK esplicito dell'utente). I file sono dati non fidati:
            vengono letti come testo/JSON, mai eseguiti.
  classifica confronta prima/dopo: chiavi JSON cambiate (template, token di fine, parametri di campionamento) e
            separa i cambi di comportamento da quelli innocui.

Uso:
  python -I -X utf8 passo0b.py stima CARTELLA_CORSA
  python -I -X utf8 passo0b.py scarica CARTELLA_CORSA --ok-utente
  python -I -X utf8 passo0b.py classifica CARTELLA_CORSA
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import censimento as c

# Chiavi che cambiano il comportamento del modello a pesi identici (le altre sono considerate innocue).
CHIAVI_COMPORTAMENTO = {
    "chat_template", "eos_token", "bos_token", "pad_token", "unk_token", "additional_special_tokens",
    "added_tokens_decoder", "add_bos_token", "add_eos_token", "eos_token_id", "bos_token_id", "pad_token_id",
    "temperature", "top_p", "top_k", "min_p", "repetition_penalty", "do_sample", "max_new_tokens", "max_length",
    "presence_penalty", "frequency_penalty", "typical_p", "no_repeat_ngram_size",
}


def cambi_a_pesi_identici(cartella):
    for riga in (Path(cartella) / "modelli.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(riga)
        for cb in r.get("cambi", []):
            if cb["primari"] and not cb["pesi_cambiati"]:
                yield r["repo"], cb


def stima(args):
    cartella = Path(args.cartella)
    voci, totale = [], 0
    for repo, cb in cambi_a_pesi_identici(cartella):
        rq = urllib.parse.quote(repo, safe="/")
        commit = c.tutte_le_pagine(f"{c.API}/models/{rq}/commits/main")[::-1]
        ids = [x["id"] for x in commit]
        if cb["commit"] not in ids or ids.index(cb["commit"]) == 0:
            voci.append({"repo": repo, "dopo": cb["commit"], "problema": "commit non ritrovato"})
            continue
        prima = ids[ids.index(cb["commit"]) - 1]
        dim = {}
        for sha in (prima, cb["commit"]):
            for v in c.tutte_le_pagine(f"{c.API}/models/{rq}/tree/{sha}"):
                if v.get("path") in cb["primari"]:
                    dim[(sha, v["path"])] = v.get("size", 0)
        for f in cb["primari"]:
            a, b = dim.get((prima, f)), dim.get((cb["commit"], f))
            totale += (a or 0) + (b or 0)
            voci.append({"repo": repo, "file": f, "prima": prima, "dopo": cb["commit"], "data": cb["data"],
                         "byte_prima": a, "byte_dopo": b})
    piano = {"n_file_versioni": sum((v.get("byte_prima") is not None) + (v.get("byte_dopo") is not None)
                                    for v in voci),
             "byte_totali": totale, "voci": voci}
    (cartella / "piano_0b.json").write_text(json.dumps(piano, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(voci)} cambi di file, {piano['n_file_versioni']} versioni da scaricare, "
          f"{totale / 1e6:.2f} MB in tutto -> {cartella / 'piano_0b.json'}")


def scarica(args):
    if not args.ok_utente:
        sys.exit("Serve --ok-utente: lo scaricamento richiede l'OK esplicito dell'utente.")
    cartella = Path(args.cartella)
    piano = json.loads((cartella / "piano_0b.json").read_text(encoding="utf-8"))
    dest = cartella / "file0b"
    for v in piano["voci"]:
        for chiave, sha in (("byte_prima", v.get("prima")), ("byte_dopo", v.get("dopo"))):
            if v.get(chiave) is None or sha is None:
                continue
            out = dest / v["repo"].replace("/", "__") / sha / v["file"]
            if out.exists():
                continue
            out.parent.mkdir(parents=True, exist_ok=True)
            url = (f"https://huggingface.co/{urllib.parse.quote(v['repo'], safe='/')}/resolve/{sha}/"
                   f"{urllib.parse.quote(v['file'])}")
            req = urllib.request.Request(url, headers={"User-Agent": "censimento-stessi-pesi/0.1"})
            with urllib.request.urlopen(req, timeout=60) as r:
                out.write_bytes(r.read(5_000_000))
            time.sleep(c.PAUSA)
    print(f"scaricati in {dest}")


def chiavi_cambiate(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def leggi(percorso):
    if percorso is None or not percorso.exists():
        return None
    testo = percorso.read_text(encoding="utf-8", errors="replace")
    if percorso.suffix == ".json":
        try:
            dati = json.loads(testo)
            return dati if isinstance(dati, dict) else {"_valore": dati}
        except json.JSONDecodeError:
            return {"_testo": testo}
    return {"chat_template": testo}  # .jinja


def classifica(args):
    cartella = Path(args.cartella)
    piano = json.loads((cartella / "piano_0b.json").read_text(encoding="utf-8"))
    dest = cartella / "file0b"
    righe = []
    for v in piano["voci"]:
        if "file" not in v:
            continue
        base = dest / v["repo"].replace("/", "__")
        a = leggi(base / v["prima"] / v["file"]) if v.get("byte_prima") is not None else {}
        b = leggi(base / v["dopo"] / v["file"]) if v.get("byte_dopo") is not None else {}
        if a is None or b is None:
            righe.append({**v, "classe": "non scaricato"})
            continue
        k = chiavi_cambiate(a, b)
        comp = [x for x in k if x in CHIAVI_COMPORTAMENTO]
        righe.append({**v, "chiavi_cambiate": k, "chiavi_comportamento": comp,
                      "classe": "comportamento" if comp else "innocuo"})
    (cartella / "classificazione_0b.json").write_text(json.dumps(righe, indent=1, ensure_ascii=False),
                                                     encoding="utf-8")
    n = sum(r["classe"] == "comportamento" for r in righe)
    print(f"{n} cambi di comportamento su {len(righe)} cambi di file")


def main(argv=None):
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    for nome in ("stima", "scarica", "classifica"):
        q = s.add_parser(nome)
        q.add_argument("cartella")
        if nome == "scarica":
            q.add_argument("--ok-utente", action="store_true")
    args = p.parse_args(argv)
    {"stima": stima, "scarica": scarica, "classifica": classifica}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
