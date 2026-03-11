from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from validate_datasets import DATASET_SPECS, DATA_DIR, validate_all


BASE_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = BASE_DIR / "dist" / "releases"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description="Stage blessed dataset CSVs for a tagged release.")
    parser.add_argument("--version", required=True, help="Release tag, for example v1.0.0")
    args = parser.parse_args()

    failures = validate_all(DATA_DIR)
    if failures:
        raise SystemExit("Refusing to stage release assets because dataset validation failed.")

    out_dir = DIST_DIR / args.version
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest: dict[str, dict[str, str | int]] = {}
    for filename in DATASET_SPECS:
        src = DATA_DIR / filename
        dest = out_dir / filename
        shutil.copy2(src, dest)
        manifest[filename] = {
            "sha256": sha256(dest),
            "bytes": dest.stat().st_size,
        }

    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(f"Staged {len(DATASET_SPECS)} release assets in {out_dir}")


if __name__ == "__main__":
    main()
