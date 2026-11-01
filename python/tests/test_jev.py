import json
import pathlib
import sqlite3
import unittest

from linktrial.ctgov import normalize_study
from linktrial.jev import FakeJev, JevClient, build_questions, consensus, jev_rank_key, triage
from tests.test_match import PATIENT

FIX = pathlib.Path(__file__).parent / "fixtures" / "NCT07062965.json"


def ans(choice, p=1.0):
    probs = {k: 0.0 for k in ("MET", "NOT_MET", "UNKNOWN", "NOT_APPLICABLE")}
    probs[choice] = p
    rest = [k for k in probs if k != choice]
    for k in rest:
        probs[k] = round((1 - p) / len(rest), 4)
    return {"type": "choice", "choice": choice, "confidence": p, "probabilities": probs}


class Questions(unittest.TestCase):
    def setUp(self):
        self.study = normalize_study(json.loads(FIX.read_text(encoding="utf-8")))

    def test_one_choice_question_per_criterion_with_polarity(self):
        q = build_questions(self.study)
        n = len(self.study["inclusion_criteria"]) + len(self.study["exclusion_criteria"])
        self.assertEqual(len(q), n)
        self.assertEqual(q["I1"]["type"], "choice")
        self.assertEqual(set(q["I1"]["criteria"]), {"MET", "NOT_MET", "UNKNOWN", "NOT_APPLICABLE"})
        self.assertIn("INCLUSÃO", q["I1"]["instructions"]["question"])
        self.assertIn("EXCLUSÃO", q["E1"]["instructions"]["question"])

    def test_triage_counts_confident_blocks(self):
        fake = FakeJev({"I1": ans("NOT_MET", 0.95), "E2": ans("MET", 0.9), "I2": ans("NOT_MET", 0.5)})
        t = triage(PATIENT, self.study, fake)
        self.assertEqual(sorted(t["confident_blocks"]), ["E2", "I1"])
        self.assertLess(t["jev_score"], 1.0)

    def test_cohort_scoped_criteria_do_not_count_as_blocks(self):
        study = {**self.study, "inclusion_criteria": ["Adults", "Part C: <50%.", "Cohort 2: EGFR exon 20"],
                 "exclusion_criteria": []}
        fake = FakeJev({"I2": ans("NOT_MET", 0.99), "I3": ans("NOT_MET", 0.99), "I1": ans("MET")})
        t = triage(PATIENT, study, fake)
        self.assertEqual(t["confident_blocks"], [])
        self.assertEqual(sorted(t["cohort_scoped_blocks"]), ["I2", "I3"])

    def test_rank_prefers_fewer_blocks(self):
        a = {"confident_blocks": [], "jev_score": 0.6}
        b = {"confident_blocks": ["I1"], "jev_score": 0.99}
        self.assertLess(jev_rank_key(a), jev_rank_key(b))

    def test_client_cache(self):
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        calls = []
        client = JevClient(api_key="x", conn=conn, transport=lambda body: calls.append(body) or
                           {"model": "jev-test", "answers": {"I1": ans("MET")}})
        client.decide({"p": 1}, {"I1": {"type": "choice"}})
        client.decide({"p": 1}, {"I1": {"type": "choice"}})
        self.assertEqual((len(calls), client.hits), (1, 1))


class Consensus(unittest.TestCase):
    def row(self, cid, verdict):
        return {"id": cid, "criterion": "c", "verdict": verdict, "evidence": "e", "missing_data": ""}

    def test_block_needs_jev_agreement(self):
        rows = [self.row("I1", "NOT_MET")]
        out = consensus(rows, {"I1": ans("MET", 0.95)})
        self.assertEqual(out[0]["verdict"], "UNKNOWN")
        self.assertIn("divergência", out[0]["missing_data"])

    def test_block_kept_when_jev_agrees(self):
        out = consensus([self.row("E1", "MET")], {"E1": ans("MET", 0.8)})
        self.assertEqual(out[0]["verdict"], "MET")
        self.assertEqual(out[0]["jev"]["choice"], "MET")

    def test_block_kept_when_jev_top_choice_agrees_even_below_threshold(self):
        # real case NCT04669873 I13 "No hematogenous metastases": Jev NOT_MET p=0.69
        out = consensus([self.row("I1", "NOT_MET")], {"I1": ans("NOT_MET", 0.55)})
        self.assertEqual(out[0]["verdict"], "NOT_MET")

    def test_block_dropped_when_jev_top_choice_is_not_blocking(self):
        out = consensus([self.row("I1", "NOT_MET")], {"I1": ans("UNKNOWN", 0.6)})
        self.assertEqual(out[0]["verdict"], "UNKNOWN")

    def test_non_blocking_verdict_untouched_but_annotated(self):
        out = consensus([self.row("I1", "MET")], {"I1": ans("UNKNOWN", 0.9)})
        self.assertEqual(out[0]["verdict"], "MET")
        self.assertEqual(out[0]["jev"]["choice"], "UNKNOWN")

    def test_missing_jev_answer_keeps_llm(self):
        out = consensus([self.row("I1", "NOT_MET")], {})
        self.assertEqual(out[0]["verdict"], "NOT_MET")


class Pipeline(unittest.TestCase):
    def test_jev_triage_then_deep_review_and_consensus(self):
        from linktrial.llm import FakeLLM
        from linktrial.match import match_patient
        base = normalize_study(json.loads(FIX.read_text(encoding="utf-8")))
        good = {**base, "nct_id": "NCTGOOD"}
        bad = {**base, "nct_id": "NCTBAD"}

        class TwoStudyJev(FakeJev):
            def decide(self, state, questions):
                self.calls += 1
                blocked = "NCTBAD" in json.dumps(questions) or False
                return {"answers": {q: ans("UNKNOWN", 0.9) for q in questions}}

        jev = TwoStudyJev()
        # LLM claims I1 blocks; Jev (UNKNOWN) does not agree -> consensus turns it into a pending item
        llm = FakeLLM({"I1": ("NOT_MET", "ECOG: 1")})
        rep = match_patient(PATIENT, [good, bad], llm, limit=10, jev=jev, deep_k=1)
        self.assertEqual(jev.calls, 2)
        self.assertEqual(rep["n_deep"], 1)
        self.assertEqual(len(rep["triage_only"]), 1)
        r = rep["results"][0]
        self.assertNotEqual(r["decision"], "INELEGIVEL")
        self.assertEqual(r["llm_jev_disagreements"], ["I1"])


if __name__ == "__main__":
    unittest.main()
