import json
import pathlib
import unittest

from linktrial.ctgov import is_oncology, normalize_state, normalize_study, parse_age, tumor_groups

FIX = pathlib.Path(__file__).parent / "fixtures" / "NCT07062965.json"


class Normalize(unittest.TestCase):
    def setUp(self):
        self.s = normalize_study(json.loads(FIX.read_text(encoding="utf-8")))

    def test_core(self):
        self.assertEqual(self.s["nct_id"], "NCT07062965")
        self.assertEqual(self.s["phases"], ["PHASE3"])
        self.assertEqual(self.s["min_age_years"], 18)
        self.assertIn("Mama", self.s["tumor_groups"])

    def test_only_brazil_sites(self):
        self.assertGreater(self.s["n_sites_br"], 0)
        self.assertTrue(all(site["state"] or site["city"] for site in self.s["sites_br"]))

    def test_criteria_structured(self):
        self.assertEqual(self.s["features"]["ecog_max"], 1)
        self.assertEqual(len(self.s["inclusion_criteria"]), 5)
        self.assertEqual(len(self.s["exclusion_criteria"]), 5)


class Helpers(unittest.TestCase):
    def test_parse_age(self):
        self.assertEqual(parse_age("18 Years"), 18)
        self.assertEqual(parse_age("6 Months"), 0.5)
        self.assertIsNone(parse_age(None))

    def test_groups(self):
        self.assertEqual(tumor_groups(["Non-small Cell Lung Cancer"]), ["Pulmão"])
        self.assertEqual(tumor_groups(["Advanced Solid Tumors"]), ["Tumores sólidos (geral)"])
        self.assertEqual(tumor_groups(["Multiple Myeloma"]), ["Hematológico"])

    def test_more_groups(self):
        self.assertEqual(tumor_groups(["Penile Squamous Cell Carcinoma"]), ["Urológico"])
        self.assertEqual(tumor_groups(["Polycythemia Vera"]), ["Hematológico"])
        self.assertEqual(tumor_groups(["Extrapulmonary Neuroendocrine Cancer (epNEC)"]), ["Neuroendócrino"])
        self.assertIn("Suporte/Qualidade de vida", tumor_groups(["Cancer Pain", "Palliative Care"]))

    def test_is_oncology(self):
        self.assertTrue(is_oncology(["Breast Cancer"], ""))
        self.assertTrue(is_oncology(["Polycythemia Vera"], ""))
        self.assertFalse(is_oncology(["Generalized Myasthenia Gravis"], "Study of drug X in gMG"))
        self.assertFalse(is_oncology(["Rheumatoid Arthritis"], ""))

    def test_states(self):
        self.assertEqual(normalize_state("Estado de Bahia"), "BA")
        self.assertEqual(normalize_state("Federal District"), "DF")
        self.assertEqual(normalize_state("São Paulo"), "SP")
        self.assertEqual(normalize_state("SP"), "SP")
        self.assertEqual(normalize_state("Rio Grande do Norte"), "RN")
        self.assertEqual(normalize_state("Paraná (PR)"), "PR")
        self.assertEqual(normalize_state("Recife - PE"), "PE")
        self.assertEqual(normalize_state("Vitoria ES"), "ES")
        self.assertEqual(normalize_state("Sao Paula"), "SP")
        self.assertEqual(normalize_state("Rio Grande Do Sil"), "RS")
        self.assertEqual(normalize_state("Belo Horizonte"), "MG")
        self.assertEqual(normalize_state("HIAE - Hospital Israelita Albert Einstein", "São Paulo"), "SP")
        self.assertEqual(normalize_state("", ""), "")

    def test_tnf_is_not_cancer(self):
        self.assertFalse(is_oncology(["Rheumatoid Arthritis"], "Anti-tumor necrosis factor switching"))


if __name__ == "__main__":
    unittest.main()
