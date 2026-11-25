import os
import shlex
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app.tools import read_file, run_bash_command


class ReadFileTests(unittest.TestCase):
    def test_lists_directory_entries_with_directories_marked(self):
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "zebra.py").write_text("print('hello')", encoding="utf-8")
            (root / "src").mkdir()

            self.assertEqual(read_file(temp_dir), "src/\nzebra.py")

    def test_reports_empty_directory(self):
        with TemporaryDirectory() as temp_dir:
            self.assertEqual(read_file(temp_dir), "(empty directory)")

    def test_reads_file_contents_as_before(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "example.py"
            path.write_text("print('hello')", encoding="utf-8")

            self.assertEqual(read_file(str(path)), "print('hello')")

    def test_bash_failure_returns_exit_status_and_both_streams(self):
        python_command = [
            sys.executable,
            "-c",
            "import sys; print('out'); print('err', file=sys.stderr); sys.exit(7)",
        ]
        if os.name == "nt":
            command = subprocess.list2cmdline(python_command)
        else:
            command = shlex.join(python_command)

        result = run_bash_command(command)

        self.assertIn("Command exited with status 7.", result)
        self.assertIn("stdout:\nout", result)
        self.assertIn("stderr:\nerr", result)

    def test_bash_exposes_working_directory_to_python_and_success_stderr(self):
        with (
            TemporaryDirectory() as temp_dir,
            patch.dict(os.environ, {"PYTHONSAFEPATH": "1"}),
        ):
            module = Path(temp_dir) / "fixture_module.py"
            module.write_text("VALUE = 42\n", encoding="utf-8")
            args = [
                sys.executable,
                "-c",
                (
                    "import fixture_module, sys; "
                    "print(fixture_module.VALUE, file=sys.stderr)"
                ),
            ]
            command = (
                subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)
            )
            previous_cwd = os.getcwd()
            try:
                os.chdir(temp_dir)
                self.assertIn("42", run_bash_command(command))
            finally:
                os.chdir(previous_cwd)


if __name__ == "__main__":
    unittest.main()
