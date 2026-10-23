"""Controllo della raccolta (punto 5): rifa' da zero, sull'API pubblica di Hugging Face, la storia di alcuni modelli
SENZA bisezione (cartella principale di OGNI commit del ramo main) e la confronta con modelli.jsonl.

Solo metadati: GET commits/main, GET tree/<commit>. Nessun file scaricato.
Uso:
  python -I ricalcolo_campione.py scarica <cartella corsa1> <cartella cache> <seme|tutti> [n]
  python -I ricalcolo_campione.py confronta <cartella corsa1> <cartella cache> <uscita.json>
"""
import json
import os
import random
import sys
from collections import Counter
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hf_api  # noqa: E402

PRIMARI = ["tokenizer_config.json", "chat_template.jinja", "chat_template.json", "generation_config.json",
           "special_tokens_map.json"]
SECONDARI = ["config.json", "tokenizer.json"]
ESTENSIONI_PESI = (".safetensors", ".bin", ".gguf", ".pt", ".pth")


def t(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc)


def analizzati(cartella):
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        rows = [json.loads(r) for r in f]
    return rows, sorted(r["repo"] for r in rows if "cambi" in r and r["rilascio"])


def scarica_repo(repo, cache):
    dest = os.path.join(cache, repo.replace("/", "__") + ".json")
    if os.path.exists(dest):
        return
    commits = hf_api.pagine(f"{repo}/commits/main")
    if isinstance(commits, dict):
        res = {"repo": repo, "errore": commits}
    else:
        commits = list(reversed(commits))        # dal piu' vecchio al piu' recente
        alberi = []
        for c in commits:
            albero = hf_api.pagine(f"{repo}/tree/{c['id']}")
            if isinstance(albero, dict):
                alberi.append({"errore": albero})
                continue
            alberi.append({x["path"]: (x.get("lfs") or {}).get("oid") or x["oid"]
                           for x in albero if x.get("type") == "file"})
        res = {"repo": repo, "commit": [{"id": c["id"], "data": c["date"], "titolo": c["title"]} for c in commits],
               "alberi": alberi}
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(res, f)


def scarica(cartella, cache, seme, n):
    rows, an = analizzati(cartella)
    os.makedirs(cache, exist_ok=True)
    if seme == "tutti":
        scelti = an
    elif seme.startswith("tutti_da_"):   # terzo processo: parte dall'indice k e prosegue
        k = int(seme.split("_")[-1])
        scelti = an[k:] + an[:k]
    elif seme == "tutti_inverso":      # per lanciare un secondo processo che parte dalla fine
        scelti = list(reversed(an))
    else:
        scelti = random.Random(int(seme)).sample(an, n)
    print("modelli scelti:", len(scelti), scelti if len(scelti) <= 25 else "...")
    for i, repo in enumerate(scelti):
        scarica_repo(repo, cache)
        print(i + 1, repo, "chiamate finora:", hf_api.n_chiamate[0], flush=True)
    with open(os.path.join(cache, "_scelti.json"), "w", encoding="utf-8") as f:
        json.dump(scelti, f)


def pesi_di(albero):
    return {k: v for k, v in albero.items() if k.endswith(ESTENSIONI_PESI)}


