"""Test della logica del censimento, senza rete. Eseguire dalla cartella: python test_censimento.py"""
import unittest

import censimento as c


class TestBisezione(unittest.TestCase):
    def test_punti_di_cambio_trova_tutti_i_salti(self):
        valori = ["a", "a", "b", "b", "b", "c", "d", "d"]
        self.assertEqual(c.punti_di_cambio(len(valori), lambda i: valori[i], 0), [2, 5, 6])

    def test_punti_di_cambio_parte_dal_rilascio(self):
        valori = ["x", "y", "y", "z"]
        self.assertEqual(c.punti_di_cambio(len(valori), lambda i: valori[i], 1), [3])

    def test_ritorno_a_b_a_sfugge_come_dichiarato(self):
        valori = ["a", "b", "a"]
        self.assertEqual(c.punti_di_cambio(len(valori), lambda i: valori[i], 0), [])

    def test_primo_indice(self):
        pesi = [False, False, True, True]
        self.assertEqual(c.primo_indice(4, lambda i: pesi[i]), 2)
        self.assertIsNone(c.primo_indice(3, lambda i: False))


class TestImpronta(unittest.TestCase):
    def test_divide_primari_secondari_pesi(self):
        voci = [
            {"type": "file", "path": "tokenizer_config.json", "oid": "t1"},
            {"type": "file", "path": "config.json", "oid": "c1"},
            {"type": "file", "path": "model.safetensors", "oid": "p", "lfs": {"oid": "sha"}},
            {"type": "directory", "path": "original", "oid": "d"},
            {"type": "file", "path": "README.md", "oid": "r"},
        ]
        f = c.impronta(voci)
        self.assertEqual(f["primari"], {"tokenizer_config.json": "t1"})
        self.assertEqual(f["secondari"], {"config.json": "c1"})
        self.assertEqual(f["pesi"], {"model.safetensors": "sha"})

    def test_cambiati_vede_aggiunte_e_rimozioni(self):
        self.assertEqual(c.cambiati({"a": 1, "b": 2}, {"b": 3, "c": 4}), ["a", "b", "c"])


class TestMisure(unittest.TestCase):
    def test_conta_solo_cambi_primari_a_pesi_identici(self):
        righe = [
            {"repo": "o/a", "rilascio": {"data": "2026-01-01T00:00:00Z"},
             "cambi": [{"primari": ["generation_config.json"], "pesi_cambiati": False,
                        "data": "2026-01-11T00:00:00Z"}]},
            {"repo": "o/b", "rilascio": {"data": "2026-01-01T00:00:00Z"},
             "cambi": [{"primari": ["tokenizer_config.json"], "pesi_cambiati": True,
                        "data": "2026-01-02T00:00:00Z"}]},
            {"repo": "o/c", "rilascio": {"data": "2026-01-01T00:00:00Z"}, "cambi": []},
            {"repo": "o/d", "non_accessibile": 401},
        ]
        m = c.misure(righe)
        self.assertEqual(m["analizzati"], 3)
        self.assertEqual(m["M1_modelli_con_cambio_primario_a_pesi_identici"], 1)
        self.assertEqual(m["M2_per_file"]["generation_config.json"], 1)
        self.assertEqual(m["M2_per_file"]["tokenizer_config.json"], 0)
        self.assertEqual(m["M3_giorni_mediana"], 10.0)
        self.assertEqual(m["M1b_oltre_7_giorni"], 1)


if __name__ == "__main__":
    unittest.main()
