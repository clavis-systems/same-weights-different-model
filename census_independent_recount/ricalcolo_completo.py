"""Riassunto della raccolta completa rifatta via API (senza bisezione), dal JSON prodotto da
`ricalcolo_campione.py confronta`. Ricalcola M1, M1b, M2, M3, M4 dai MIEI dati e li confronta con i numeri
dichiarati; elenca i cambi persi dalla bisezione e i nomi di "pesi" insoliti al rilascio.
Uso: python -I ricalcolo_completo.py <confronto.json> <cache>
"""
import json
import os
import statistics
import sys
from collections import Counter

GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
          "HuggingFaceTB", "allenai", "ibm-granite"]
PRIMARI = ["tokenizer_config.json", "chat_template.jinja", "chat_template.json", "generation_config.json",
           "special_tokens_map.json"]
NOMI_PESI_NORMALI = ("model", "pytorch_model", "consolidated", "adapter_model", "diffusion_pytorch_model", "tf_model")


def normale(nome):
    return nome.endswith(".gguf") or nome.startswith(NOMI_PESI_NORMALI)


def riga(nome, sub):
    n = len(sub)
    m1 = sum(s["M1_api"] for s in sub)
    m1b = sum(s["M1b_api"] for s in sub)
    m1s = sum(s["M1_pesi_come_rilascio"] for s in sub)
    m1bs = sum(s["M1b_pesi_come_rilascio"] for s in sub)
    print(f"{nome:10s} n={n:3d}  M1={m1:3d} ({100 * m1 / n:4.1f}%)  M1b={m1b:3d} ({100 * m1b / n:4.1f}%)  "
          f"| con pesi uguali a quelli del rilascio: M1={m1s:3d} ({100 * m1s / n:4.1f}%)  M1b={m1bs:3d} ({100 * m1bs / n:4.1f}%)")
    for f in PRIMARI:
        print(f"      {f:26s} modelli {sum(1 for s in sub if s['file_api'][f]):3d}")
    rit = [x for s in sub for x in s["ritardi_api"]]
    if len(rit) >= 4:
        q = statistics.quantiles(rit, n=4)
        print(f"      M3: {len(rit)} cambi, mediana {statistics.median(rit):.2f} g, quartili {q[0]:.2f} / {q[1]:.2f} / {q[2]:.2f}")


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        o = json.load(f)
    ms = o["modelli"]
    print("modelli confrontati:", len(ms))
    print(json.dumps(o["somma"], indent=1))
    riga("tutti", ms)
    riga("grandi", [s for s in ms if s["repo"].split("/")[0] in GRANDI])
    print("--- differenze con modelli.jsonl ---")
    for s in ms:
        if (not s["n_commit_uguale"] or not s["rilascio_uguale"] or s["elencati_ma_non_trovati"]
                or s["trovati_ma_non_elencati"] or s["disaccordi"] or s["M1_elencato"] != s["M1_api"]):
            print(s["repo"], "n_commit", s["n_commit_api"], s["n_commit_mio"], "| rilascio uguale:", s["rilascio_uguale"],
                  "| mancanti:", len(s["elencati_ma_non_trovati"]), "| in piu':", len(s["trovati_ma_non_elencati"]),
                  "| disaccordi:", len(s["disaccordi"]), "| M1", s["M1_elencato"], s["M1_api"])
    print("--- pesi al rilascio con nomi insoliti ---")
    for s in ms:
        strani = [n for n in s["pesi_al_rilascio"] if not normale(n)]
        if strani:
            print(s["repo"], strani[:5])
    print("--- modelli con pesi cambiati dopo il rilascio in commit senza cambi di config ---")
    c = Counter()
    for s in ms:
        if s["pesi_cambiati_dopo_rilascio_senza_config"]:
            c[s["repo"]] = s["pesi_cambiati_dopo_rilascio_senza_config"]
    print(len(c), c.most_common(10))


if __name__ == "__main__":
    main()
