"""Regression tests for the preserved command-line analysis scripts."""

from contextlib import redirect_stdout
from importlib.util import module_from_spec, spec_from_file_location
from io import StringIO
from pathlib import Path
import tempfile
import unittest

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = ROOT / "data" / "cleaned" / "marketing_campaign_cleaned.csv"
ORIGINAL_COLUMNS = (
    "Campaign_ID",
    "Campaign_Name",
    "Date",
    "Channel",
    "Customer_ID",
    "Age_Group",
    "Gender",
    "Impressions",
    "Clicks",
    "Leads",
    "Conversions",
    "Ad_Spend",
    "Revenue",
)


def _load_script(filename: str):
    path = ROOT / "python" / filename
    module_name = f"regression_{path.stem.replace('-', '_')}"
    spec = spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to import {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ScriptRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.script01 = _load_script("01_load_and_inspect.py")
        cls.script02 = _load_script("02_data_quality_check.py")
        cls.script03 = _load_script("03_kpi_analysis.py")
        cls.bundled_data = pd.read_csv(
            SOURCE_PATH,
            encoding="utf-8-sig",
            dtype="string",
            keep_default_na=False,
        )

    def _slice(self, rows: int = 2) -> pd.DataFrame:
        return self.bundled_data.loc[: rows - 1, ORIGINAL_COLUMNS].copy()

    @staticmethod
    def _write_csv(data: pd.DataFrame, directory: str, name: str = "input.csv") -> Path:
        path = Path(directory) / name
        data.to_csv(path, index=False)
        return path

    def _run_kpi_script(self, data: pd.DataFrame) -> str:
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_csv(data, directory)
            output = StringIO()
            with redirect_stdout(output):
                self.script03.main(source)
            return output.getvalue()

    def test_load_script_selects_named_schema_preserves_text_and_date_format(self):
        data = self._slice()
        data.loc[0, "Campaign_Name"] = "NA"
        data.loc[0, "Gender"] = "N/A"
        data.loc[1, "Revenue"] = ""
        data.insert(0, "Unexpected_First_Column", ["ignore-1", "ignore-2"])
        data["Unexpected_Last_Column"] = ["ignore-3", "ignore-4"]

        with tempfile.TemporaryDirectory() as directory:
            source = self._write_csv(data, directory)
            destination = Path(directory) / "cleaned.csv"
            self.script01.main(source, destination)
            result = pd.read_csv(
                destination,
                dtype="string",
                keep_default_na=False,
            )

        self.assertEqual(list(result.columns), list(ORIGINAL_COLUMNS))
        self.assertEqual(result.loc[0, "Campaign_Name"], "NA")
        self.assertEqual(result.loc[0, "Gender"], "N/A")
        self.assertEqual(result.loc[1, "Revenue"], "")
        self.assertRegex(result.loc[0, "Date"], r"^\d{2}-\d{2}-\d{4}$")

    def test_data_quality_script_handles_empty_data_without_none_or_crash(self):
        data = pd.DataFrame(columns=ORIGINAL_COLUMNS)
        with tempfile.TemporaryDirectory() as directory:
            source = self._write_csv(data, directory)
            output = StringIO()
            with redirect_stdout(output):
                self.script02.main(source)

        text = output.getvalue()
        self.assertIn("Revenue coverage: N/A", text)
        self.assertNotIn("\nNone\n", f"\n{text}\n")

    def test_kpi_script_prints_na_for_zero_denominators(self):
        data = self._slice(1)
        data.loc[0, ["Impressions", "Clicks", "Leads", "Conversions", "Ad_Spend"]] = "0"
        data.loc[0, "Revenue"] = "0"

        text = self._run_kpi_script(data)

        self.assertIn("CTR: N/A", text)
        self.assertIn("Conversion Rate: N/A", text)
        self.assertIn("CAC (INR): N/A", text)
        self.assertIn("ROAS: N/A", text)
        self.assertIn("ROI: N/A", text)
        self.assertNotIn("None", text)

    def test_kpi_script_warns_for_partial_and_all_unknown_revenue(self):
        partial = self._slice()
        partial.loc[0, "Revenue"] = ""
        partial_text = self._run_kpi_script(partial)
        self.assertIn("WARNING: Revenue is partial", partial_text)
        self.assertIn("known revenue only", partial_text)
        self.assertIn("Revenue Coverage: 50.00%", partial_text)

        unknown = self._slice()
        unknown["Revenue"] = ""
        unknown_text = self._run_kpi_script(unknown)
        self.assertIn("Known Revenue (INR): N/A", unknown_text)
        self.assertIn("WARNING: Revenue is partial", unknown_text)
        self.assertIn("Revenue Coverage: 0.00%", unknown_text)


if __name__ == "__main__":
    unittest.main()
