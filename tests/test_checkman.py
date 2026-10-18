import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "cmk_addons" / "plugins" / "entra_cloudsync" / "agent_based" / "entra_cloudsync.py"
CHECKMAN = ROOT / "cmk_addons" / "plugins" / "entra_cloudsync" / "checkman"


def _plugin_names() -> set[str]:
    text = PLUGIN.read_text(encoding="utf-8")
    return set(re.findall(r'CheckPlugin\(\s*\n?\s*name="([^"]+)"', text))


def _parse_checkman(path: Path) -> dict[str, str]:
    parsed: dict[str, list[str]] = {}
    current_key: str | None = None

    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        if line.startswith(" "):
            assert current_key is not None, f"orphan continuation in {path.name}:{lineno}"
            parsed.setdefault(current_key, []).append(line.strip())
            continue

        assert ":" in line, f"unparseable checkman line in {path.name}:{lineno}: {line!r}"
        current_key, rest = line.split(":", 1)
        parsed.setdefault(current_key, []).append(rest.strip())

    return {key: "\n".join(values) for key, values in parsed.items()}


def test_every_check_plugin_has_matching_manual():
    checks = _plugin_names()
    manuals = {path.name for path in CHECKMAN.iterdir() if path.is_file()}
    assert checks == manuals
    assert checks == {
        "entra_cloudsync_dropped",
        "entra_cloudsync_execution",
        "entra_cloudsync_job",
        "entra_cloudsync_objects",
        "entra_cloudsync_properties",
        "entra_cloudsync_provisioning",
    }


def test_checkman_metadata_and_operator_content():
    required = {"title", "agents", "license", "distribution", "catalog", "description", "item", "discovery"}
    for path in CHECKMAN.iterdir():
        if not path.is_file():
            continue
        data = _parse_checkman(path)
        assert required <= set(data), path.name
        assert data["catalog"] == "cloud/azure"
        assert data["agents"] == "special_entra_cloudsync"
        assert "Data source:" in data["description"]
        assert "Vendor documentation:" in data["description"]
        assert data["item"]
        assert data["discovery"]
        assert "author" not in data
        assert "release" not in data
