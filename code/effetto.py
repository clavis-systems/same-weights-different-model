"""Passo 1 di "stessi pesi, modello diverso": effetto sui punteggi del template di prima e di dopo, pesi identici.

Definizioni e ipotesi in PREMESSA.md (aggiunta "passo 1"). Usa i file di comportamento gia' scaricati (passo 0b),
i pesi locali in esterni/modelli e GSM8K test in esterni/gsm8k.

Uso (ambiente con torch + transformers):
  python -I -X utf8 effetto.py pesi CORSA                     # verifica sha256 locali = oid LFS prima e dopo
  python -I -X utf8 effetto.py genera CORSA CASO CONDIZIONE --out DIR [--limite N]
        CASO in A, B, C; CONDIZIONE in prima, dopo, controllo
  python -I -X utf8 effetto.py analizza DIR
"""
import argparse
import hashlib
import json
import math
import os
import random
import re
import sys
import time
import urllib.parse
from datetime import datetime
from pathlib import Path

import censimento as c
from passo0c import template_da

RADICE = Path(r"C:/Users/emari/Desktop/MIA IA LOCALE")
LUCCHETTO = RADICE / "strumenti/risultati/.gpu_lock"
GSM8K = RADICE / "esterni/gsm8k/main/test-00000-of-00001.parquet"
ISTRUZIONE = "\nPlease reason step by step, and put your final answer within \\boxed{}."
CASI = {
    "A": {"repo": "Qwen/Qwen2.5-0.5B-Instruct", "data": "2024-09-18", "max_nuovi": 1024,
          "locale": RADICE / "esterni/modelli/Qwen2.5-0.5B-Instruct"},
    "B": {"repo": "Qwen/Qwen2.5-1.5B-Instruct", "data": "2024-09-18", "max_nuovi": 1024,
          "locale": RADICE / "esterni/modelli/Qwen2.5-1.5B-Instruct"},
    "C": {"repo": "deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B", "data": "2025-02-09", "max_nuovi": 2048,
          "locale": RADICE / "esterni/modelli/DeepSeek-R1-Distill-Qwen-1.5B"},
}
LOTTO = 32


def cambio(corsa, caso):
    """Il cambio di tokenizer_config.json del caso, dal passo 0b: commit di prima e di dopo."""
    cfg = CASI[caso]
    righe = json.loads((Path(corsa) / "classificazione_0b.json").read_text(encoding="utf-8"))
    trovati = [r for r in righe if r["repo"] == cfg["repo"] and r["file"] == "tokenizer_config.json"
               and r["data"].startswith(cfg["data"]) and "chat_template" in r.get("chiavi_comportamento", [])]
    if len(trovati) != 1:
        sys.exit(f"cambio non univoco per {caso}: {len(trovati)}")
    return trovati[0]


def templates(corsa, caso):
    r = cambio(corsa, caso)
    base = Path(corsa) / "file0b" / r["repo"].replace("/", "__")
    return {"prima": template_da(base / r["prima"] / r["file"]), "dopo": template_da(base / r["dopo"] / r["file"])}, r


def sha256(percorso):
    h = hashlib.sha256()
    with open(percorso, "rb") as f:
        for blocco in iter(lambda: f.read(1 << 22), b""):
            h.update(blocco)
    return h.hexdigest()


def pesi(args):
    esito = {}
    for caso, cfg in CASI.items():
        r = cambio(args.corsa, caso)
        rq = urllib.parse.quote(cfg["repo"], safe="/")
        locali = {p.name: sha256(p) for p in sorted(cfg["locale"].glob("*.safetensors"))}
        remoti = {}
        for sha in (r["prima"], r["dopo"]):
            remoti[sha] = {v["path"]: (v.get("lfs") or {}).get("oid") for v in
                           c.tutte_le_pagine(f"{c.API}/models/{rq}/tree/{sha}") if v["path"].endswith(".safetensors")}
        uguali = bool(locali) and all(remoti[s] == locali for s in remoti)
        esito[caso] = {"repo": cfg["repo"], "locali": locali, "remoti": remoti, "identici": uguali}
        print(caso, cfg["repo"], "pesi identici prima/dopo/locali:", uguali)
    Path(args.corsa, "verifica_pesi.json").write_text(json.dumps(esito, indent=1), encoding="utf-8")


