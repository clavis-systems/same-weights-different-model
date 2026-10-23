"""Ricalcolo indipendente del passo 0a ("stessi pesi, modello diverso").

Legge SOLO modelli.jsonl (uscita grezza del censimento) e PREMESSA.md (definizioni).
Non usa il codice dell'altra sessione. Uso:
    python -I ricalcolo_0a.py <cartella corsa1> [--json uscita.json]
"""
import json
import statistics
import sys
from datetime import datetime, timezone

PRIMARI = ["tokenizer_config.json", "chat_template.jinja", "chat_template.json",
           "generation_config.json", "special_tokens_map.json"]
GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia",
          "deepseek-ai", "openai", "HuggingFaceTB", "allenai", "ibm-granite"]


def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def carica(cartella):
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        return [json.loads(r) for r in f]


def quartili(x, metodo):
    x = sorted(x)
    if metodo == "inclusive":      # = numpy linear
        q = statistics.quantiles(x, n=4, method="inclusive")
    else:                          # = metodo esclusivo (default di statistics)
        q = statistics.quantiles(x, n=4, method="exclusive")
    return q


def cambi_stessi_pesi(r):
    """cambi post-rilascio a pesi identici con almeno un file primario cambiato"""
    rel = t(r["rilascio"]["data"])
    out = []
    for c in r["cambi"]:
        if c["pesi_cambiati"]:
            continue
        if not c["primari"]:
            continue
        # sicurezza: il cambio dev'essere successivo al rilascio (per indice)
        if c["indice"] <= r["rilascio"]["indice"]:
            continue
        giorni = (t(c["data"]) - rel).total_seconds() / 86400
        out.append((c, giorni))
    return out


def grande(repo):
    return repo.split("/")[0] in GRANDI


def riepilogo(sub, etichetta):
    n = len(sub)
    m1 = [r for r in sub if cambi_stessi_pesi(r)]
    m1b = [r for r in sub if any(g > 7 for _, g in cambi_stessi_pesi(r))]
    perfile = {f: sum(1 for r in sub if any(f in c["primari"] for c, _ in cambi_stessi_pesi(r))) for f in PRIMARI}
    perfile_cambi = {f: sum(1 for r in sub for c, _ in cambi_stessi_pesi(r) if f in c["primari"]) for f in PRIMARI}
    # M3: varianti
    tutti = [g for r in sub for _, g in cambi_stessi_pesi(r)]
    primo = [min(g for _, g in cambi_stessi_pesi(r)) for r in m1]
    out = {"etichetta": etichetta, "n": n, "M1": len(m1), "M1_pct": 100 * len(m1) / n,
           "M1b": len(m1b), "M1b_pct": 100 * len(m1b) / n,
           "per_file_modelli": perfile, "per_file_cambi": perfile_cambi,
           "n_cambi": len(tutti)}
    for nome, serie in (("M3_tutti_i_cambi", tutti), ("M3_primo_cambio_per_modello", primo)):
        out[nome] = {"n": len(serie), "mediana": statistics.median(serie),
                     "quartili_esclusivo": quartili(serie, "esclusivo"),
                     "quartili_inclusivo": quartili(serie, "inclusive")}
    return out


def main():
    cartella = sys.argv[1]
    rows = carica(cartella)
    non_acc = [r for r in rows if "non_accessibile" in r]
    senza_rel = [r for r in rows if "cambi" in r and not r["rilascio"]]
    analizzati = [r for r in rows if "cambi" in r and r["rilascio"]]
    print("totale righe", len(rows), "| non accessibili", len(non_acc),
          "| senza rilascio", [r["repo"] for r in senza_rel], "| analizzati", len(analizzati))
    res = {"n_righe": len(rows), "non_accessibili": len(non_acc),
           "senza_rilascio": [r["repo"] for r in senza_rel], "analizzati": len(analizzati)}
    res["tutti"] = riepilogo(analizzati, "tutti")
    res["grandi"] = riepilogo([r for r in analizzati if grande(r["repo"])], "grandi")
    res["altri"] = riepilogo([r for r in analizzati if not grande(r["repo"])], "altri")
    res["non_accessibili_grandi"] = sum(1 for r in non_acc if grande(r["repo"]))
    # nota: quanti cambi con pesi cambiati e file primari (esclusi per definizione)
    res["cambi_primari_con_pesi_cambiati"] = sum(1 for r in analizzati for c in r["cambi"]
                                                 if c["pesi_cambiati"] and c["primari"])
    res["cambi_primari_stessi_pesi"] = sum(1 for r in analizzati for c, _ in cambi_stessi_pesi(r))
    res["file_primari_cambiati_stessi_pesi"] = sum(len(c["primari"]) for r in analizzati
                                                   for c, _ in cambi_stessi_pesi(r))
    # bordo dei 7 giorni
    bordo = [(r["repo"], round(g, 4)) for r in analizzati for _, g in cambi_stessi_pesi(r) if 6.9 < g < 7.1]
    res["cambi_vicini_a_7_giorni"] = bordo
    print(json.dumps(res, indent=1, ensure_ascii=False, default=str))
    if "--json" in sys.argv:
        with open(sys.argv[sys.argv.index("--json") + 1], "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1, ensure_ascii=False, default=str)


if __name__ == "__main__":
    main()
