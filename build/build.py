"""Build the one-folder launcher: `python build/build.py` (run on each target OS).

Output: dist/ResumeWriterLauncher/ (ResumeWriterLauncher.exe + _internal/). One-folder is
required for MSIX / Microsoft Store packaging and starts faster than one-file."""
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

subprocess.check_call([
    sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
    "--onedir", "--windowed", "--name", "ResumeWriterLauncher",
    # dulwich/certifi are imported lazily, so tell PyInstaller to bundle them fully.
    "--collect-submodules", "dulwich", "--collect-data", "certifi",
    "--distpath", str(ROOT / "dist"), "--workpath", str(ROOT / "build" / "work"),
    "--specpath", str(ROOT / "build"),
    str(ROOT / "run_launcher.py"),
], cwd=ROOT)
