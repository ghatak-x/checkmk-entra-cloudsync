import ast
import importlib.util
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_builder():
    path = ROOT / "tools" / "build_mkp.py"
    spec = importlib.util.spec_from_file_location("build_mkp", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    return module


def _inner_names(outer: tarfile.TarFile, component: str, tmp_path: Path) -> set[str]:
    data = outer.extractfile(component).read()
    path = tmp_path / component
    path.write_bytes(data)
    with tarfile.open(path, "r") as inner:
        return set(inner.getnames())


def test_mkp_build_and_payload(tmp_path):
    builder = _load_builder()
    mkp = builder.build()
    assert mkp.exists()

    with tarfile.open(mkp, "r:gz") as outer:
        assert set(outer.getnames()) == {"info", "info.json", "agents.tar", "cmk_addons_plugins.tar"}
        info_json = json.load(outer.extractfile("info.json"))
        info_repr = ast.literal_eval(outer.extractfile("info").read().decode())
        assert info_json == info_repr
        plugin_names = _inner_names(outer, "cmk_addons_plugins.tar", tmp_path)
        agent_names = _inner_names(outer, "agents.tar", tmp_path)

    assert info_json["version"] == "0.0.1"
    assert info_json["author"] == "Sudhir Chauhan"
    assert info_json["version.usable_until"] is None
    assert plugin_names == set(info_json["files"]["cmk_addons_plugins"])
    assert agent_names == set(info_json["files"]["agents"])
    assert "entra_cloudsync/libexec/agent_entra_cloudsync" in plugin_names
    assert "windows/local/entra_cloudsync_agent_version.ps1" in agent_names
    assert "windows/local/entra_cloudsync_connectivity.ps1" in agent_names
    assert "windows/config/entra_cloudsync_local.json.example" in agent_names
    assert not any("__pycache__" in name or name.endswith(".pyc") for name in plugin_names | agent_names)
