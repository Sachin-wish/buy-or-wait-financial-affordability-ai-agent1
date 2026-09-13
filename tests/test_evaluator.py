import unittest
from buy_or_wait.evaluator import build_benchmark_suite, evaluate_strategy, run_evaluation_pipeline, print_evaluation_summary

class EvaluatorTests(unittest.TestCase):
    def test_benchmark_suite_construction(self):
        cases = build_benchmark_suite()
        self.assertGreaterEqual(len(cases), 10)
        categories = {c.category for c in cases}
        self.assertIn("Affordability", categories)
        self.assertIn("Safety", categories)
        self.assertIn("Security", categories)
        self.assertIn("Forex", categories)
        self.assertIn("Policy", categories)

    def test_deterministic_strategy_evaluation(self):
        cases = build_benchmark_suite()
        metrics = evaluate_strategy("deterministic", cases)
        self.assertEqual(metrics.total_cases, len(cases))
        self.assertGreaterEqual(metrics.accuracy, 0.90)
        self.assertEqual(metrics.safety_violations, 0)
        self.assertEqual(metrics.safety_rate, 1.0)
        self.assertEqual(metrics.injection_defense_rate, 1.0)

    def test_full_evaluation_pipeline_and_summary(self):
        report = run_evaluation_pipeline()
        self.assertIn("strategies", report)
        self.assertIn("deterministic", report["strategies"])
        self.assertIn("conservative", report["strategies"])
        self.assertIn("optimistic", report["strategies"])
        
        summary_text = print_evaluation_summary(report)
        self.assertIn("BUY-OR-WAIT FINANCIAL AFFORDABILITY AGENT EVALUATION", summary_text)
        self.assertIn("deterministic", summary_text)

if __name__ == "__main__":
    unittest.main()
