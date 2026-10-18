import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_manifest_has_public_release_metadata():
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "entra_cloudsync"
    assert manifest["title"] == "Microsoft Entra Cloud Sync Monitoring"
    assert manifest["version"] == "0.0.1"
    assert manifest["version.min_required"] == "2.5.0"
    assert manifest["version.usable_until"] is None
    assert manifest["author"] == "Sudhir Chauhan"
    assert manifest["license"] == "GPL-2.0-only"
    assert manifest["download_url"] == "https://github.com/ghatak-x/checkmk-entra-cloudsync"
