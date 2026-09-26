import json, runpy, unittest
from pathlib import Path
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
SOURCE=(ROOT/'look'/'lk').read_text()

class WeatherTransport675Tests(unittest.TestCase):
    def test_dual_transport_and_diagnostics_are_shipped(self):
        self.assertIn('curl=shutil.which("curl")', SOURCE)
        self.assertIn('HTTP JSON failed: urllib [', SOURCE)
        self.assertIn("_ansi_label('weather !', '31')", SOURCE)
        self.assertIn('events.emit("tool_error", tool="weather"', SOURCE)

    def test_weather_receipt_contract_remains_strict(self):
        self.assertIn('if weather_required and not weather_succeeded:', SOURCE)
        self.assertIn('successful live WEATHER receipt', SOURCE)

if __name__ == '__main__': unittest.main()
