"""Ricalcolo indipendente della misura 4 ("cambio reale"): template visibile OPPURE token di fine OPPURE
campionamento, a pesi identici, su modelli analizzati. Usa le uscite dei miei ricalcoli 0b e 0c.
Uso: python -I ricalcolo_4.py <cartella corsa1> <mio_0b.json> <classi_0c.json>
"""
import json
import sys
from collections import defaultdict

GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
          "HuggingFaceTB", "allenai", "ibm-granite"]


def grande(repo):
    return repo.split("/")[0] in GRANDI


def main():
    cartella = sys.argv[1]
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        analizzati = [r["repo"] for r in map(json.loads, f) if "cambi" in r and r["rilascio"]]
    with open(sys.argv[2], encoding="utf-8") as f:
        b0 = json.load(f)["cambi"]
    with open(sys.argv[3], encoding="utf-8") as f:
        c0 = json.load(f)
    comp = {k: set() for k in ("template_uso_normale", "template_uso_o_strumenti", "fine_modifica",
                               "fine_anche_creazioni", "campionamento", "stretta_0b")}
    for o in b0:
        if o["fine"] and o["stato"] == "modificato":
            comp["fine_modifica"].add(o["repo"])
        if o["fine"]:
            comp["fine_anche_creazioni"].add(o["repo"])
        if o["campionamento"]:
            comp["campionamento"].add(o["repo"])
        if o["stretta"] == "comportamento":
            comp["stretta_0b"].add(o["repo"])
    for s in c0:
        if s["classe"] == "uso normale":
            comp["template_uso_normale"].add(s["repo"])
        if s["classe"] in ("uso normale", "solo con strumenti"):
            comp["template_uso_o_strumenti"].add(s["repo"])
    comp = {k: v & set(analizzati) for k, v in comp.items()}
    ng = sum(1 for r in analizzati if grande(r))

    def riga(nome, ins):
        print(f"{nome:55s} {len(ins):4d}/{len(analizzati)} = {100 * len(ins) / len(analizzati):5.1f}% | "
              f"grandi {sum(1 for r in ins if grande(r)):3d}/{ng} = {100 * sum(1 for r in ins if grande(r)) / ng:5.1f}%")

    for k, v in comp.items():
        riga(k, v)
    print("--- unioni ---")
    riga("A: template(uso normale) | fine(modifiche) | campionamento",
         comp["template_uso_normale"] | comp["fine_modifica"] | comp["campionamento"])
    riga("B: template(uso normale o strumenti) | fine | campionamento",
         comp["template_uso_o_strumenti"] | comp["fine_modifica"] | comp["campionamento"])
    riga("C: come A ma fine contando anche creazioni/cancellazioni",
         comp["template_uso_normale"] | comp["fine_anche_creazioni"] | comp["campionamento"])
    riga("D: come B ma fine contando anche creazioni/cancellazioni",
         comp["template_uso_o_strumenti"] | comp["fine_anche_creazioni"] | comp["campionamento"])


if __name__ == "__main__":
    main()
