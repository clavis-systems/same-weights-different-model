"""Censimento "stessi pesi, modello diverso" (passo 0a, solo metadati).

Per i modelli text-generation piu' scaricati su Hugging Face ricostruisce dalla storia dei commit quando sono
cambiati i file che decidono il comportamento (template di chat, parametri di generazione, token speciali) e se
nello stesso commit sono cambiati anche i pesi. Usa solo l'API pubblica dei metadati: non scarica il contenuto di
nessun file. Definizioni in PREMESSA.md.

Uso:
  python -I -X utf8 censimento.py raccogli --n 200 --out CARTELLA [--solo repo1,repo2]
  python -I -X utf8 censimento.py riassumi CARTELLA
"""
import argparse
import json
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://huggingface.co/api"
PRIMARI = ("tokenizer_config.json", "chat_template.jinja", "chat_template.json",
           "generation_config.json", "special_tokens_map.json")
SECONDARI = ("config.json", "tokenizer.json")
ESTENSIONI_PESI = (".safetensors", ".bin", ".gguf", ".pt", ".pth")
ORG_GRANDI = ("google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
              "HuggingFaceTB", "allenai", "ibm-granite")
PAUSA = 0.35


class Rifiutato(Exception):
    """Risposta 401/403/404: repository riservato o sparito."""


