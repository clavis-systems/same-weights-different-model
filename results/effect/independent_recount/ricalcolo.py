"""Ricalcolo indipendente del passo 1 di "stessi pesi, modello diverso".

Parte SOLO dalle regole della PREMESSA (sezione "Aggiunta 20/10, 15:15 - passo 1" e
deviazioni 1, 1b, 1c, 1d, 1e) e dalle risposte grezze in ../{A,B,C}_{prima,dopo,controllo}.jsonl.
Non usa ne' legge il codice del progetto. Solo libreria standard.

Uso:  python -X utf8 ricalcolo.py
Scrive miei_numeri.json accanto a questo file e stampa un riassunto.

Regole applicate (PREMESSA):
- punteggio: ultimo \\boxed{}, altrimenti ultimo numero; uguaglianza numerica con l'oro;
- McNemar esatto bilaterale sulle coppie discordanti prima/dopo;
- Holm sui 3 modelli (A, B, C), alfa 0,05;
- il caso vale come effetto del template solo se il controllo (prima vs controllo) NON e'
  significativo con lo stesso test; se lo e', il caso e' "non interpretabile".

Scelte mie (la premessa non le fissa): vedi le funzioni normalizza(), estrai() e VARIANTI.
"""
import json
import math
import os
import re
from fractions import Fraction

QUI = os.path.dirname(os.path.abspath(__file__))
DATI = os.path.normpath(os.path.join(QUI, ".."))
CASI = ["A", "B", "C"]
CONDIZIONI = ["prima", "dopo", "controllo"]
ALFA = 0.05
BS = chr(92)  # barra rovesciata, scritta cosi' per non avere problemi di escape


# ---------------------------------------------------------------- lettura dati
def carica(caso, cond):
    righe = {}
    with open(os.path.join(DATI, f"{caso}_{cond}.jsonl"), encoding="utf-8") as f:
        for riga in f:
            if riga.strip():
                r = json.loads(riga)
                if r["i"] in righe:
                    raise ValueError(f"indice doppio {caso} {cond} {r['i']}")
                righe[r["i"]] = r
    return righe


# ---------------------------------------------------------------- estrazione
RE_TESTO = re.compile(re.escape(BS) + r"(?:text|textbf|textit|mathrm|mbox)\s*\{([^{}]*)\}")
RE_FRAZ = re.compile(re.escape(BS) + r"[dt]?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}")
RE_NUM = re.compile(r"(-?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)")
BOXED = BS + "boxed"


def ultimo_boxed(s):
    """Contenuto dell'ultimo \\boxed{...} con graffe bilanciate; None se non c'e'."""
    ultimo = None
    idx = 0
    while True:
        j = s.find(BOXED, idx)
        if j < 0:
            break
        k = j + len(BOXED)
        while k < len(s) and s[k] == " ":
            k += 1
        if k < len(s) and s[k] == "{":
            prof = 0
            m = k
            while m < len(s):
                if s[m] == "{":
                    prof += 1
                elif s[m] == "}":
                    prof -= 1
                    if prof == 0:
                        break
                m += 1
            if prof == 0:
                ultimo = s[k + 1:m]
                idx = m
                continue
        idx = k
    return ultimo


def _frazione(m):
    a = m.group(1).strip().replace(",", "")
    b = m.group(2).strip().replace(",", "")
    try:
        v = Fraction(a) / Fraction(b)
    except (ValueError, ZeroDivisionError):
        return "§"  # segnaposto: frazione non numerica, nessun numero da estrarre
    return f"{float(v):.12f}"


def normalizza(t, testo="apri"):
    """Toglie decorazioni LaTeX. testo='apri': \\text{..} -> contenuto; 'scarta': eliminato."""
    if testo == "apri":
        t = RE_TESTO.sub(r" \1 ", t)
    else:
        t = RE_TESTO.sub(" ", t)
    t = RE_FRAZ.sub(_frazione, t)
    for x in (BS + "$", BS + "%", BS + ",", BS + "!"):
        t = t.replace(x, "")
    t = t.replace(BS + ";", " ").replace(BS + " ", " ")
    t = t.replace("$", "").replace("%", "")
    return t


