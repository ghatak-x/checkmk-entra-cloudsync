from __future__ import annotations

import importlib.machinery
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
COLLECTOR = ROOT / "cmk_addons/plugins/entra_cloudsync/libexec/agent_entra_cloudsync"

cmk = types.ModuleType("cmk")
password_store = types.ModuleType("cmk.password_store")
v1 = types.ModuleType("cmk.password_store.v1_unstable")
v1.parser_add_secret_option = lambda *args, **kwargs: None
v1.resolve_secret_option = lambda *args, **kwargs: None
sys.modules.setdefault("cmk", cmk)
sys.modules.setdefault("cmk.password_store", password_store)
sys.modules["cmk.password_store.v1_unstable"] = v1

loader = importlib.machinery.SourceFileLoader("agent_entra_cloudsync", str(COLLECTOR))
spec = importlib.util.spec_from_loader(loader.name, loader)
mod = importlib.util.module_from_spec(spec)
loader.exec_module(mod)


def test_empty_property_values_are_normalized():
    for value in (None, "", "   ", [], {}):
        assert mod._normalize_property_value(value) is None
    assert mod._normalize_property_value("Member") == "Member"


def test_event_identity_prefers_source_id_then_target_then_upn():
    key, display = mod._event_identity({
        "sourceIdentity": {"id": "source-1"},
        "targetIdentity": {"id": "target-1", "details": {"UserPrincipalName": "u@example.test"}},
    })
    assert key == "source:source-1"
    assert display == "u@example.test"
