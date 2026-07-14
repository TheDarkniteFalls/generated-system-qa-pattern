from __future__ import annotations

import unittest
from pathlib import Path

import generated_system_qa


ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"


class GeneratedSystemQATests(unittest.TestCase):
    def test_good_case_passes(self) -> None:
        self.assertEqual(generated_system_qa.check_path(EXAMPLES / "good.json"), [])

    def test_expected_bad_cases_fail_with_named_code(self) -> None:
        for name, (_, expected_code) in generated_system_qa.SELF_TEST_CASES.items():
            if expected_code is None:
                continue
            with self.subTest(name=name):
                codes = {finding.code for finding in generated_system_qa.check_path(EXAMPLES / name)}
                self.assertIn(expected_code, codes)

    def test_shortest_path_is_measured_from_entry(self) -> None:
        adjacency = {
            "entry": {"middle"},
            "middle": {"goal"},
            "goal": set(),
        }
        self.assertEqual(
            generated_system_qa._distances("entry", adjacency),
            {"entry": 0, "middle": 1, "goal": 2},
        )


if __name__ == "__main__":
    unittest.main()