def numeri(t):
    """Tutti i numeri del testo, come Fraction esatte (virgole delle migliaia ammesse)."""
    out = []
    for m in RE_NUM.finditer(t):
        neg = m.group(1) == "-"
        if neg and m.start() > 0:
            prec = t[m.start() - 1]
            if prec.isalnum() or prec in ")]}":
                neg = False  # "3-5": il meno e' un trattino
        v = Fraction(m.group(2).replace(",", ""))
        out.append(-v if neg else v)
    return out


def ultimo_numero(t):
    n = numeri(normalizza(t))
    return n[-1] if n else None


RE_BOX_UNA_ANNIDAZIONE = re.compile(re.escape(BS) + r"boxed\{((?:[^{}]|\{[^{}]*\})*)\}")
RE_ORARIO = re.compile(r"^\s*(\d{1,2}):\d{2}\b")


def estrai_primo_numero(testo):
    """Regola ALTERNATIVA, scritta dopo il confronto con effetto.py per spiegare le differenze:
    ultima scatola (una sola annidazione), virgole/$/% tolti, PRIMO numero della scatola (le frazioni
    valgono il numeratore); senza scatola: ultimo numero del testo."""
    scatole = RE_BOX_UNA_ANNIDAZIONE.findall(testo)
    s = scatole[-1] if scatole else None
    if s is None:
        nn = re.findall(r"-?\d[\d,]*(?:\.\d+)?", testo)
        s = nn[-1] if nn else None
    if s is None:
        return None
    s = s.replace(",", "").replace("$", "").replace(BS + "%", "").replace("%", "").strip().rstrip(".")
    m = re.search(r"-?\d+(?:\.\d+)?", s)
    return Fraction(m.group()) if m else None


def estrai(risposta, variante):
    """Ritorna (valore Fraction o None, fonte). fonte in
    boxed | boxed_non_numerico | ultimo_numero | nessuno."""
    if variante == "primo_numero_scatola":  # solo per le aggiunte dopo il confronto
        v = estrai_primo_numero(risposta)
        return v, ("boxed" if v is not None else "nessuno")
    if variante == "principale_orari":  # principale + "H:MM" vale H (aggiunta dopo il confronto)
        bb = ultimo_boxed(risposta)
        if bb is not None:
            m = RE_ORARIO.match(normalizza(bb))
            if m:
                return Fraction(int(m.group(1))), "boxed"
        return estrai(risposta, "principale")
    b = ultimo_boxed(risposta)
    if variante == "solo_testo":
        v = ultimo_numero(risposta)
        return v, ("ultimo_numero" if v is not None else "nessuno")
    if b is None:
        if variante == "solo_boxed":
            return None, "nessuno"
        v = ultimo_numero(risposta)
        return v, ("ultimo_numero" if v is not None else "nessuno")
    # c'e' un \boxed{}
    if BS + "overline" in b:  # decimale periodico: mai un intero
        v = None
    elif variante == "rigida":
        t = normalizza(b, testo="scarta").strip()
        m = re.fullmatch(r"(-?)(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)", t)
        v = None
        if m:
            v = Fraction(m.group(2).replace(",", ""))
            if m.group(1) == "-":
                v = -v
    else:
        n = numeri(normalizza(b))
        v = n[-1] if n else None
    if v is not None:
        return v, "boxed"
    if variante == "boxed_poi_testo":
        v = ultimo_numero(risposta)
        return v, ("ultimo_numero" if v is not None else "nessuno")
    return None, "boxed_non_numerico"


VARIANTI = {
    "principale": "ultimo \\boxed{} (ultimo numero dentro la scatola, frazioni calcolate, unita' ignorate); "
                  "senza scatola: ultimo numero del testo",
    "rigida": "scatola accettata solo se e' un numero puro (con $, %, unita' \\text, virgole delle migliaia); "
              "altrimenti sbagliata; senza scatola: ultimo numero",
    "solo_boxed": "come principale ma senza scatola = sbagliata (nessun ripiego sul testo)",
    "boxed_poi_testo": "come principale ma se la scatola non contiene numeri si ripiega sull'ultimo numero del testo",
    "solo_testo": "ignora la scatola: ultimo numero di tutto il testo",
}