def problemi(limite=None):
    import pyarrow.parquet as pq
    t = pq.read_table(GSM8K).to_pylist()
    out = [{"i": i, "domanda": x["question"], "oro": x["answer"].split("####")[-1].strip().replace(",", "")}
           for i, x in enumerate(t)]
    return out[:limite] if limite else out


class Lucchetto:
    def __init__(self, attivita):
        self.testo = f"Claude | {attivita} (sessione procedural-maps) | {datetime.now():%d/%m %H:%M} | {os.getpid()}"

    def __enter__(self):
        if LUCCHETTO.exists():
            sys.exit(f"GPU occupata: {LUCCHETTO.read_text(encoding='utf-8', errors='replace').strip()}")
        LUCCHETTO.write_text(self.testo, encoding="utf-8")
        return self

    def __exit__(self, *a):
        if LUCCHETTO.exists() and LUCCHETTO.read_text(encoding="utf-8", errors="replace").strip() == self.testo:
            LUCCHETTO.unlink()


def genera(args):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    from transformers.utils.chat_template_utils import render_jinja_template
    cfg = CASI[args.caso]
    tpl, _ = templates(args.corsa, args.caso)
    template = tpl["dopo" if args.condizione == "dopo" else "prima"]
    probs = problemi(args.limite)
    if args.condizione == "controllo":
        random.Random(1).shuffle(probs)
    out = Path(args.out) / f"{args.caso}_{args.condizione}.jsonl"
    out.parent.mkdir(parents=True, exist_ok=True)
    fatti = set()
    if out.exists():
        fatti = {json.loads(l)["i"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()}
    probs = [p for p in probs if p["i"] not in fatti]
    tok = AutoTokenizer.from_pretrained(cfg["locale"])
    tok.padding_side = "left"
    if tok.pad_token is None:
        tok.pad_token = tok.eos_token
    testi = {}
    for p in probs:
        s, _ = render_jinja_template(conversations=[[{"role": "user", "content": p["domanda"] + ISTRUZIONE}]],
                                     chat_template=template, add_generation_prompt=True,
                                     bos_token=tok.bos_token or "", eos_token=tok.eos_token or "")
        testi[p["i"]] = s[0]
    with Lucchetto(f"stessi pesi passo 1 {args.caso} {args.condizione}"):
        model = AutoModelForCausalLM.from_pretrained(cfg["locale"], dtype=torch.bfloat16, device_map="cuda")
        model.eval()
        t0 = time.time()
        with out.open("a", encoding="utf-8") as fh:
            for k in range(0, len(probs), args.lotto):
                lotto = probs[k:k + args.lotto]
                enc = tok([testi[p["i"]] for p in lotto], return_tensors="pt", padding=True,
                          add_special_tokens=False).to("cuda")
                extra = {"cache_implementation": "static", "disable_compile": True} if args.cache_statica else {}
                with torch.no_grad():
                    gen = model.generate(**enc, max_new_tokens=cfg["max_nuovi"], do_sample=False, temperature=None,
                                         top_p=None, top_k=None, pad_token_id=tok.pad_token_id, **extra)
                nuovi = gen[:, enc["input_ids"].shape[1]:]
                for p, seq in zip(lotto, nuovi):
                    ids = [t for t in seq.tolist() if t != tok.pad_token_id]
                    risposta = tok.decode(ids, skip_special_tokens=True)
                    fh.write(json.dumps({"i": p["i"], "oro": p["oro"], "risposta": risposta, "n_token": len(ids),
                                         "troncata": len(ids) >= cfg["max_nuovi"]}, ensure_ascii=False) + "\n")
                fh.flush()
                del gen, nuovi, enc
                torch.cuda.empty_cache()
                fatti_ora = k + len(lotto)
                stima = (time.time() - t0) / fatti_ora * (len(probs) - fatti_ora)
                print(f"{args.caso} {args.condizione}: {fatti_ora}/{len(probs)}, mancano ~{stima / 60:.0f} min",
                      flush=True)


def estrai(testo):
    scatole = re.findall(r"\\boxed\{((?:[^{}]|\{[^{}]*\})*)\}", testo)
    s = scatole[-1] if scatole else None
    if s is None:
        numeri = re.findall(r"-?\d[\d,]*(?:\.\d+)?", testo)
        s = numeri[-1] if numeri else None
    if s is None:
        return None
    s = s.replace(",", "").replace("$", "").replace("\\%", "").replace("%", "").strip().rstrip(".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return float(m.group()) if m else None


def giusta(riga):
    v = estrai(riga["risposta"])
    try:
        return v is not None and abs(v - float(riga["oro"])) < 1e-6
    except ValueError:
        return False


def pensiero_vuoto(testo):
    """Il ragionamento fra <think> e </think> e' vuoto (meno di 20 caratteri)."""
    if "</think>" not in testo:
        return False
    prima = testo.split("</think>")[0].replace("<think>", "")
    return len(prima.strip()) < 20


def mcnemar(b, c_):
    """McNemar esatto bilaterale sulle coppie discordanti."""
    n = b + c_
    if n == 0:
        return 1.0
    k = min(b, c_)
    coda = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * coda)


def analizza(args):
    d = Path(args.dir)
    ris, pv = {}, {}
    for caso in CASI:
        corse = {}
        for cond in ("prima", "dopo", "controllo"):
            f = d / f"{caso}_{cond}.jsonl"
            if f.exists():
                corse[cond] = {json.loads(l)["i"]: json.loads(l) for l in f.read_text(encoding="utf-8").splitlines()
                               if l.strip()}
        if "prima" not in corse or "dopo" not in corse:
            continue
        comuni = sorted(set(corse["prima"]) & set(corse["dopo"]) & set(corse.get("controllo", corse["prima"])))
        acc = {k: sum(giusta(v[i]) for i in comuni) / len(comuni) for k, v in corse.items()}

        def conf(x, y):
            b = sum(giusta(corse[x][i]) and not giusta(corse[y][i]) for i in comuni)
            c_ = sum(not giusta(corse[x][i]) and giusta(corse[y][i]) for i in comuni)
            return b, c_, mcnemar(b, c_)

        b, c_, p = conf("prima", "dopo")
        r = {"n": len(comuni), "accuratezza": {k: round(v, 4) for k, v in acc.items()},
             "prima_giusta_dopo_sbagliata": b, "prima_sbagliata_dopo_giusta": c_, "p_mcnemar": p}
        if "controllo" in corse:
            bc, cc, pc = conf("prima", "controllo")
            r["controllo"] = {"prima_giusta_controllo_sbagliata": bc, "prima_sbagliata_controllo_giusta": cc,
                              "p_mcnemar": pc, "significativo": pc < 0.05}
        r["descrittive"] = {k: {"token_medi": round(sum(v[i]["n_token"] for i in comuni) / len(comuni), 1),
                                "troncate": sum(v[i]["troncata"] for i in comuni),
                                "senza_boxed": sum("\\boxed" not in v[i]["risposta"] for i in comuni),
                                "ragionamento_vuoto": sum(pensiero_vuoto(v[i]["risposta"]) for i in comuni)}
                            for k, v in corse.items()}
        ris[caso] = r
        pv[caso] = p
    # Holm sui casi presenti
    ordine = sorted(pv, key=pv.get)
    for j, caso in enumerate(ordine):
        ris[caso]["p_holm"] = min(1.0, max(pv[k] * (len(ordine) - i) for i, k in enumerate(ordine[:j + 1])))
        ctrl_ok = not ris[caso].get("controllo", {}).get("significativo", False)
        ris[caso]["verdetto"] = ("non interpretabile (controllo significativo)" if not ctrl_ok else
                                 "effetto del template" if ris[caso]["p_holm"] < 0.05 else "nessun effetto dimostrato")
    print(json.dumps(ris, indent=1, ensure_ascii=False))
    (d / "analisi.json").write_text(json.dumps(ris, indent=1, ensure_ascii=False), encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    q = s.add_parser("pesi")
    q.add_argument("corsa")
    g = s.add_parser("genera")
    g.add_argument("corsa")
    g.add_argument("caso", choices=list(CASI))
    g.add_argument("condizione", choices=["prima", "dopo", "controllo"])
    g.add_argument("--out", required=True)
    g.add_argument("--limite", type=int)
    g.add_argument("--lotto", type=int, default=LOTTO, help="dimensione dei gruppi (deviazione 1: 16 per il caso C)")
    g.add_argument("--cache-statica", action="store_true", help="cache KV preallocata (deviazione 1b, caso C)")
    a = s.add_parser("analizza")
    a.add_argument("dir")
    args = p.parse_args(argv)
    {"pesi": pesi, "genera": genera, "analizza": analizza}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