def chiedi(url, tentativi=6):
    for t in range(tentativi):
        req = urllib.request.Request(url, headers={"User-Agent": "censimento-stessi-pesi/0.1"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                corpo = r.read()
                link = r.headers.get("Link", "") or ""
            time.sleep(PAUSA)
            return json.loads(corpo), link
        except urllib.error.HTTPError as e:
            if e.code in (401, 403, 404):
                raise Rifiutato(e.code)
            if e.code == 429 or e.code >= 500:
                attesa = int(e.headers.get("Retry-After") or 0) or 10 * (t + 1)
                time.sleep(min(attesa, 300))
                continue
            raise
        except (urllib.error.URLError, TimeoutError):
            time.sleep(5 * (t + 1))
    raise RuntimeError(f"troppi tentativi: {url}")


def prossimo(link):
    for parte in link.split(","):
        if 'rel="next"' in parte:
            return parte[parte.find("<") + 1:parte.find(">")]
    return None


def tutte_le_pagine(url):
    out = []
    while url:
        dati, link = chiedi(url)
        out.extend(dati)
        url = prossimo(link)
    return out


def impronta(voci):
    prim, sec, pesi = {}, {}, {}
    for v in voci:
        if v.get("type") != "file":
            continue
        p = v["path"]
        if p in PRIMARI:
            prim[p] = v.get("oid")
        elif p in SECONDARI:
            sec[p] = v.get("oid")
        if p.endswith(ESTENSIONI_PESI):
            pesi[p] = (v.get("lfs") or {}).get("oid") or v.get("oid")
    return {"primari": prim, "secondari": sec, "pesi": pesi}


def primo_indice(n, vero, inizio=0):
    """Primo indice in [inizio, n) con vero(i), assumendo che dopo la prima volta resti vero; None se mai."""
    if n == 0 or not vero(n - 1):
        return None
    lo, hi = inizio, n - 1
    while lo < hi:
        m = (lo + hi) // 2
        if vero(m):
            hi = m
        else:
            lo = m + 1
    return lo


def punti_di_cambio(n, chiave, inizio):
    """Indici j > inizio con chiave(j) != chiave(j-1), per bisezione (i ritorni A->B->A sfuggono)."""
    trovati = []

    def tratto(i, j):
        if chiave(i) == chiave(j):
            return
        if j == i + 1:
            trovati.append(j)
            return
        m = (i + j) // 2
        tratto(i, m)
        tratto(m, j)

    if inizio is not None and n - 1 > inizio:
        tratto(inizio, n - 1)
    return sorted(trovati)


def cambiati(a, b):
    return sorted(k for k in set(a) | set(b) if a.get(k) != b.get(k))


def analizza(repo):
    rq = urllib.parse.quote(repo, safe="/")
    commit = tutte_le_pagine(f"{API}/models/{rq}/commits/main")[::-1]  # dal piu' vecchio
    cache = {}

    def f(i):
        if i not in cache:
            sha = commit[i]["id"]
            cache[i] = impronta(tutte_le_pagine(f"{API}/models/{rq}/tree/{sha}"))
        return cache[i]

    n = len(commit)
    rilascio = primo_indice(n, lambda i: bool(f(i)["pesi"]))
    approssimato = False
    if rilascio is None:
        rilascio = primo_indice(n, lambda i: bool(f(i)["primari"]))
        approssimato = True
    punti = punti_di_cambio(n, lambda i: (f(i)["primari"], f(i)["secondari"]), rilascio)
    cambi = []
    for j in punti:
        a, b = f(j - 1), f(j)
        cambi.append({
            "indice": j,
            "commit": commit[j]["id"],
            "data": commit[j].get("date"),
            "titolo": (commit[j].get("title") or "")[:200],
            "primari": cambiati(a["primari"], b["primari"]),
            "secondari": cambiati(a["secondari"], b["secondari"]),
            "pesi_cambiati": a["pesi"] != b["pesi"],
        })
    return {
        "repo": repo,
        "n_commit": n,
        "rilascio": None if rilascio is None else {"indice": rilascio, "commit": commit[rilascio]["id"],
                                                    "data": commit[rilascio].get("date"),
                                                    "approssimato": approssimato},
        "chiamate_tree": len(cache),
        "cambi": cambi,
    }


def raccogli(args):
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    if args.solo:
        elenco = [{"id": r, "downloads": None} for r in args.solo.split(",")]
    else:
        url = (f"{API}/models?pipeline_tag=text-generation&sort=downloads&direction=-1&limit={args.n}")
        elenco, _ = chiedi(url)
        elenco = elenco[:args.n]
    istantanea = {"ora_utc": datetime.now(timezone.utc).isoformat(), "n": len(elenco),
                  "modelli": [{"repo": m["id"], "downloads": m.get("downloads"), "likes": m.get("likes")}
                              for m in elenco]}
    (out / "istantanea.json").write_text(json.dumps(istantanea, indent=1), encoding="utf-8")
    righe = out / "modelli.jsonl"
    fatti = set()
    if righe.exists():
        fatti = {json.loads(l)["repo"] for l in righe.read_text(encoding="utf-8").splitlines() if l.strip()}
    with righe.open("a", encoding="utf-8") as fh:
        for k, m in enumerate(elenco, 1):
            repo = m["id"]
            if repo in fatti:
                continue
            t0 = time.time()
            try:
                riga = analizza(repo)
            except Rifiutato as e:
                riga = {"repo": repo, "non_accessibile": int(str(e))}
            except Exception as e:  # registrato, la corsa continua
                riga = {"repo": repo, "errore": f"{type(e).__name__}: {e}"[:300]}
            riga["downloads"] = m.get("downloads")
            fh.write(json.dumps(riga, ensure_ascii=False) + "\n")
            fh.flush()
            stato = ("non accessibile" if "non_accessibile" in riga else "errore" if "errore" in riga
                     else f"{riga['n_commit']} commit, {len(riga['cambi'])} cambi")
            print(f"[{k}/{len(elenco)}] {repo}: {stato} ({time.time() - t0:.0f} s)", flush=True)


def giorni(a, b):
    da = datetime.fromisoformat(a.replace("Z", "+00:00"))
    db = datetime.fromisoformat(b.replace("Z", "+00:00"))
    return (db - da).total_seconds() / 86400


def misure(righe):
    ok = [r for r in righe if "cambi" in r and r.get("rilascio")]
    con = [r for r in ok if any(c["primari"] and not c["pesi_cambiati"] for c in r["cambi"])]
    con_tardi = [r for r in ok if any(c["primari"] and not c["pesi_cambiati"] and c.get("data")
                                      and r["rilascio"].get("data")
                                      and giorni(r["rilascio"]["data"], c["data"]) > 7 for c in r["cambi"])]
    per_file = {p: sum(1 for r in ok if any(p in c["primari"] and not c["pesi_cambiati"] for c in r["cambi"]))
                for p in PRIMARI}
    ritardi = [giorni(r["rilascio"]["data"], c["data"]) for r in ok for c in r["cambi"]
               if c["primari"] and not c["pesi_cambiati"] and c.get("data") and r["rilascio"].get("data")]
    q = statistics.quantiles(ritardi, n=4) if len(ritardi) >= 4 else None
    return {
        "analizzati": len(ok),
        "M1_modelli_con_cambio_primario_a_pesi_identici": len(con),
        "M1_quota": round(len(con) / len(ok), 3) if ok else None,
        "M1b_oltre_7_giorni": len(con_tardi),
        "M1b_quota": round(len(con_tardi) / len(ok), 3) if ok else None,
        "M2_per_file": per_file,
        "M3_giorni_mediana": round(statistics.median(ritardi), 1) if ritardi else None,
        "M3_quartili": [round(x, 1) for x in q] if q else None,
        "n_cambi_primari_a_pesi_identici": len(ritardi),
        "modelli_con_cambio": [r["repo"] for r in con],
    }


def riassumi(args):
    cartella = Path(args.cartella)
    righe = [json.loads(l) for l in (cartella / "modelli.jsonl").read_text(encoding="utf-8").splitlines()
             if l.strip()]
    grandi = [r for r in righe if r["repo"].split("/")[0] in ORG_GRANDI]
    ris = {
        "totale_righe": len(righe),
        "non_accessibili": [r["repo"] for r in righe if "non_accessibile" in r],
        "errori": [{"repo": r["repo"], "errore": r["errore"]} for r in righe if "errore" in r],
        "rilascio_approssimato": [r["repo"] for r in righe if (r.get("rilascio") or {}).get("approssimato")],
        "tutti": misure(righe),
        "M4_org_grandi": misure(grandi),
    }
    (cartella / "riassunto.json").write_text(json.dumps(ris, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(ris, indent=1, ensure_ascii=False)[:4000])


def main(argv=None):
    p = argparse.ArgumentParser()
    s = p.add_subparsers(dest="cmd", required=True)
    r = s.add_parser("raccogli")
    r.add_argument("--n", type=int, default=200)
    r.add_argument("--out", required=True)
    r.add_argument("--solo")
    a = s.add_parser("riassumi")
    a.add_argument("cartella")
    args = p.parse_args(argv)
    {"raccogli": raccogli, "riassumi": riassumi}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
