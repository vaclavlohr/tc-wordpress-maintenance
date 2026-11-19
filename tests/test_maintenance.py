#!/usr/bin/env python3
import importlib.util
import json
import tempfile
import unittest
from datetime import date, timedelta
from email import policy
from email.parser import BytesParser
from pathlib import Path
from unittest import mock
import sys

ROOT = Path(__file__).resolve().parents[1]

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

class MaintenanceTests(unittest.TestCase):
    def test_html_mail_report(self):
        mod = load("tc-wp-mail-report.py", "tc_mail")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(mod.subprocess, "run") as run:
            state = Path(tmp)
            (state / "plugins-before.json").write_text(json.dumps([
                {"name":"elementor","version":"4.4.0", "update":"available", "update_version":"4.4.1"}]))
            (state / "plugins-after.json").write_text(json.dumps([
                {"name":"elementor","version":"4.4.1", "update":"none"}]))
            (state / "themes-before.json").write_text("[]")
            (state / "themes-after.json").write_text("[]")
            (state / "core-before").write_text("7.1.4")
            (state / "core-after").write_text("7.1.4")
            with mock.patch.object(sys, "argv", [
                "tc-wp-mail-report.py", "--mode=--run", "--result=0",
                "--updated=1", "--translations=2", "--state", str(state)
            ]):
                mod.main()
            self.assertEqual(run.call_count, 1)
            message = BytesParser(policy=policy.default).parsebytes(run.call_args.kwargs["input"])
            self.assertIn("Elementor", message.get_body(preferencelist=("html",)).get_content().title())
            self.assertIn("4.4.1", message.get_body(preferencelist=("html",)).get_content())
            self.assertIn("2 jazykových", message.get_body(preferencelist=("html",)).get_content())
            self.assertTrue(message.get_body(preferencelist=("plain",)))
            self.assertIn("Ing. Václav Lohr, Ph.D.", message.get_body(preferencelist=("html",)).get_content())
            self.assertIn("Ing. Václav Lohr, Ph.D.", message.get_body(preferencelist=("plain",)).get_content())
            self.assertIn("+420 734 170 772", message.get_body(preferencelist=("plain",)).get_content())
            self.assertEqual(str(message["Reply-To"]), "lohr@pef.czu.cz")
    def test_failed_preflight_explains_no_rollback_needed(self):
        mod = load("tc-wp-mail-report.py", "tc_mail_error")
        with tempfile.TemporaryDirectory() as tmp, mock.patch.object(mod.subprocess, "run") as run:
            log = Path(tmp) / "check.log"
            log.write_text("tc-wp-maintenance: line 170: SENDMAIL: unbound variable\n")
            with mock.patch.object(sys, "argv", [
                "tc-wp-mail-report.py", "--mode=--check", "--result=1",
                "--log", str(log), "--backup", ""
            ]):
                mod.main()
            message = BytesParser(policy=policy.default).parsebytes(run.call_args.kwargs["input"])
            body = message.get_body(preferencelist=("html",)).get_content()
            self.assertIn("unbound variable", body)
            self.assertIn("rollback nebyl potřeba", body)
            self.assertIn("Žádné změny WordPressu se nespustily", body)
    def test_sendmail_variable_defined_before_preflight(self):
        shell = (ROOT / "tc-wp-maintenance").read_text(encoding="utf-8")
        self.assertIn("SENDMAIL=/usr/sbin/sendmail", shell)
        self.assertLess(shell.index("SENDMAIL=/usr/sbin/sendmail"), shell.index('[[ -x "$SENDMAIL" ]]'))

    def test_six_month_ten_snapshot_policy(self):
        mod = load("tc-wp-prune-backups.py", "tc_prune")
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            stamp = date.today().strftime("%Y%m%d")
            for i in range(12):
                (p / f"{stamp}-040000-{1000+i}").mkdir()
            older = date.today().replace(year=date.today().year - 1)
            (p / f"{older.strftime('%Y%m%d')}-030000-13").mkdir()
            (p / "other-snapshot").mkdir()
            mod.main(tmp)
            candidates = [n for n in p.iterdir() if n.name.startswith(stamp)]
            self.assertEqual(len(candidates), 10)
            self.assertTrue((p / "other-snapshot").exists())
            self.assertFalse((p / f"{older.strftime('%Y%m%d')}-030000-13").exists())

if __name__ == "__main__":
    unittest.main()