def punteggia(righe, variante):
    """dict i -> (corretta bool, fonte)."""
    out = {}
    for i, r in righe.items():
        oro = Fraction(r["oro"].replace(",", ""))
        v, fonte = estrai(r["risposta"], variante)
        out[i] = (v is not None and v == oro, fonte)
    return out


# ---------------------------------------------------------------- statistica
def mcnemar_esatto(b, c):
    """p bilaterale esatto = min(1, 2 * P(X <= min(b,c))), X ~ Bin(b+c, 1/2)."""
    n = b + c
    if n == 0:
        return 1.0
    k = min(b, c)
    s = sum(math.comb(n, j) for j in range(k + 1))
    return float(min(Fraction(1), Fraction(2 * s, 2 ** n)))


def holm(ps):
    """Holm-Bonferroni: p corretti, nello stesso ordine di ps."""
    m = len(ps)
    ordine = sorted(range(m), key=lambda i: ps[i])
    out = [0.0] * m
    corrente = 0.0
    for rango, i in enumerate(ordine):
        corrente = max(corrente, min(1.0, (m - rango) * ps[i]))
        out[i] = corrente
    return out


def ic_diff_appaiata(b, c, n):
    """IC 95% (Wald) della differenza appaiata (b-c)/n, in punti percentuali."""
    d = (b - c) / n
    var = (b + c - (b - c) ** 2 / n) / n ** 2
    se = math.sqrt(max(var, 0.0))
    return [100 * (d - 1.959964 * se), 100 * (d + 1.959964 * se)]


def soglia_k(n_disc, alfa):
    """Il piu' grande k tale che 2*P(X<=k) <= alfa con X~Bin(n_disc,1/2); -1 se nessuno."""
    k_ok = -1
    for k in range(n_disc + 1):
        if mcnemar_esatto(k, n_disc - k) <= alfa:
            k_ok = k
        else:
            break
    return k_ok


def potenza(n_disc, n_tot, delta_punti, alfa):
    """Potenza del McNemar esatto, dato il numero di coppie discordanti e una differenza
    vera (dopo meno prima) di delta_punti punti su n_tot problemi."""
    if n_disc == 0:
        return 0.0
    k = soglia_k(n_disc, alfa)
    if k < 0:
        return 0.0
    delta = delta_punti / 100.0 * n_tot  # b - c atteso
    p1 = min(max((n_disc + delta) / (2 * n_disc), 0.0), 1.0)

    def pmf(j):
        return math.comb(n_disc, j) * p1 ** j * (1 - p1) ** (n_disc - j)

    return sum(pmf(j) for j in range(k + 1)) + sum(pmf(j) for j in range(n_disc - k, n_disc + 1))


def diff_minima(n_disc, n_tot, alfa):
    """Piu' piccola differenza |b-c| (con b+c=n_disc) significativa; in problemi e in punti."""
    for d in range(n_disc + 1):
        if (n_disc - d) % 2:
            continue
        c = (n_disc - d) // 2
        b = n_disc - c
        if mcnemar_esatto(b, c) <= alfa:
            return d, 100.0 * d / n_tot
    return None, None


# ---------------------------------------------------------------- analisi
def confronto(pu, pv, ids):
    """pu = prima, pv = altra condizione; b = prima giusta/altra sbagliata, c = viceversa."""
    b = sum(1 for i in ids if pu[i][0] and not pv[i][0])
    c = sum(1 for i in ids if (not pu[i][0]) and pv[i][0])
    n = len(ids)
    return {
        "b_prima_giusta_altra_sbagliata": b,
        "c_prima_sbagliata_altra_giusta": c,
        "discordanti": b + c,
        "diff_punti_altra_meno_prima": 100.0 * (c - b) / n,
        "ic95_diff_punti": ic_diff_appaiata(c, b, n),
        "p_mcnemar": mcnemar_esatto(b, c),
    }


