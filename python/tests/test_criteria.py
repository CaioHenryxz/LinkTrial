import unittest

from linktrial.criteria import split_criteria, extract_features

TEXT = """Inclusion Criteria:

* Confirmed diagnosis of HR-positive HER2-negative breast cancer with evidence of locally advanced or metastatic disease.
* Measurable disease per RECIST v1.1
* Eastern Cooperative Oncology Group (ECOG) Performance Status (PS) 0 or 1.

Exclusion Criteria:

* Documented detectable PIK3CA/AKT1/PTEN alterations in tissue
* Received greater than two prior lines of systemic therapy
* Active brain metastases
"""


class SplitCriteria(unittest.TestCase):
    def test_split_bullets(self):
        inc, exc = split_criteria(TEXT)
        self.assertEqual(len(inc), 3)
        self.assertEqual(len(exc), 3)
        self.assertTrue(inc[0].startswith("Confirmed diagnosis"))
        self.assertEqual(exc[2], "Active brain metastases")

    def test_no_headers_goes_to_inclusion(self):
        inc, exc = split_criteria("* Age 18 or older\n* ECOG 0-2")
        self.assertEqual(inc, ["Age 18 or older", "ECOG 0-2"])
        self.assertEqual(exc, [])

    def test_numbered_and_subbullets(self):
        txt = "Inclusion Criteria:\n1. Adults\n2. Histology:\n   * adenocarcinoma\nExclusion criteria:\n- Pregnancy"
        inc, exc = split_criteria(txt)
        self.assertEqual(inc, ["Adults", "Histology: (1) adenocarcinoma"])
        self.assertEqual(exc, ["Pregnancy"])

    def test_empty(self):
        self.assertEqual(split_criteria(""), ([], []))
        self.assertEqual(split_criteria(None), ([], []))


class Features(unittest.TestCase):
    def setUp(self):
        inc, exc = split_criteria(TEXT)
        self.f = extract_features(inc, exc)

    def test_ecog(self):
        self.assertEqual(self.f["ecog_max"], 1)

    def test_ecog_range(self):
        f = extract_features(["ECOG performance status of 0-2"], [])
        self.assertEqual(f["ecog_max"], 2)
        f = extract_features(["ECOG PS ≤ 1"], [])
        self.assertEqual(f["ecog_max"], 1)

    def test_biomarkers_split_by_section(self):
        self.assertIn("HER2", self.f["biomarkers_inclusion"])
        self.assertIn("HR", self.f["biomarkers_inclusion"])
        self.assertIn("PIK3CA", self.f["biomarkers_exclusion"])

    def test_disease_setting(self):
        self.assertIn("metastatic", self.f["disease_setting"])
        self.assertIn("locally_advanced", self.f["disease_setting"])

    def test_flags(self):
        self.assertTrue(self.f["requires_measurable_disease"])
        self.assertTrue(self.f["excludes_brain_mets"])
        self.assertFalse(self.f["allows_brain_mets_if_stable"])


class RealWorldQuirks(unittest.TestCase):
    def test_ecog_written_before_keyword(self):
        f = extract_features(["Performance status of 0 to 1, according to the Eastern Cooperative Oncology Group (ECOG) criteria."], [])
        self.assertEqual(f["ecog_max"], 1)

    def test_markdown_escapes_removed(self):
        inc, _ = split_criteria("Inclusion Criteria:\n7\\. Karnofsky \\>= 50% for participants \\< 16 years")
        self.assertEqual(inc, ["Karnofsky >= 50% for participants < 16 years"])

    def test_setting_from_title_and_stage(self):
        f = extract_features(["NSCLC with Stage IIIB-IIIC or Stage IV disease"], [], "First-Line Drug X in NSCLC")
        self.assertIn("first_line", f["disease_setting"])
        self.assertIn("metastatic", f["disease_setting"])
        self.assertIn("advanced", f["disease_setting"])

    def test_indented_alternatives_stay_with_parent(self):
        txt = ("Inclusion Criteria:\n\n"
               "3. Pre- or perimenopausal women must receive LHRH analogue.\n\n"
               "   Post-menopausal women as defined by any of the following criteria:\n"
               "   1. Age ≥ 60 years;\n"
               "   2. Age \\< 60 years and amenorrhea for 12 months\n"
               "4. ECOG 0-1\n")
        inc, _ = split_criteria(txt)
        self.assertEqual(len(inc), 2)
        self.assertEqual(inc[0], "Pre- or perimenopausal women must receive LHRH analogue. Post-menopausal women as "
                                 "defined by any of the following criteria: (1) Age ≥ 60 years; (2) Age < 60 years and "
                                 "amenorrhea for 12 months")
        self.assertEqual(inc[1], "ECOG 0-1")

    def test_formatting_indent_is_not_nesting(self):
        # NCT06170788 style: every bullet after the first is indented, but they are independent AND criteria
        txt = ("Inclusion Criteria:\n\n* Confirmed NSCLC\n\n"
               "  * EGFR/ALK/ROS1-directed therapy not indicated\n  * PD-L1 >= 50%\n")
        inc, _ = split_criteria(txt)
        self.assertEqual(inc, ["Confirmed NSCLC", "EGFR/ALK/ROS1-directed therapy not indicated", "PD-L1 >= 50%"])

    def test_kps(self):
        self.assertEqual(extract_features(["Karnofsky performance status score ≥70"], [])["kps_min"], 70)


if __name__ == "__main__":
    unittest.main()
