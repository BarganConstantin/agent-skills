"""Unit tests for scoring, not evidence of model/browser execution."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "evals" / "score.py"
spec = importlib.util.spec_from_file_location("score", SCRIPT)
score = importlib.util.module_from_spec(spec)
spec.loader.exec_module(score)


def manifest():
    return {"schema_version": 1, "fixtures": [{"fixture_id": "demo", "truth_ids": ["FX-001", "FX-002"]}]}


def finding(fid, verdict, truth_id=None, checked=True):
    return {"finding_id": fid, "review": {"verdict": verdict, "truth_id": truth_id,
            "reviewer": "independent-reviewer" if verdict != "unreviewed" else None,
            "evidence_checked": checked, "reproduction_checked": checked}}


def run(arm, findings=None, pair="p1", status="completed"):
    return {"run_id": arm + "-" + pair, "fixture_id": "demo", "pair_id": pair,
            "arm": arm, "status": status, "findings": findings or []}


def reviews(*runs):
    return {"schema_version": 1, "data_kind": "real_evaluation", "runs": list(runs)}


class ScorerTests(unittest.TestCase):
    def test_complete_pairs_score_recall_and_precision(self):
        r = score.evaluate(manifest(), reviews(
            run("control", [finding("a", "matched", "FX-001"), finding("b", "false_positive")]),
            run("skill", [finding("a", "matched", "FX-001"), finding("b", "matched", "FX-002")])
        ))
        self.assertTrue(r["comparison_available"])
        self.assertEqual(r["mean_recall_delta_skill_minus_control"], .5)
        self.assertEqual(r["runs"][0]["precision"], .5)
        self.assertEqual(r["runs"][1]["precision"], 1)

    def test_duplicate_truth_match_cannot_inflate_recall(self):
        r = score.evaluate(manifest(), reviews(
            run("control", [finding("a", "matched", "FX-001"), finding("b", "matched", "FX-001")]),
            run("skill")
        ))
        self.assertEqual(r["runs"][0]["true_positive_defects"], 1)
        self.assertEqual(r["runs"][0]["redundant_matches"], 1)

    def test_clean_fixture_penalizes_false_positive_without_fake_recall(self):
        m = {"schema_version": 1, "fixtures": [{"fixture_id": "demo", "truth_ids": []}]}
        r = score.evaluate(m, reviews(run("control", [finding("a", "false_positive")]), run("skill")))
        self.assertTrue(r["comparison_available"])
        self.assertIsNone(r["mean_recall_delta_skill_minus_control"])
        self.assertEqual(r["mean_false_positive_delta_skill_minus_control"], -1)
        self.assertIsNone(r["runs"][0]["recall"])
        self.assertEqual(r["runs"][0]["false_positive_findings"], 1)

    def test_unreviewed_finding_blocks_pairwise_claim(self):
        r = score.evaluate(manifest(), reviews(run("control", [finding("a", "unreviewed")]), run("skill")))
        self.assertFalse(r["comparison_available"])
        self.assertIsNone(r["mean_recall_delta_skill_minus_control"])
        self.assertEqual(r["runs"][0]["unreviewed_findings"], 1)

    def test_failed_run_is_not_silently_dropped(self):
        r = score.evaluate(manifest(), reviews(run("control", status="failed"), run("skill")))
        self.assertEqual(r["run_count"], 2)
        self.assertEqual(r["completed_run_count"], 1)
        self.assertFalse(r["comparison_available"])

    def test_missing_arm_blocks_comparison(self):
        r = score.evaluate(manifest(), reviews(run("skill")))
        self.assertFalse(r["comparison_available"])
        self.assertTrue(r["comparison_blockers"])

    def test_missing_fixture_blocks_comparison(self):
        m = manifest()
        m["fixtures"].append({"fixture_id": "heldout", "truth_ids": ["FX-003"]})
        r = score.evaluate(m, reviews(run("control"), run("skill")))
        self.assertFalse(r["comparison_available"])

    def test_rejects_invalid_matching_truth_or_duplicate_ids(self):
        with self.assertRaises(score.EvalError):
            score.evaluate(manifest(), reviews(run("control", [finding("a", "matched", "FX-999")])))
        with self.assertRaises(score.EvalError):
            score.evaluate(manifest(), reviews(run("control", [finding("a", "false_positive"), finding("a", "false_positive")])))
        with self.assertRaises(score.EvalError):
            score.evaluate(manifest(), reviews(run("control"), run("control")))

    def test_rejects_synthetic_experiment_as_measured_results(self):
        x = reviews(run("control"))
        x["data_kind"] = "synthetic_example"
        with self.assertRaises(score.EvalError):
            score.evaluate(manifest(), x)

    def test_rejects_unreviewed_label_on_matched_finding(self):
        f = finding("f1", "matched", "FX-001")
        f["review"]["reviewer"] = None
        with self.assertRaises(score.EvalError):
            score.evaluate(manifest(), reviews(run("control", [f])))

    def test_output_does_not_claim_significance(self):
        result = score.evaluate(manifest(), reviews(run("control"), run("skill")))
        self.assertEqual(result["status"], "reviewed_inputs_not_independently_verified")
        self.assertIn("does not run agents", result["disclaimer"])


if __name__ == "__main__":
    unittest.main()