def analizza_variante(dati, variante, ids_per_caso):
    pun = {c: {cond: punteggia(dati[c][cond], variante) for cond in CONDIZIONI} for c in CASI}
    out = {}
    for c in CASI:
        ids = ids_per_caso[c]
        acc = {}
        for cond in CONDIZIONI:
            k = sum(1 for i in ids if pun[c][cond][i][0])
            acc[cond] = {"corrette": k, "accuratezza_%": 100.0 * k / len(ids)}
        out[c] = {
            "n_comuni": len(ids),
            "accuratezza": acc,
            "dopo_vs_prima": confronto(pun[c]["prima"], pun[c]["dopo"], ids),
            "controllo_vs_prima": confronto(pun[c]["prima"], pun[c]["controllo"], ids),
        }
    p_dopo = [out[c]["dopo_vs_prima"]["p_mcnemar"] for c in CASI]
    p_h = holm(p_dopo)
    for c, ph in zip(CASI, p_h):
        o = out[c]
        o["p_holm_dopo_vs_prima"] = ph
        p_ctrl = o["controllo_vs_prima"]["p_mcnemar"]
        o["controllo_significativo"] = p_ctrl < ALFA
        diff = o["dopo_vs_prima"]["diff_punti_altra_meno_prima"]
        if p_ctrl < ALFA:
            o["verdetto"] = "non interpretabile (controllo significativo)"
        elif ph < ALFA:
            o["verdetto"] = "effetto del template: dopo " + (">" if diff > 0 else "<") + " prima"
        else:
            o["verdetto"] = "nessun effetto dimostrato"
    return out, pun


