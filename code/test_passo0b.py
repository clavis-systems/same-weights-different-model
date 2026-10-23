"""Test della classificazione del passo 0b, senza rete. Eseguire dalla cartella: python test_passo0b.py"""
import json
import tempfile
import unittest
from pathlib import Path

import passo0b as p


class TestClassifica(unittest.TestCase):
    def test_chiavi_cambiate(self):
        self.assertEqual(p.chiavi_cambiate({"a": 1, "chat_template": "x"}, {"a": 1, "chat_template": "y"}),
                         ["chat_template"])

    def test_leggi_json_e_jinja(self):
        with tempfile.TemporaryDirectory() as d:
            j = Path(d) / "generation_config.json"
            j.write_text(json.dumps({"temperature": 0.7}), encoding="utf-8")
            t = Path(d) / "chat_template.jinja"
            t.write_text("{{ messages }}", encoding="utf-8")
            self.assertEqual(p.leggi(j), {"temperature": 0.7})
            self.assertEqual(p.leggi(t), {"chat_template": "{{ messages }}"})
            self.assertIsNone(p.leggi(Path(d) / "manca.json"))

    def test_classifica_comportamento_e_innocuo(self):
        with tempfile.TemporaryDirectory() as d:
            cart = Path(d)
            voci = [
                {"repo": "o/a", "file": "generation_config.json", "prima": "s1", "dopo": "s2",
                 "byte_prima": 10, "byte_dopo": 10},
                {"repo": "o/b", "file": "tokenizer_config.json", "prima": "s1", "dopo": "s2",
                 "byte_prima": 10, "byte_dopo": 10},
            ]
            (cart / "piano_0b.json").write_text(json.dumps({"voci": voci}), encoding="utf-8")
            contenuti = {("o__a", "s1"): {"temperature": 0.7, "transformers_version": "4"},
                         ("o__a", "s2"): {"temperature": 0.6, "transformers_version": "5"},
                         ("o__b", "s1"): {"model_max_length": 2048},
                         ("o__b", "s2"): {"model_max_length": 8192}}
            for (repo, sha), dati in contenuti.items():
                nome = "generation_config.json" if repo == "o__a" else "tokenizer_config.json"
                f = cart / "file0b" / repo / sha / nome
                f.parent.mkdir(parents=True)
                f.write_text(json.dumps(dati), encoding="utf-8")
            p.classifica(type("A", (), {"cartella": str(cart)})())
            righe = json.loads((cart / "classificazione_0b.json").read_text(encoding="utf-8"))
            self.assertEqual([r["classe"] for r in righe], ["comportamento", "innocuo"])
            self.assertEqual(righe[0]["chiavi_comportamento"], ["temperature"])


if __name__ == "__main__":
    unittest.main()
