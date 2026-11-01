import unittest

from linktrial.decision import decide, decide_with_cohorts, validate_evidence

PATIENT_TEXT = "Idade: 62\nECOG: 1\nKRAS: G12C mutado\nMetástases cerebrais: ausentes"


def v(cid, verdict, evidence="", missing=""):
    return {"id": cid, "verdict": verdict, "evidence": evidence, "missing_data": missing}


class Evidence(unittest.TestCase):
    def test_fabricated_evidence_is_downgraded(self):
        out = validate_evidence([v("I1", "MET", "EGFR selvagem")], PATIENT_TEXT)
        self.assertEqual(out[0]["verdict"], "UNKNOWN")
        self.assertTrue(out[0]["evidence_rejected"])

    def test_real_evidence_kept_case_and_space_insensitive(self):
        out = validate_evidence([v("I1", "MET", "kras:  g12c MUTADO")], PATIENT_TEXT)
        self.assertEqual(out[0]["verdict"], "MET")

    def test_met_without_evidence_becomes_unknown(self):
        out = validate_evidence([v("I1", "MET", "")], PATIENT_TEXT)
        self.assertEqual(out[0]["verdict"], "UNKNOWN")

    def test_not_applicable_needs_no_evidence(self):
        out = validate_evidence([v("I1", "NOT_APPLICABLE", "")], PATIENT_TEXT)
        self.assertEqual(out[0]["verdict"], "NOT_APPLICABLE")


class Decide(unittest.TestCase):
    def test_exclusion_met_is_ineligible(self):
        d = decide([v("I1", "MET", "ECOG: 1")], [v("E1", "MET", "KRAS: G12C mutado")])
        self.assertEqual(d["decision"], "INELEGIVEL")
        self.assertIn("E1", d["blocking"])

    def test_inclusion_not_met_is_ineligible(self):
        d = decide([v("I1", "NOT_MET", "ECOG: 1")], [])
        self.assertEqual(d["decision"], "INELEGIVEL")

    def test_all_known_is_probable(self):
        d = decide([v("I1", "MET", "ECOG: 1")], [v("E1", "NOT_MET", "Metástases cerebrais: ausentes")])
        self.assertEqual(d["decision"], "MATCH_PROVAVEL")
        self.assertEqual(d["pending"], [])

    def test_few_unknowns_is_possible_with_checklist(self):
        d = decide([v("I1", "MET", "ECOG: 1"), v("I2", "UNKNOWN", missing="Creatinina")],
                   [v("E1", "UNKNOWN", missing="Hepatite B")])
        self.assertEqual(d["decision"], "MATCH_POSSIVEL")
        self.assertEqual(d["pending"], ["Creatinina", "Hepatite B"])

    def test_many_unknowns_needs_review(self):
        inc = [v(f"I{i}", "UNKNOWN", missing=f"dado {i}") for i in range(8)]
        self.assertEqual(decide(inc, [])["decision"], "REVISAO_NECESSARIA")

    def test_order_for_ranking(self):
        a = decide([v("I1", "MET", "x")], [])
        b = decide([v("I1", "UNKNOWN", missing="y")], [])
        self.assertLess(a["rank_key"], b["rank_key"])


def c(cid, verdict, cohort, evidence="ev", missing=""):
    return {**v(cid, verdict, evidence, missing), "cohort": cohort}


class Cohorts(unittest.TestCase):
    def test_block_in_one_cohort_does_not_block_study(self):
        inc = [c("I1", "MET", ""), c("I2", "MET", "Part A"), c("I3", "NOT_MET", "Part C")]
        d = decide_with_cohorts(inc, [])
        self.assertEqual(d["decision"], "MATCH_PROVAVEL")
        self.assertEqual(d["cohort"], "Part A")

    def test_block_in_all_cohorts_blocks(self):
        inc = [c("I1", "MET", ""), c("I2", "NOT_MET", "Part A"), c("I3", "NOT_MET", "Part B")]
        d = decide_with_cohorts(inc, [])
        self.assertEqual(d["decision"], "INELEGIVEL")

    def test_general_block_always_blocks(self):
        inc = [c("I1", "NOT_MET", ""), c("I2", "MET", "Part A")]
        self.assertEqual(decide_with_cohorts(inc, [])["decision"], "INELEGIVEL")

    def test_no_cohorts_same_as_decide(self):
        inc = [c("I1", "MET", ""), c("I2", "UNKNOWN", "", missing="x")]
        self.assertEqual(decide_with_cohorts(inc, [])["decision"], decide(inc, [])["decision"])

    def test_cohort_exclusion_only_hits_that_cohort(self):
        inc = [c("I1", "MET", ""), c("I2", "MET", "Coorte 1"), c("I3", "MET", "Coorte 2")]
        exc = [c("E1", "MET", "Coorte 1")]
        d = decide_with_cohorts(inc, exc)
        self.assertEqual((d["decision"], d["cohort"]), ("MATCH_PROVAVEL", "Coorte 2"))

    def test_nested_cohort_inherits_parent_criteria(self):
        inc = [c("I1", "MET", "Fase 2"),
               c("I2", "UNKNOWN", "Fase 3", missing="PD-L1"),
               c("I3", "MET", "Fase 3 > sem metástase cerebral")]
        d = decide_with_cohorts(inc, [])
        # leaf "Fase 3 > sem..." must carry parent "Fase 3" pending item; parent alone is not evaluated
        self.assertEqual(sorted(d["cohorts_evaluated"]), ["Fase 2", "Fase 3 > sem metástase cerebral"])
        self.assertEqual(d["cohort"], "Fase 2")
        inc[0] = c("I1", "NOT_MET", "Fase 2")
        d = decide_with_cohorts(inc, [])
        self.assertEqual((d["cohort"], d["pending"]), ("Fase 3 > sem metástase cerebral", ["PD-L1"]))


if __name__ == "__main__":
    unittest.main()
