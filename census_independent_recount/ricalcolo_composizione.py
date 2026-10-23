"""Sensibilita' dei numeri alla composizione della popolazione (Qwen, fixture di test, derivati quantizzati).
Uso: python -I ricalcolo_composizione.py <cartella corsa1> <mio_0b.json>
"""
import json
import sys
from datetime import datetime, timezone

GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
          "HuggingFaceTB", "allenai", "ibm-granite"]
FIXTURE = ("tiny-random", "trl-internal-testing", "peft-internal-testing", "tiny-qwen", "tiny-llama")
QUANT = ("AWQ", "GPTQ", "FP8", "NVFP4", "GGUF", "bnb", "mlx", "4bit")


def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def main():
    cartella = sys.argv[1]
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        rows = [json.loads(r) for r in f]
    an = [r for r in rows if "cambi" in r and r["rilascio"]]
    with open(sys.argv[2], encoding="utf-8") as f:
        b0 = json.load(f)["cambi"]
    comp0b = {o["repo"] for o in b0 if o["stretta"] == "comportamento"}

    def org(r):
        return r["repo"].split("/")[0]

    def m1(r):
        return any(c["primari"] and not c["pesi_cambiati"] for c in r["cambi"])

    def m1b(r):
        return any(c["primari"] and not c["pesi_cambiati"] and (t(c["data"]) - t(r["rilascio"]["data"])).total_seconds() > 7 * 86400
                   for c in r["cambi"])

    def riga(nome, sub):
        n = len(sub)
        a, b, c = sum(map(m1, sub)), sum(map(m1b, sub)), sum(1 for r in sub if r["repo"] in comp0b)
        print(f"{nome:46s} n={n:3d}  M1 {a:3d} ({100 * a / n:4.1f}%)  M1b {b:3d} ({100 * b / n:4.1f}%)  "
              f"0b-comportamento {c:3d} ({100 * c / n:4.1f}%)")

    gr = [r for r in an if org(r) in GRANDI]
    riga("tutti", an)
    riga("senza Qwen/", [r for r in an if org(r) != "Qwen"])
    riga("solo Qwen/", [r for r in an if org(r) == "Qwen"])
    riga("senza fixture di test", [r for r in an if not any(k in r["repo"] for k in FIXTURE)])
    riga("senza Qwen/ e senza fixture", [r for r in an if org(r) != "Qwen" and not any(k in r["repo"] for k in FIXTURE)])
    riga("grandi organizzazioni", gr)
    riga("grandi organizzazioni senza Qwen/", [r for r in gr if org(r) != "Qwen"])
    riga("non grandi", [r for r in an if org(r) not in GRANDI])
    riga("derivati quantizzati (nome)", [r for r in an if any(k in r["repo"] for k in QUANT)])
    riga("non quantizzati (nome)", [r for r in an if not any(k in r["repo"] for k in QUANT)])
    # quanti modelli distinti per organizzazione tra i 102
    from collections import Counter
    c = Counter(org(r) for r in an if m1(r))
    print("organizzazioni distinte fra i modelli con M1:", len(c), "| prime:", c.most_common(5))
    # non accessibili: tutte grandi?
    na = [r["repo"] for r in rows if "non_accessibile" in r]
    print("non accessibili:", len(na), "di cui org grandi:", sum(1 for r in na if r.split("/")[0] in GRANDI))
    print("senza rilascio ne' file primari (silenziosamente fuori da 189):",
          [r["repo"] for r in rows if "cambi" in r and not r["rilascio"]])
    ap = [(r["repo"], r["rilascio"]["indice"], r["n_commit"]) for r in an if r["rilascio"]["approssimato"]]
    print("rilascio approssimato:", ap)


if __name__ == "__main__":
    main()
