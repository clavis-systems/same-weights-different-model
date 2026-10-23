"""Quanto regge "a pesi identici"? Analisi sulla raccolta completa (cache di ricalcolo_campione.py).

Per ogni cambio di file primario con pesi uguali al commit precedente (la definizione della premessa) si chiede anche:
 (a) i pesi sono uguali a quelli del RILASCIO (mappa dei file di pesi identica)?
 (b) i file di pesi presenti al rilascio sono tutti ancora presenti e con la stessa impronta (si ammettono file
     AGGIUNTI, come nei repository GGUF che aggiungono quantizzazioni)?
 (c) c'e' stata una SOSTITUZIONE (stesso nome di file, impronta diversa) fra il rilascio e il cambio?
Inoltre ricalcola il rilascio escludendo i file che non sono pesi (training_args.bin, optimizer.pt, lfstest.bin...).
Uso: python -I ricalcolo_pesi.py <cartella corsa1> <cache>
"""
import json
import os
import sys
from datetime import datetime, timezone

GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
          "HuggingFaceTB", "allenai", "ibm-granite"]
PRIMARI = ["tokenizer_config.json", "chat_template.jinja", "chat_template.json", "generation_config.json",
           "special_tokens_map.json"]
ESTENSIONI = (".safetensors", ".bin", ".gguf", ".pt", ".pth")
NON_PESI = ("training_args.bin", "optimizer.pt", "scheduler.pt", "rng_state.pth", "lfstest.bin", "trainer_state.bin")


def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def pesi(albero, filtro=False):
    return {k: v for k, v in albero.items() if k.endswith(ESTENSIONI) and not (filtro and k in NON_PESI)}


def main():
    cartella, cache = sys.argv[1], sys.argv[2]
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        rows = {r["repo"]: r for r in map(json.loads, f)}
    an = sorted(r for r, x in rows.items() if "cambi" in x and x["rilascio"])
    contatori = {k: [] for k in ("M1", "M1b", "a_uguale_rilascio", "b_rilascio_invariato", "c_sostituzione")}
    per_modello = {}
    for repo in an:
        with open(os.path.join(cache, repo.replace("/", "__") + ".json"), encoding="utf-8") as f:
            c = json.load(f)
        commits, alberi = c["commit"], c["alberi"]
        rel = next((i for i, a in enumerate(alberi) if pesi(a)), None)
        if rel is None:
            continue
        pr = pesi(alberi[rel])
        ok = {"M1": False, "M1b": False, "a": False, "a_b7": False, "b": False, "b_b7": False,
              "sostituzione_prima_di_un_cambio": False}
        for i in range(rel + 1, len(commits)):
            a, b = alberi[i - 1], alberi[i]
            if not [f for f in PRIMARI if a.get(f) != b.get(f)]:
                continue
            if pesi(a) != pesi(b):
                continue
            g = (t(commits[i]["data"]) - t(commits[rel]["data"])).total_seconds() / 86400
            pb = pesi(b)
            ok["M1"] = True
            ok["M1b"] |= g > 7
            uguale = pb == pr
            invariato = all(pb.get(n) == v for n, v in pr.items())
            sostituito = any(n in pb and pb[n] != v for n, v in pr.items())
            ok["a"] |= uguale
            ok["a_b7"] |= uguale and g > 7
            ok["b"] |= invariato
            ok["b_b7"] |= invariato and g > 7
            ok["sostituzione_prima_di_un_cambio"] |= sostituito
        per_modello[repo] = ok

    def riga(nome, ins):
        n = len(ins)
        def c(k):
            return sum(1 for r in ins if per_modello.get(r, {}).get(k))
        print(f"{nome:14s} n={n:3d} | M1 {c('M1'):3d} ({100 * c('M1') / n:4.1f}%) M1b {c('M1b'):3d} ({100 * c('M1b') / n:4.1f}%)"
              f" | (a) mappa pesi = rilascio: {c('a'):3d} ({100 * c('a') / n:4.1f}%) oltre 7 g {c('a_b7'):3d}"
              f" | (b) file del rilascio invariati: {c('b'):3d} ({100 * c('b') / n:4.1f}%) oltre 7 g {c('b_b7'):3d}")

    riga("tutti", an)
    riga("grandi", [r for r in an if r.split("/")[0] in GRANDI])
    print("modelli con M1 ma nessun cambio a file-di-rilascio-invariati:",
          sorted(r for r, v in per_modello.items() if v["M1"] and not v["b"]))
    print("modelli con un file di pesi SOSTITUITO (stesso nome, impronta diversa) prima di un cambio di config:",
          sorted(r for r, v in per_modello.items() if v["sostituzione_prima_di_un_cambio"]))
    # rilascio senza i file che non sono pesi
    print("--- rilascio ricalcolato senza training_args.bin & co ---")
    for repo in an:
        with open(os.path.join(cache, repo.replace("/", "__") + ".json"), encoding="utf-8") as f:
            c = json.load(f)
        alberi = c["alberi"]
        r1 = next((i for i, a in enumerate(alberi) if pesi(a)), None)
        r2 = next((i for i, a in enumerate(alberi) if pesi(a, True)), None)
        if r1 != r2:
            print(repo, "rilascio", r1, "->", r2, "|", c["commit"][r1]["data"][:16] if r1 is not None else None, "->",
                  c["commit"][r2]["data"][:16] if r2 is not None else None,
                  "| file al primo:", sorted(pesi(alberi[r1]))[:3])


if __name__ == "__main__":
    main()