def descrittive(dati, pun_princ, ids_per_caso):
    out = {}
    for c in CASI:
        ids = ids_per_caso[c]
        o = {}
        for cond in CONDIZIONI:
            righe = dati[c][cond]
            p = pun_princ[c][cond]
            senza_box = [i for i in ids if ultimo_boxed(righe[i]["risposta"]) is None]
            box_non_num = [i for i in ids if p[i][1] == "boxed_non_numerico"]
            nessuno = [i for i in ids if p[i][1] == "nessuno"]
            tronc = [i for i in ids if righe[i]["troncata"]]
            d = {
                "senza_boxed": len(senza_box),
                "senza_boxed_%": 100.0 * len(senza_box) / len(ids),
                "boxed_non_numerico": len(box_non_num),
                "nessun_numero_estraibile": len(nessuno),
                "troncate": len(tronc),
                "troncate_%": 100.0 * len(tronc) / len(ids),
                "senza_boxed_e_troncate": len(set(senza_box) & set(tronc)),
                "senza_boxed_non_troncate": len(set(senza_box) - set(tronc)),
                "token_medi": sum(righe[i]["n_token"] for i in ids) / len(ids),
                "punteggiate_col_ripiego_ultimo_numero": sum(1 for i in ids if p[i][1] == "ultimo_numero"),
                "corrette_col_ripiego": sum(1 for i in ids if p[i][1] == "ultimo_numero" and p[i][0]),
                "corrette_tra_troncate": sum(1 for i in tronc if p[i][0]),
            }
            if c == "C":
                d["con_</think>"] = sum(1 for i in ids if "</think>" in righe[i]["risposta"])
                d["iniziano_con_<think>"] = sum(1 for i in ids if righe[i]["risposta"].startswith("<think>"))
            o[cond] = d

        # uscite identiche (per C: "dopo" riceve <think>\n nel prompt, lo si rimette davanti)
        def testo(cond, i):
            t = dati[c][cond][i]["risposta"]
            if c == "C" and cond == "dopo" and not t.startswith("<think>"):
                t = "<think>\n" + t
            return t

        o["uscite_identiche"] = {
            "prima=dopo": sum(1 for i in ids if testo("prima", i) == testo("dopo", i)),
            "prima=controllo": sum(1 for i in ids if testo("prima", i) == testo("controllo", i)),
            "dopo=controllo": sum(1 for i in ids if testo("dopo", i) == testo("controllo", i)),
        }

        # prefisso comune (in caratteri): dove le due uscite cominciano a divergere
        def prefisso(a, b):
            n = min(len(a), len(b))
            k = 0
            while k < n and a[k] == b[k]:
                k += 1
            return k

        pref = {}
        for x, y in (("prima", "dopo"), ("prima", "controllo"), ("dopo", "controllo")):
            L = sorted(prefisso(testo(x, i), testo(y, i)) for i in ids)
            pref[f"{x}-{y}"] = {
                "mediana_caratteri": L[len(L) // 2],
                "quota_con_almeno_100_caratteri_uguali_%": 100.0 * sum(1 for v in L if v >= 100) / len(L),
                "quota_con_almeno_500_caratteri_uguali_%": 100.0 * sum(1 for v in L if v >= 500) / len(L),
            }
        o["prefisso_comune"] = pref

        # l'assenza di \boxed{} cambia con il template? (descrittivo, non nella premessa)
        sb = {cond: {i for i in ids if ultimo_boxed(dati[c][cond][i]["risposta"]) is None} for cond in CONDIZIONI}
        o["senza_boxed_mcnemar"] = {}
        for altra in ("dopo", "controllo"):
            solo_p = len(sb["prima"] - sb[altra])
            solo_a = len(sb[altra] - sb["prima"])
            o["senza_boxed_mcnemar"][f"prima_vs_{altra}"] = {
                "senza_box_solo_in_prima": solo_p, f"senza_box_solo_in_{altra}": solo_a,
                "p_mcnemar": mcnemar_esatto(solo_p, solo_a)}
        out[c] = o
    return out


def analisi_troncate(dati, pun_princ, ids_per_caso):
    """Quanto pesano le risposte troncate (rilevante soprattutto per C)."""
    out = {}
    for c in CASI:
        ids = ids_per_caso[c]
        tr = {cond: {i for i in ids if dati[c][cond][i]["troncata"]} for cond in CONDIZIONI}
        mai = [i for i in ids if not any(i in tr[cond] for cond in CONDIZIONI)]
        almeno = [i for i in ids if any(i in tr[cond] for cond in CONDIZIONI)]
        o = {"n_mai_troncate_in_nessuna_condizione": len(mai), "n_troncate_in_almeno_una": len(almeno)}
        o["accuratezza_sulle_mai_troncate"] = {
            cond: 100.0 * sum(1 for i in mai if pun_princ[c][cond][i][0]) / len(mai) for cond in CONDIZIONI
        }
        o["dopo_vs_prima_solo_mai_troncate"] = confronto(pun_princ[c]["prima"], pun_princ[c]["dopo"], mai)
        o["controllo_vs_prima_solo_mai_troncate"] = confronto(pun_princ[c]["prima"], pun_princ[c]["controllo"], mai)
        # coppie discordanti dopo/prima in cui almeno una delle due risposte e' troncata
        disc = [i for i in ids if pun_princ[c]["prima"][i][0] != pun_princ[c]["dopo"][i][0]]
        o["discordanti_prima_dopo_con_una_troncata"] = sum(1 for i in disc if i in tr["prima"] or i in tr["dopo"])
        o["discordanti_prima_dopo_totali"] = len(disc)
        disc2 = [i for i in ids if pun_princ[c]["prima"][i][0] != pun_princ[c]["controllo"][i][0]]
        o["discordanti_prima_controllo_con_una_troncata"] = sum(
            1 for i in disc2 if i in tr["prima"] or i in tr["controllo"])
        o["discordanti_prima_controllo_totali"] = len(disc2)
        # il template cambia il tasso di troncatura? (McNemar sulla troncatura)
        for altra in ("dopo", "controllo"):
            b = len(tr["prima"] - tr[altra])
            cc = len(tr[altra] - tr["prima"])
            o[f"troncatura_prima_vs_{altra}"] = {
                "troncate_solo_in_prima": b, f"troncate_solo_in_{altra}": cc, "p_mcnemar": mcnemar_esatto(b, cc)}
        # scenario estremo: le troncate (mai completate) sarebbero giuste con prob. q?
        # Limite superiore del possibile effetto: tutte le coppie con una sola troncata
        # decise a favore di "dopo" (o di "prima").
        sole = [i for i in ids if (i in tr["prima"]) != (i in tr["dopo"])]
        o["coppie_con_una_sola_troncata_prima_dopo"] = len(sole)
        out[c] = o
    return out


def potenze(risultati_princ):
    out = {}
    for c in CASI:
        r = risultati_princ[c]
        n = r["n_comuni"]
        o = {}
        for nome, chiave in (("rumore_prima_vs_controllo", "controllo_vs_prima"),
                             ("osservato_prima_vs_dopo", "dopo_vs_prima")):
            nd = r[chiave]["discordanti"]
            d05, p05 = diff_minima(nd, n, 0.05)
            d017, p017 = diff_minima(nd, n, 0.05 / 3)
            o[nome] = {
                "discordanti": nd,
                "diff_minima_significativa_alfa_0.05": {"problemi": d05, "punti": p05},
                "diff_minima_significativa_alfa_0.0167": {"problemi": d017, "punti": p017},
                "potenza_alfa_0.05": {f"{dp}_punti": potenza(nd, n, dp, 0.05) for dp in (1, 2, 3)},
                "potenza_alfa_0.0167": {f"{dp}_punti": potenza(nd, n, dp, 0.05 / 3) for dp in (1, 2, 3)},
            }
        out[c] = o
    return out


def main():
    dati = {c: {cond: carica(c, cond) for cond in CONDIZIONI} for c in CASI}
    ids_per_caso = {}
    for c in CASI:
        comuni = set(dati[c]["prima"]) & set(dati[c]["dopo"]) & set(dati[c]["controllo"])
        ids_per_caso[c] = sorted(comuni)
        # l'oro deve essere uguale nelle tre condizioni
        for i in comuni:
            assert dati[c]["prima"][i]["oro"] == dati[c]["dopo"][i]["oro"] == dati[c]["controllo"][i]["oro"]

    risultati = {}
    pun_per_variante = {}
    for v in VARIANTI:
        risultati[v], pun_per_variante[v] = analizza_variante(dati, v, ids_per_caso)

    princ = risultati["principale"]
    pun_princ = pun_per_variante["principale"]

    # quante risposte cambiano esito fra varianti (dipendenza dall'estrazione)
    dip = {}
    for c in CASI:
        dip[c] = {}
        for cond in CONDIZIONI:
            base = pun_princ[c][cond]
            dip[c][cond] = {}
            for v in VARIANTI:
                if v == "principale":
                    continue
                altro = pun_per_variante[v][c][cond]
                dip[c][cond][v] = sum(1 for i in ids_per_caso[c] if base[i][0] != altro[i][0])

    out = {
        "nota": "Ricalcolo indipendente, codice proprio (ricalcolo.py). Generato senza aver letto effetto.py ne' analisi.json.",
        "varianti_di_punteggio": VARIANTI,
        "problemi_comuni": {c: len(ids_per_caso[c]) for c in CASI},
        "principale": princ,
        "sensibilita_estrazione": risultati,
        "esiti_diversi_rispetto_alla_principale": dip,
        "descrittive": descrittive(dati, pun_princ, ids_per_caso),
        "troncate": analisi_troncate(dati, pun_princ, ids_per_caso),
        "potenza": potenze(princ),
    }
    with open(os.path.join(QUI, "miei_numeri.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # riassunto a video
    print("VARIANTE principale")
    for c in CASI:
        r = princ[c]
        a = r["accuratezza"]
        print(f"{c}: n={r['n_comuni']}  prima={a['prima']['corrette']} ({a['prima']['accuratezza_%']:.2f}%)"
              f"  dopo={a['dopo']['corrette']} ({a['dopo']['accuratezza_%']:.2f}%)"
              f"  controllo={a['controllo']['corrette']} ({a['controllo']['accuratezza_%']:.2f}%)")
        for k in ("dopo_vs_prima", "controllo_vs_prima"):
            x = r[k]
            print(f"   {k}: b={x['b_prima_giusta_altra_sbagliata']} c={x['c_prima_sbagliata_altra_giusta']}"
                  f" disc={x['discordanti']} diff={x['diff_punti_altra_meno_prima']:+.2f} pt"
                  f" IC95=[{x['ic95_diff_punti'][0]:+.2f},{x['ic95_diff_punti'][1]:+.2f}] p={x['p_mcnemar']:.4f}")
        print(f"   Holm(dopo vs prima)={r['p_holm_dopo_vs_prima']:.4f}  controllo signif.={r['controllo_significativo']}"
              f"  -> {r['verdetto']}")
    print()
    for v in VARIANTI:
        if v == "principale":
            continue
        print("VARIANTE", v)
        for c in CASI:
            r = risultati[v][c]
            a = r["accuratezza"]
            print(f"  {c}: {a['prima']['corrette']}/{a['dopo']['corrette']}/{a['controllo']['corrette']}"
                  f"  p_dopo={r['dopo_vs_prima']['p_mcnemar']:.4f} Holm={r['p_holm_dopo_vs_prima']:.4f}"
                  f" p_ctrl={r['controllo_vs_prima']['p_mcnemar']:.4f} -> {r['verdetto']}")
    print("\nsalvato miei_numeri.json")
    aggiunte(dati, ids_per_caso)


def aggiunte(dati, ids_per_caso):
    """Calcoli aggiunti DOPO il confronto con analisi.json / effetto.py (file separato,
    miei_numeri.json resta quello scritto prima del confronto)."""
    out = {"nota": "Aggiunte scritte dopo aver aperto analisi.json ed effetto.py, per spiegare le differenze "
                   "e per la descrittiva 'ragionamento vuoto'."}
    # ragionamento vuoto (descrittiva della premessa): testo prima di </think> (senza <think>) lungo < 20 caratteri
    vuoto = {}
    for c in CASI:
        vuoto[c] = {}
        for cond in CONDIZIONI:
            n = 0
            for i in ids_per_caso[c]:
                t = dati[c][cond][i]["risposta"]
                if "</think>" in t and len(t.split("</think>")[0].replace("<think>", "").strip()) < 20:
                    n += 1
            vuoto[c][cond] = n
    out["ragionamento_vuoto"] = vuoto
    # punto di partenza nel testo: in "dopo" di C il prompt contiene gia' <think>\n
    out["C_inizio_risposta"] = {
        cond: {
            "iniziano_con_<think>\\nOkay": sum(1 for i in ids_per_caso["C"]
                                              if dati["C"][cond][i]["risposta"].startswith("<think>\nOkay")),
            "iniziano_con_Okay": sum(1 for i in ids_per_caso["C"]
                                     if dati["C"][cond][i]["risposta"].startswith("Okay")),
        } for cond in CONDIZIONI}
    # regole alternative
    for nome in ("primo_numero_scatola", "principale_orari"):
        ris, _ = analizza_variante(dati, nome, ids_per_caso)
        out[nome] = ris
    with open(os.path.join(QUI, "miei_numeri_aggiunte.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print("\nAGGIUNTE (dopo il confronto)")
    print("ragionamento vuoto:", json.dumps(vuoto))
    for nome in ("primo_numero_scatola", "principale_orari"):
        print(nome)
        for c in CASI:
            r = out[nome][c]
            a = r["accuratezza"]
            print(f"  {c}: {a['prima']['corrette']}/{a['dopo']['corrette']}/{a['controllo']['corrette']}"
                  f"  dopo_vs_prima b={r['dopo_vs_prima']['b_prima_giusta_altra_sbagliata']}"
                  f" c={r['dopo_vs_prima']['c_prima_sbagliata_altra_giusta']} p={r['dopo_vs_prima']['p_mcnemar']:.4f}"
                  f" Holm={r['p_holm_dopo_vs_prima']:.4f}"
                  f" ctrl b={r['controllo_vs_prima']['b_prima_giusta_altra_sbagliata']}"
                  f" c={r['controllo_vs_prima']['c_prima_sbagliata_altra_giusta']}"
                  f" p={r['controllo_vs_prima']['p_mcnemar']:.4f} -> {r['verdetto']}")


if __name__ == "__main__":
    main()