def confronta(cartella, cache, dest):
    rows, an = analizzati(cartella)
    per_repo = {r["repo"]: r for r in rows}
    out = {"modelli": [], "somma": Counter()}
    for nome in sorted(os.listdir(cache)):
        if nome.startswith("_"):
            continue
        with open(os.path.join(cache, nome), encoding="utf-8") as f:
            d = json.load(f)
        repo = d["repo"]
        r = per_repo[repo]
        sc = {"repo": repo, "n_commit_api": len(d["commit"]), "n_commit_mio": r["n_commit"]}
        sc["n_commit_uguale"] = sc["n_commit_api"] == sc["n_commit_mio"]
        commits, alberi = d["commit"], d["alberi"]
        # rilascio: primo commit con un file di pesi
        rel = next((i for i, a in enumerate(alberi) if pesi_di(a)), None)
        approx = False
        if rel is None:
            rel = next((i for i, a in enumerate(alberi) if any(p in a for p in PRIMARI)), None)
            approx = True
        sc["rilascio_api"] = {"indice": rel,
                              "commit": None if rel is None else commits[rel]["id"], "approssimato": approx}
        sc["rilascio_mio_file"] = r["rilascio"]
        sc["rilascio_uguale"] = (rel is not None and commits[rel]["id"] == r["rilascio"]["commit"]
                                 and rel == r["rilascio"]["indice"])   # indice 0-based (il primo commit e' 0)
        # cambi trovati scandendo ogni coppia di commit consecutivi
        trovati = {}
        for i in range(rel + 1, len(commits)) if rel is not None else []:
            a, b = alberi[i - 1], alberi[i]
            prim = [f for f in PRIMARI if a.get(f) != b.get(f)]
            sec = [f for f in SECONDARI if a.get(f) != b.get(f)]
            if prim or sec:
                trovati[commits[i]["id"]] = {"indice": i, "primari": prim, "secondari": sec,
                                             "giorni": (t(commits[i]["data"]) - t(commits[rel]["data"])).total_seconds() / 86400,
                                             "pesi_cambiati": pesi_di(a) != pesi_di(b),
                                             "pesi_uguali_al_rilascio": pesi_di(b) == pesi_di(alberi[rel])}
        elenco = {c["commit"]: c for c in r["cambi"]}
        sc["cambi_elencati"] = len(elenco)
        sc["cambi_trovati_api"] = len(trovati)
        sc["elencati_ma_non_trovati"] = sorted(set(elenco) - set(trovati))
        sc["trovati_ma_non_elencati"] = sorted(set(trovati) - set(elenco))
        disaccordi = []
        for k in set(elenco) & set(trovati):
            e, tr = elenco[k], trovati[k]
            if sorted(e["primari"]) != sorted(tr["primari"]) or sorted(e["secondari"]) != sorted(tr["secondari"]) \
                    or e["pesi_cambiati"] != tr["pesi_cambiati"] \
                    or e["indice"] != tr["indice"]:
                disaccordi.append({"commit": k, "elencato": {x: e[x] for x in ("indice", "primari", "secondari", "pesi_cambiati")},
                                   "api": {x: tr[x] for x in ("indice", "primari", "secondari", "pesi_cambiati")}})
            # data
            idx = tr["indice"]
            if t(commits[idx]["data"]) != t(e["data"]):
                disaccordi.append({"commit": k, "data": [commits[idx]["data"], e["data"]]})
        sc["disaccordi"] = disaccordi
        # M1 per questo modello, dai due insiemi
        def m1(cambi, chiave_primari="primari"):
            return any(x[chiave_primari] and not x["pesi_cambiati"] for x in cambi)
        sc["M1_elencato"] = m1(r["cambi"])
        sc["M1_api"] = m1(trovati.values())
        # cambi a pesi identici al commit prima ma pesi diversi dal rilascio
        sc["cambi_stessi_pesi_ma_diversi_dal_rilascio"] = [k for k, x in trovati.items()
                                                           if x["primari"] and not x["pesi_cambiati"] and not x["pesi_uguali_al_rilascio"]]
        sc["pesi_finali"] = sorted(pesi_di(alberi[-1]))[:6]
        sc["M1b_api"] = any(x["primari"] and not x["pesi_cambiati"] and x["giorni"] > 7 for x in trovati.values())
        sc["M1_pesi_come_rilascio"] = any(x["primari"] and not x["pesi_cambiati"] and x["pesi_uguali_al_rilascio"]
                                          for x in trovati.values())
        sc["M1b_pesi_come_rilascio"] = any(x["primari"] and not x["pesi_cambiati"] and x["pesi_uguali_al_rilascio"]
                                           and x["giorni"] > 7 for x in trovati.values())
        sc["file_api"] = {f: any(f in x["primari"] and not x["pesi_cambiati"] for x in trovati.values()) for f in PRIMARI}
        sc["pesi_al_rilascio"] = sorted(pesi_di(alberi[rel])) if rel is not None else []
        sc["ritardi_api"] = sorted(x["giorni"] for x in trovati.values() if x["primari"] and not x["pesi_cambiati"])
        sc["pesi_cambiati_dopo_rilascio_senza_config"] = sum(
            1 for i in range(rel + 1, len(commits)) if rel is not None and pesi_di(alberi[i]) != pesi_di(alberi[i - 1])
            and commits[i]["id"] not in trovati)
        out["modelli"].append(sc)
        out["somma"]["modelli"] += 1
        out["somma"]["n_commit_uguale"] += sc["n_commit_uguale"]
        out["somma"]["rilascio_uguale"] += sc["rilascio_uguale"]
        out["somma"]["cambi_elencati"] += sc["cambi_elencati"]
        out["somma"]["cambi_trovati_api"] += sc["cambi_trovati_api"]
        out["somma"]["elencati_ma_non_trovati"] += len(sc["elencati_ma_non_trovati"])
        out["somma"]["trovati_ma_non_elencati"] += len(sc["trovati_ma_non_elencati"])
        out["somma"]["disaccordi"] += len(disaccordi)
        out["somma"]["M1_elencato"] += sc["M1_elencato"]
        out["somma"]["M1_api"] += sc["M1_api"]
        out["somma"]["cambi_stessi_pesi_ma_diversi_dal_rilascio"] += len(sc["cambi_stessi_pesi_ma_diversi_dal_rilascio"])
        out["somma"]["M1b_api"] += sc["M1b_api"]
        out["somma"]["M1_pesi_come_rilascio"] += sc["M1_pesi_come_rilascio"]
        out["somma"]["M1b_pesi_come_rilascio"] += sc["M1b_pesi_come_rilascio"]
        out["somma"]["pesi_cambiati_dopo_rilascio_senza_config"] += sc["pesi_cambiati_dopo_rilascio_senza_config"]
        out["somma"]["modelli_con_pesi_cambiati_dopo_rilascio_senza_config"] += sc["pesi_cambiati_dopo_rilascio_senza_config"] > 0
        for f in PRIMARI:
            out["somma"]["file_" + f] += sc["file_api"][f]
    out["somma"] = dict(out["somma"])
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(out["somma"], indent=1))
    for sc in out["modelli"]:
        brutti = [k for k in ("n_commit_uguale", "rilascio_uguale") if not sc[k]]
        if brutti or sc["elencati_ma_non_trovati"] or sc["trovati_ma_non_elencati"] or sc["disaccordi"] \
                or sc["M1_elencato"] != sc["M1_api"] or sc["cambi_stessi_pesi_ma_diversi_dal_rilascio"]:
            print("DA GUARDARE:", sc["repo"], brutti, "mancano:", len(sc["elencati_ma_non_trovati"]),
                  "in piu':", len(sc["trovati_ma_non_elencati"]), "disaccordi:", len(sc["disaccordi"]),
                  "pesi!=rilascio:", len(sc["cambi_stessi_pesi_ma_diversi_dal_rilascio"]))


if __name__ == "__main__":
    if sys.argv[1] == "scarica":
        scarica(sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]) if len(sys.argv) > 5 else 20)
    else:
        confronta(sys.argv[2], sys.argv[3], sys.argv[4])
