"""Controllo dell'"oscuramento": in transformers 5, se nel repository esiste chat_template.jinja, quel file ha
la precedenza sulla chiave chat_template di tokenizer_config.json. Un cambio della sola chiave potrebbe quindi non
avere alcun effetto. Per ogni cambio di template in cui il jinja non e' stato scaricato (perche' non cambiato)
si chiede all'API (solo metadati: paths-info) se chat_template.jinja esiste in quel commit.
Uso: python -I ricalcolo_oscurati.py <lavori.json> <uscita.json>
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hf_api  # noqa: E402


def main():
    with open(sys.argv[1], encoding="utf-8") as f:
        lavori = json.load(f)
    out = {}
    for l in lavori:
        if "jinja" in l["sorgenti"]:
            continue
        chiave = f"{l['repo']}@{l['commit']}"
        dati, _ = hf_api.post(f"{l['repo']}/paths-info/{l['commit']}", {"paths": ["chat_template.jinja"]})
        if isinstance(dati, dict) and "_http" in dati:
            out[chiave] = "api_errore_" + str(dati["_http"])
        else:
            out[chiave] = "oscurato" if any(x.get("path") == "chat_template.jinja" for x in dati) else "visibile"
    with open(sys.argv[2], "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    from collections import Counter
    print(Counter(out.values()), "chiamate:", hf_api.n_chiamate[0])


if __name__ == "__main__":
    main()
