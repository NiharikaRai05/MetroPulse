import unittest
from pathlib import Path

class TestMetricDictionary(unittest.TestCase):
    def test_metric_dictionary_exists(self):
        p = Path("docs/metric_dictionary.md")
        self.assertTrue(p.exists(), "docs/metric_dictionary.md must exist")

    def test_metric_dictionary_contents(self):
        text = Path("docs/metric_dictionary.md").read_text(encoding="utf-8")
        required_topics = [
            "Observed Fact",
            "Derived Fact",
            "Estimate / Proxy",
            "Policy / Heuristic Assumption",
            "Credit Card Tip Percentage",
            "payment_type = 1",
            "Effective Trip Average Speed",
            "speed_mph",
            "Underserved Zone Indicator",
            "is_underserved",
            "Lag-1",
            "Association",
            "Simpson's Paradox",
        ]
        for topic in required_topics:
            self.assertIn(topic, text)

if __name__ == "__main__":
    unittest.main()
