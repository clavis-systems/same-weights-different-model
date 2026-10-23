"""Ricalcolo indipendente del passo 0b: i cambi di file toccano il comportamento?

Entrate: modelli.jsonl, piano_0b.json (elenco dei file scaricati) e file0b/ (DATI NON FIDATI, solo letti
come testo/JSON; nessun codice viene eseguito). Uscita: classificazione di ogni cambio di file.

Le liste di chiavi sono MIE, fissate qui in base al ruolo di ogni chiave in transformers; la premessa non le
contiene. Si riportano due versioni: STRETTA (chat template, token di fine/inizio/riempimento/ignoto e id,
parametri di campionamento/lunghezza) e LARGA (stretta + definizione dei token speciali e opzioni di
tokenizzazione). Tutto il resto e' innocuo.
Uso: python -I ricalcolo_0b.py <cartella corsa1> [--json uscita.json]
"""
import json
import os
import sys
from collections import Counter, defaultdict

GRANDI = ["google", "meta-llama", "Qwen", "mistralai", "microsoft", "nvidia", "deepseek-ai", "openai",
          "HuggingFaceTB", "allenai", "ibm-granite"]

TOK = {"bos_token", "eos_token", "pad_token", "unk_token"}
CORE = {
    "tokenizer_config.json": TOK | {"chat_template"},
    "special_tokens_map.json": TOK,
    "generation_config.json": {"eos_token_id", "bos_token_id", "pad_token_id", "decoder_start_token_id",
                               "temperature", "top_p", "top_k", "min_p", "typical_p", "do_sample",
                               "repetition_penalty", "max_new_tokens", "max_length", "min_length",
                               "min_new_tokens", "num_beams", "length_penalty", "no_repeat_ngram_size"},
}
LARGA = {
    "tokenizer_config.json": {
        "added_tokens_decoder", "tokenizer_class", "clean_up_tokenization_spaces", "add_bos_token",
        "extra_special_tokens", "add_prefix_space", "padding_side", "additional_special_tokens",
        "add_eos_token", "legacy", "sp_model_kwargs", "split_special_tokens", "response_schema",
        "model_specific_special_tokens", "model_input_names", "pad_token_type_id",
        "use_default_system_prompt", "video_token", "audio_token", "vision_eos_token", "image_token",
        "pretokenize_regex", "truncation_side", "audio_bos_token", "audio_eos_token", "vision_bos_token",
        "spaces_between_special_tokens", "errors", "cls_token", "sep_token", "mask_token"},
    "special_tokens_map.json": {"additional_special_tokens", "cls_token", "sep_token", "mask_token"},
    "generation_config.json": {"tool_call_parser", "default_chat_template_kwargs", "reasoning_parser"},
}
# chiavi che sono "di fine" (token di fine sequenza) e "di campionamento" per la misura 4
FINE = {"eos_token", "eos_token_id"}
CAMPIONAMENTO = {"temperature", "top_p", "top_k", "min_p", "typical_p", "do_sample", "repetition_penalty",
                 "num_beams", "length_penalty", "no_repeat_ngram_size"}


def norm_tok(v):
    if isinstance(v, dict) and "content" in v:
        return v["content"]
    if isinstance(v, list):
        return [norm_tok(x) for x in v]
    return v


def norm(chiave, v):
    if chiave in TOK or chiave in ("additional_special_tokens", "cls_token", "sep_token", "mask_token"):
        v = norm_tok(v)
    if chiave.endswith("_token_id") and isinstance(v, list):
        v = sorted(v)
    if chiave.endswith("_token_id") and isinstance(v, int):
        v = [v]          # 2 e [2] sono la stessa cosa
    return v


def leggi(cartella, voce, lato):
    if voce["byte_" + lato] is None:
        return None
    p = f"{cartella}/file0b/{voce['repo'].replace('/', '__')}/{voce[lato]}/{voce['file']}"
    with open(p, "rb") as f:
        return f.read().decode("utf-8")


def diff_chiavi(file, a, b):
    """restituisce (stato, chiavi_cambiate); stato in modificato/creato/cancellato/illeggibile/identico"""
    if file.startswith("chat_template."):
        if a is None:
            return "creato", ["<contenuto>"]
        if b is None:
            return "cancellato", ["<contenuto>"]
        return ("identico", []) if a == b else ("modificato", ["<contenuto>"])
    try:
        ja = json.loads(a) if a is not None else {}
        jb = json.loads(b) if b is not None else {}
        assert isinstance(ja, dict) and isinstance(jb, dict)
    except Exception:
        return "illeggibile", ["<json non valido>"]
    chiavi = []
    for k in sorted(set(ja) | set(jb)):
        va = norm(k, ja.get(k, "<ASSENTE>"))
        vb = norm(k, jb.get(k, "<ASSENTE>"))
        if va != vb:
            chiavi.append(k)
    stato = "creato" if a is None else "cancellato" if b is None else "modificato"
    if not chiavi and stato == "modificato":
        stato = "identico"
    return stato, chiavi


