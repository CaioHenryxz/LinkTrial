import json
import pathlib
import sqlite3
import unittest

from linktrial.ctgov import normalize_study
from linktrial.llm import CachedLLM, FakeLLM
from linktrial.match import evaluate_study, match_patient, patient_text, prefilter

FIX = pathlib.Path(__file__).parent / "fixtures" / "NCT07062965.json"  # HR+/HER2- breast, ECOG 0-1, phase 3

PATIENT = {
    "id": "SYN-T1", "age": 55, "sex": "FEMALE", "uf": "SP", "tumor_group": "Mama",
    "diagnosis": "Carcinoma de mama RH+ HER2- metastático", "ecog": 1,
    "biomarkers": {"RE": "positivo 90%", "HER2": "negativo (IHQ 1+)", "PIK3CA": "não detectado"},
    "clinical": {"Metástases cerebrais": "ausentes"},
    "prior_therapies": ["palbociclibe + letrozol (progressão em 10 meses)"],
}


class Match(unittest.TestCase):
    def setUp(self):
        self.study = normalize_study(json.loads(FIX.read_text(encoding="utf-8")))

    def test_prefilter_keeps_matching_group_and_drops_others(self):
        other = {**self.study, "nct_id": "NCTX", "tumor_groups": ["Pulmão"]}
        kept = [s["nct_id"] for _, s, _ in prefilter(PATIENT, [self.study, other])]
        self.assertEqual(kept, ["NCT07062965"])

    def test_prefilter_hard_filters(self):
        self.assertEqual(prefilter({**PATIENT, "ecog": 2}, [self.study]), [])
        self.assertEqual(prefilter({**PATIENT, "age": 16}, [self.study]), [])

    def test_evaluate_with_fake_llm_probable(self):
        n_i, n_e = len(self.study["inclusion_criteria"]), len(self.study["exclusion_criteria"])
        verdicts = {f"I{i}": ("MET", "ECOG: 1") for i in range(1, n_i + 1)}
        verdicts.update({f"E{i}": ("NOT_MET", "PIK3CA: não detectado") for i in range(1, n_e + 1)})
        r = evaluate_study(PATIENT, self.study, FakeLLM(verdicts))
        self.assertEqual(r["decision"], "MATCH_PROVAVEL")
        self.assertEqual(r["evidence_rejected"], 0)

    def test_hallucinated_evidence_cannot_make_match(self):
        n_i = len(self.study["inclusion_criteria"])
        verdicts = {f"I{i}": ("MET", "paciente com ótima função renal") for i in range(1, n_i + 1)}
        r = evaluate_study(PATIENT, self.study, FakeLLM(verdicts))
        self.assertNotEqual(r["decision"], "MATCH_PROVAVEL")
        self.assertEqual(r["evidence_rejected"], n_i)

    def test_exclusion_hit_blocks(self):
        r = evaluate_study(PATIENT, self.study, FakeLLM({"E1": ("MET", "PIK3CA: não detectado")}))
        self.assertEqual(r["decision"], "INELEGIVEL")
        self.assertEqual(r["blocking"], ["E1"])

    def test_verifier_disagreement_unblocks_to_pending(self):
        first = FakeLLM({"I3": ("NOT_MET", "Tratamentos prévios: palbociclibe + letrozol (progressão em 10 meses)")})
        second = FakeLLM({"I3": ("NOT_APPLICABLE", "")})
        r = evaluate_study(PATIENT, self.study, first, verifier=second)
        self.assertNotEqual(r["decision"], "INELEGIVEL")
        self.assertEqual(r["blockers_disputed"], ["I3"])
        self.assertTrue(any("divergência" in p for p in r["pending"]))

    def test_verifier_agreement_keeps_block(self):
        ev = "Tratamentos prévios: palbociclibe + letrozol (progressão em 10 meses)"
        r = evaluate_study(PATIENT, self.study, FakeLLM({"I3": ("NOT_MET", ev)}),
                           verifier=FakeLLM({"I3": ("NOT_MET", ev)}))
        self.assertEqual((r["decision"], r["blockers_disputed"]), ("INELEGIVEL", []))

    def test_verifier_only_sees_blocking_criteria(self):
        second = FakeLLM({"I3": ("NOT_APPLICABLE", "")})
        evaluate_study(PATIENT, self.study, FakeLLM({"I3": ("NOT_MET", "ECOG: 1")}), verifier=second)
        self.assertEqual(second.calls, 1)

    def test_cache_avoids_second_call(self):
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        fake = FakeLLM()
        llm = CachedLLM(fake, conn)
        match_patient(PATIENT, [self.study], llm)
        match_patient(PATIENT, [self.study], llm)
        self.assertEqual((fake.calls, llm.hits), (1, 1))

    def test_patient_text_is_line_based(self):
        self.assertIn("ECOG: 1", patient_text(PATIENT).splitlines())


if __name__ == "__main__":
    unittest.main()
