"""Pack the PyInstaller one-folder output into an (unsigned) .msix for the Microsoft Store.

The Store signs the package after certification, so no certificate is needed here.
Usage (Windows, after build/build.py):
    python packaging/msix/build_msix.py --version 1.0.0.0
"""
from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import quoteattr

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent


def find_makeappx() -> str:
    found = shutil.which("makeappx")
    if found:
        return found
    pattern = r"C:\Program Files (x86)\Windows Kits\10\bin\*\x64\makeappx.exe"
    candidates = sorted(glob.glob(pattern))  # latest SDK version sorts last
    if not candidates:
        sys.exit("makeappx.exe not found (install the Windows 10/11 SDK).")
    return candidates[-1]


def attr(value: str) -> str:
    """XML-escape for use inside an attribute/text value (strips the surrounding quotes)."""
    return quoteattr(value)[1:-1]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", required=True, help="4-part version, e.g. 1.0.0.0 (Store needs last part 0)")
    ap.add_argument("--dist", default=str(ROOT / "dist" / "ResumeWriterLauncher"))
    ap.add_argument("--out", default=str(ROOT / "dist" / "ResumeWriterLauncher.msix"))
    ap.add_argument("--identity-name", default=os.environ.get("MSIX_IDENTITY_NAME") or "ResumeWriter.Launcher")
    ap.add_argument("--publisher", default=os.environ.get("MSIX_PUBLISHER") or "CN=ResumeWriter")
    ap.add_argument("--publisher-display-name",
                    default=os.environ.get("MSIX_PUBLISHER_DISPLAY_NAME") or "ResumeWriter")
    ap.add_argument("--display-name", default=os.environ.get("MSIX_DISPLAY_NAME") or "ResWritLauncher")
    ap.add_argument("--skip-pack", action="store_true", help="only stage files (for testing)")
    args = ap.parse_args()

    if len(args.version.split(".")) != 4:
        sys.exit("--version must have four parts, e.g. 1.0.0.0")
    dist = Path(args.dist)
    if not (dist / "ResumeWriterLauncher.exe").is_file() and not args.skip_pack:
        sys.exit(f"{dist}\\ResumeWriterLauncher.exe not found; run build/build.py first.")

    stage = ROOT / "build" / "msix_stage"
    if stage.exists():
        shutil.rmtree(stage)
    if dist.is_dir():
        shutil.copytree(dist, stage)
    else:
        stage.mkdir(parents=True)
    shutil.copytree(HERE / "Assets", stage / "Assets")

    manifest = (HERE / "AppxManifest.xml.in").read_text(encoding="utf-8")
    for token, value in {
        "@IDENTITY_NAME@": args.identity_name, "@PUBLISHER@": args.publisher,
        "@VERSION@": args.version, "@DISPLAY_NAME@": args.display_name,
        "@PUBLISHER_DISPLAY_NAME@": args.publisher_display_name,
    }.items():
        manifest = manifest.replace(token, attr(value))
    (stage / "AppxManifest.xml").write_text(manifest, encoding="utf-8")
    print(f"Staged package contents in {stage}")
    if args.skip_pack:
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.check_call([find_makeappx(), "pack", "/d", str(stage), "/p", str(out), "/o"])
    print(f"Created {out}")


if __name__ == "__main__":
    main()
