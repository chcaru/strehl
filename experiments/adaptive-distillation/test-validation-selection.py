"""Reject validation weighting that lets extra variants buy extra source votes."""
import copy
import importlib.util
from pathlib import Path
import sys
import unittest

spec = importlib.util.spec_from_file_location("selection_train", Path(__file__).with_name("train-v4.py"))
TRAIN = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = TRAIN
spec.loader.exec_module(TRAIN)


class ValidationSelectionTests(unittest.TestCase):
    def setUp(self):
        self.records = [{"group_id": "a", "source_id": source} for source in ("one", "two", "two")]
        self.records.append({"group_id": "b", "source_id": "three"})
        self.rows = [{"row": i, "mae": dict.fromkeys(TRAIN.V4.OUTPUT_NAMES, error),
                      "baseline": dict.fromkeys(TRAIN.V4.OUTPUT_NAMES, baseline)}
                     for i, (error, baseline) in enumerate(((0, 2), (4, 4), (8, 8), (10, 12)))]

    def test_variants_do_not_buy_source_votes(self):
        result = TRAIN.validation_group_summary(self.records, self.rows)
        # Source two's mean is6. Group a averages source one(0) and two(6),
        # giving3, not the row-weighted4. Group b's10 still gets a whole vote.
        for key in TRAIN.V4.OUTPUT_NAMES:
            self.assertEqual(result["a"]["mae"][key], 3)
            self.assertEqual(result["a"]["baseline"][key], 4)
            self.assertEqual((result["a"]["mae"][key] + result["b"]["mae"][key]) / 2, 6.5)
        self.assertEqual((result["a"]["count"], result["a"]["source_count"]), (3, 2))

    def test_replicating_one_sources_variants_does_not_change_its_weight(self):
        expected = TRAIN.validation_group_summary(self.records, self.rows)
        actual = TRAIN.validation_group_summary(self.records, self.rows + self.rows[1:3] * 4)
        self.assertEqual(expected["a"]["mae"], actual["a"]["mae"])
        self.assertEqual(expected["a"]["baseline"], actual["a"]["baseline"])
        self.assertEqual(actual["a"]["count"], 11)

    def test_distinct_sources_with_same_path_still_count_separately(self):
        for record in self.records:
            record["path"] = "same-name.jpg"
        self.assertEqual(TRAIN.validation_group_summary(self.records, self.rows)["a"]["source_count"], 2)

    def test_invalid_or_incomplete_measurements_rejected(self):
        for bad in (-1, float("nan"), float("inf")):
            rows = copy.deepcopy(self.rows)
            rows[0]["mae"][TRAIN.V4.OUTPUT_NAMES[0]] = bad
            with self.assertRaises(ValueError):
                TRAIN.validation_group_summary(self.records, rows)
        rows = copy.deepcopy(self.rows)
        rows[0]["baseline"].pop(TRAIN.V4.OUTPUT_NAMES[0])
        with self.assertRaises(ValueError):
            TRAIN.validation_group_summary(self.records, rows)
        with self.assertRaises(ValueError):
            TRAIN.validation_group_summary(self.records, [])


if __name__ == "__main__":
    unittest.main()
