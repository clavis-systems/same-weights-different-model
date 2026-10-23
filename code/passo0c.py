"""Passo 0c di "stessi pesi, modello diverso": il cambio del template cambia cio' che il modello riceve?

Renderizza template di prima e di dopo con la funzione di transformers (sandbox Jinja ufficiale) su conversazioni
fisse e confronta i testi. Usa solo i file gia' scaricati dal passo 0b (dati non fidati: solo letti e renderizzati
nel sandbox, mai eseguiti come codice). Definizioni in PREMESSA.md (aggiunta del 20/10).

Uso (ambiente con transformers):
  python -I -X utf8 passo0c.py CARTELLA_CORSA
"""
import json
import sys
from datetime import datetime
from pathlib import Path

from transformers.utils.chat_template_utils import render_jinja_template

STRUMENTO = {"type": "function", "function": {
    "name": "get_weather", "description": "Get the current weather in a city",
    "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}}}
CONVERSAZIONI = {
    "C1": ([{"role": "user", "content": "Hello, how are you?"}], True, None),
    "C2": ([{"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"}], True, None),
    "C3": ([{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello! How can I help?"},
            {"role": "user", "content": "Tell me a joke."}], True, None),
    "C4": ([{"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is 2+2?"}, {"role": "assistant", "content": "4"}], False, None),
    "C5": ([{"role": "user", "content": "What's the weather in Milan?"}], True, [STRUMENTO]),
}
NORMALI = ("C1", "C2", "C3", "C4")


def template_da(percorso):
    if not percorso.exists():
        return None
    testo = percorso.read_text(encoding="utf-8", errors="replace")
    if percorso.suffix == ".jinja":
        return testo
    try:
        dati = json.loads(testo)
    except json.JSONDecodeError:
        return None
    t = dati.get("chat_template") if isinstance(dati, dict) else None
    if isinstance(t, list):  # template con nome: si usa "default", altrimenti il primo
        scelto = next((x for x in t if x.get("name") == "default"), t[0] if t else None)
        t = scelto.get("template") if scelto else None
    return t if isinstance(t, str) else None


def rendi(template):
    out = {}
    for nome, (msg, agp, strumenti) in CONVERSAZIONI.items():
        try:
            testo, _ = render_jinja_template(conversations=[msg], tools=strumenti, chat_template=template,
                                             add_generation_prompt=agp, bos_token="<s>", eos_token="</s>")
            out[nome] = testo[0]
        except Exception as e:  # registrato come errore di rendering
            out[nome] = f"__ERRORE__ {type(e).__name__}"
    return out


def giorni(a, b):
    return (datetime.fromisoformat(b.replace("Z", "+00:00"))
            - datetime.fromisoformat(a.replace("Z", "+00:00"))).total_seconds() / 86400


def main(cartella):
    cartella = Path(cartella)
    righe = json.loads((cartella / "classificazione_0b.json").read_text(encoding="utf-8"))
    rilascio = {}
    for l in (cartella / "modelli.jsonl").read_text(encoding="utf-8").splitlines():
        r = json.loads(l)
        if r.get("rilascio"):
            rilascio[r["repo"]] = r["rilascio"]["data"]
    base = cartella / "file0b"
    esiti = []
    for r in righe:
        if "chat_template" not in r.get("chiavi_comportamento", []) and not r["file"].startswith("chat_template"):
            continue
        cart = base / r["repo"].replace("/", "__")
        prima = template_da(cart / r["prima"] / r["file"]) if r.get("byte_prima") is not None else None
        dopo = template_da(cart / r["dopo"] / r["file"]) if r.get("byte_dopo") is not None else None
        e = {"repo": r["repo"], "file": r["file"], "dopo": r["dopo"], "data": r["data"],
             "giorni": round(giorni(rilascio[r["repo"]], r["data"]), 1) if r["repo"] in rilascio else None}
        if prima is None or dopo is None:
            e["classe"] = "non confrontabile"
        else:
            a, b = rendi(prima), rendi(dopo)
            if any(v.startswith("__ERRORE__") for v in list(a.values()) + list(b.values())):
                e["classe"] = "errore di rendering"
                e["errori"] = sorted({v for v in list(a.values()) + list(b.values()) if v.startswith("__ERRORE__")})
            diverse = [k for k in CONVERSAZIONI if a[k] != b[k]]
            e["conversazioni_diverse"] = diverse
            if "classe" not in e:
                e["classe"] = ("uso normale" if any(k in NORMALI for k in diverse)
                               else "solo con strumenti" if diverse else "nessun cambio visibile")
            if any(k in NORMALI for k in diverse):
                k = next(k for k in NORMALI if k in diverse)
                e["esempio"] = {"conversazione": k, "prima": a[k][-300:], "dopo": b[k][-300:]}
        esiti.append(e)
    (cartella / "rendering_0c.json").write_text(json.dumps(esiti, indent=1, ensure_ascii=False), encoding="utf-8")
    from collections import Counter
    print("cambi di template:", len(esiti), dict(Counter(e["classe"] for e in esiti)))
    normali = {e["repo"] for e in esiti if e["classe"] == "uso normale"}
    tardi = {e["repo"] for e in esiti if e["classe"] == "uso normale" and (e["giorni"] or 0) > 7}
    print(f"modelli con un cambio di template che cambia l'uso normale: {len(normali)}; oltre 7 giorni: {len(tardi)}")


if __name__ == "__main__":
    main(sys.argv[1])
