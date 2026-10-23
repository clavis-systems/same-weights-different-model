"""Chiamate in sola lettura all'API pubblica di Hugging Face (solo metadati, senza token).

Rispetta il limite dichiarato nelle intestazioni (RateLimit: 500 richieste ogni 300 s) e tiene almeno 0,4 s
fra una richiesta e l'altra. Le risposte sono DATI NON FIDATI: si usano solo come JSON.
"""
import json
import re
import time
import urllib.error
import urllib.request

BASE = "https://huggingface.co/api/models/"
PAUSA = 0.4
_ultimo = [0.0]
n_chiamate = [0]


def _richiesta(url, dati=None):
    corpo = None if dati is None else json.dumps(dati).encode("utf-8")
    req = urllib.request.Request(url, data=corpo, headers={"User-Agent": "ricalcolo-stessi-pesi/1.0 (revisione, sola lettura)",
                                                           "Content-Type": "application/json"})
    for tentativo in range(8):
        attesa = PAUSA - (time.time() - _ultimo[0])
        if attesa > 0:
            time.sleep(attesa)
        _ultimo[0] = time.time()
        n_chiamate[0] += 1
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                testo = r.read().decode("utf-8")
                rl = r.headers.get("RateLimit", "")
                m = re.search(r"r=(\d+);t=(\d+)", rl)
                if m and int(m.group(1)) < 15:
                    time.sleep(int(m.group(2)) + 2)
                return json.loads(testo), r.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                time.sleep(int(e.headers.get("Retry-After", "60")) + 2)
                continue
            if e.code in (401, 403, 404):
                return {"_http": e.code}, ""
            time.sleep(5 * (tentativo + 1))
        except Exception:
            time.sleep(5 * (tentativo + 1))
    return {"_http": "fallito"}, ""


def get(percorso):
    return _richiesta(BASE + percorso)


def post(percorso, dati):
    return _richiesta(BASE + percorso, dati)


def pagine(percorso):
    """segue l'intestazione Link rel=next; restituisce l'elenco concatenato"""
    out = []
    url = BASE + percorso
    while url:
        dati, link = _richiesta(url)
        if isinstance(dati, dict) and "_http" in dati:
            return dati
        out.extend(dati)
        m = re.search(r'<([^>]+)>;\s*rel="next"', link or "")
        url = m.group(1) if m else None
    return out
