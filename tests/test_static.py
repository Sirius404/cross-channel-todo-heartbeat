import json
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class StaticTests(unittest.TestCase):
    def test_example_config(self):
        config = json.loads((ROOT / "config.example.json").read_text())
        self.assertEqual(config["timezone"], "Asia/Shanghai")
        self.assertIn("chat_ids", config["telegram"])

    def test_telegram_requires_scope(self):
        result = subprocess.run(
            ["python3", str(ROOT / "scripts/tg_live_scan.py")],
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("provide --name-regex", result.stderr)


if __name__ == "__main__":
    unittest.main()
