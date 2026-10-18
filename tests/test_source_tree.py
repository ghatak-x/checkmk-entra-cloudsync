import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "cmk_addons" / "plugins" / "entra_cloudsync"


def test_python_sources_compile(tmp_path):
    sources = [
        path
        for path in PLUGIN.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and (path.suffix == ".py" or (path.name.startswith("agent_") and path.suffix == ""))
    ]
    assert sources
    for index, source in enumerate(sources):
        py_compile.compile(str(source), cfile=str(tmp_path / f"{index}.pyc"), doraise=True)


def test_expected_source_layout():
    assert (PLUGIN / "agent_based" / "entra_cloudsync.py").is_file()
    assert (PLUGIN / "libexec" / "agent_entra_cloudsync").is_file()
    assert (PLUGIN / "rulesets" / "special_agent.py").is_file()
    assert (PLUGIN / "rulesets" / "check_parameters.py").is_file()
    assert (PLUGIN / "server_side_calls" / "special_agent.py").is_file()


def test_repository_does_not_mirror_checkmk_local_tree():
    assert not (ROOT / "local" / "lib" / "python3").exists()
    assert not (ROOT / "scripts").exists()
    assert set(path.name for path in (ROOT / "tools").iterdir() if path.is_file()) == {"build_mkp.py"}


def test_optional_windows_local_checks_are_present():
    local = ROOT / "agents" / "windows" / "local"
    assert {path.name for path in local.iterdir() if path.is_file()} == {
        "entra_cloudsync_agent_version.ps1",
        "entra_cloudsync_connectivity.ps1",
    }
    assert (ROOT / "agents" / "windows" / "config" / "entra_cloudsync_local.json.example").is_file()