def classifica(file, stato, chiavi):
    if stato == "illeggibile":
        return "illeggibile", "illeggibile"
    if file.startswith("chat_template."):
        c = "comportamento" if stato != "identico" else "innocuo"
        return c, c
    core = [k for k in chiavi if k in CORE.get(file, set())]
    larga = [k for k in chiavi if k in LARGA.get(file, set())]
    stretta = "comportamento" if core else "innocuo"
    largac = "comportamento" if (core or larga) else "innocuo"
    return stretta, largac


def grande(repo):
    return repo.split("/")[0] in GRANDI


def main():
    cartella = sys.argv[1]
    with open(cartella + "/modelli.jsonl", encoding="utf-8") as f:
        rows = [json.loads(r) for r in f]
    with open(cartella + "/piano_0b.json", encoding="utf-8") as f:
        piano = json.load(f)["voci"]
    # 1) l'elenco atteso dei cambi di file, dalle sole uscite del censimento
    attesi = set()
    for r in rows:
        if "cambi" not in r or not r["rilascio"]:
            continue
        for c in r["cambi"]:
            if c["pesi_cambiati"] or c["indice"] <= r["rilascio"]["indice"]:
                continue
            for fl in c["primari"]:
                attesi.add((r["repo"], c["commit"], fl))
    scaricati = {(v["repo"], v["dopo"], v["file"]) for v in piano}
    print("cambi di file attesi dal censimento:", len(attesi), "| nel piano 0b:", len(scaricati),
          "| solo in uno:", len(attesi ^ scaricati))

    out = []
    for v in piano:
        a, b = leggi(cartella, v, "prima"), leggi(cartella, v, "dopo")
        stato, chiavi = diff_chiavi(v["file"], a, b)
        stretta, larga = classifica(v["file"], stato, chiavi)
        out.append({"repo": v["repo"], "file": v["file"], "commit": v["dopo"], "data": v["data"], "stato": stato,
                    "chiavi": chiavi, "stretta": stretta, "larga": larga,
                    "fine": bool(set(chiavi) & FINE), "campionamento": bool(set(chiavi) & CAMPIONAMENTO),
                    "template": ("chat_template" in chiavi) or v["file"].startswith("chat_template.")})
    res = {"n_cambi_file": len(out)}
    res["stato"] = dict(Counter(o["stato"] for o in out))
    for nome in ("stretta", "larga"):
        res[nome] = dict(Counter(o[nome] for o in out))
    res["identici_dopo_normalizzazione"] = [(o["repo"], o["file"], o["commit"][:8]) for o in out if o["stato"] == "identico"]
    res["illeggibili"] = [(o["repo"], o["file"], o["commit"][:8]) for o in out if o["stato"] == "illeggibile"]

    # modelli
    per_modello = defaultdict(list)
    for o in out:
        per_modello[o["repo"]].append(o)
    analizzati = [r["repo"] for r in rows if "cambi" in r and r["rilascio"]]
    for nome in ("stretta", "larga"):
        m = [r for r in analizzati if any(o[nome] == "comportamento" for o in per_modello.get(r, []))]
        mg = [r for r in m if grande(r)]
        ng = sum(1 for r in analizzati if grande(r))
        res["modelli_" + nome] = {"modelli": len(m), "pct": 100 * len(m) / len(analizzati), "grandi": len(mg),
                                  "grandi_su": ng, "grandi_pct": 100 * len(mg) / ng}
    # chiavi: frequenza per file
    freq = defaultdict(Counter)
    for o in out:
        for k in o["chiavi"]:
            freq[o["file"]][k] += 1
    res["frequenza_chiavi"] = {f: dict(c.most_common()) for f, c in freq.items()}
    res["n_cambi_con_template"] = sum(1 for o in out if o["template"])
    # innocui (stretta) per tipo di chiavi
    res["innocui_stretta_chiavi"] = Counter(tuple(o["chiavi"]) for o in out if o["stretta"] == "innocuo").most_common()
    res["differenza_stretta_larga"] = Counter(
        (o["file"], tuple(k for k in o["chiavi"] if k in LARGA.get(o["file"], set())))
        for o in out if o["stretta"] == "innocuo" and o["larga"] == "comportamento").most_common()
    print(json.dumps(res, indent=1, ensure_ascii=False, default=list))
    if "--json" in sys.argv:
        dest = sys.argv[sys.argv.index("--json") + 1]
        with open(dest, "w", encoding="utf-8") as f:
            json.dump({"riassunto": res, "cambi": out}, f, indent=1, ensure_ascii=False, default=list)


if __name__ == "__main__":
    main()
