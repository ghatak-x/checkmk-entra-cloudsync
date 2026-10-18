from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import importlib.util
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "cmk_addons/plugins/entra_cloudsync/agent_based/entra_cloudsync.py"


class State(IntEnum):
    OK = 0
    WARN = 1
    CRIT = 2
    UNKNOWN = 3


@dataclass
class Result:
    state: State
    summary: str | None = None
    notice: str | None = None
    details: str | None = None


@dataclass
class Metric:
    name: str
    value: float | int


@dataclass
class Service:
    item: str | None = None


class AgentSection:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class CheckPlugin:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


_VALUE_STORE: dict[str, float] = {}


def get_value_store():
    return _VALUE_STORE


cmk = types.ModuleType("cmk")
agent_based = types.ModuleType("cmk.agent_based")
v2 = types.ModuleType("cmk.agent_based.v2")
for name, obj in {
    "AgentSection": AgentSection,
    "CheckPlugin": CheckPlugin,
    "Metric": Metric,
    "Result": Result,
    "Service": Service,
    "State": State,
    "get_value_store": get_value_store,
}.items():
    setattr(v2, name, obj)
sys.modules.setdefault("cmk", cmk)
sys.modules.setdefault("cmk.agent_based", agent_based)
sys.modules["cmk.agent_based.v2"] = v2

spec = importlib.util.spec_from_file_location("entra_cloudsync", PLUGIN)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)


def base_job():
    return {
        "id": "job-1",
        "configuration_name": "example.test",
        "schedule": {"state": "Active", "interval": "PT20M"},
        "status": {
            "code": "Active",
            "successive_failures": 0,
            "quarantine": None,
            "last_execution": {
                "state": "Succeeded",
                "time_began": "2026-10-17T20:00:00Z",
                "time_ended": "2026-10-17T20:00:05Z",
                "error": None,
            },
            "object_counts": [{"key": "user to User", "value": 3}],
        },
        "provisioning_logs": {
            "window_minutes": 60,
            "counts": {"total": 4, "success": 3, "warning": 0, "failure": 1},
            "unresolved": {"total": 0, "failure": 0, "warning": 0},
            "actions": {"update": 4},
            "latest_problem": None,
            "dropped_objects": {
                "counts": {"delete": 1, "stageddelete": 0, "disable": 0, "skipped": 1},
                "events": [],
            },
            "property_changes": {
                "total_changes": 7,
                "objects_changed": 2,
                "attributes": [{"name": "Department", "count": 2}],
            },
        },
    }


def section(job=None):
    return {"jobs": [job or base_job()]}


def states(results):
    return [r.state for r in results if isinstance(r, Result)]


def test_discovers_all_six_services():
    sec = section()
    discovers = [
        mod.discover_entra_cloudsync_job,
        mod.discover_entra_cloudsync_execution,
        mod.discover_entra_cloudsync_objects,
        mod.discover_entra_cloudsync_provisioning,
        mod.discover_entra_cloudsync_dropped,
        mod.discover_entra_cloudsync_properties,
    ]
    for fn in discovers:
        services = list(fn(sec))
        assert [s.item for s in services] == ["example.test"]


def test_job_active_is_ok():
    results = list(mod.check_entra_cloudsync_job("example.test", {"notrun_grace_intervals": 2.0}, section()))
    assert State.CRIT not in states(results)
    assert results[0].summary == "Schedule: Active, status: Active"


def test_job_notrun_starts_warn():
    job = base_job()
    job["status"]["code"] = "NotRun"
    _VALUE_STORE.clear()
    mod.time.time = lambda: 1000.0
    results = list(mod.check_entra_cloudsync_job("example.test", {"notrun_grace_intervals": 2.0}, section(job)))
    assert results[0].state == State.WARN
    assert "grace 40m" in results[0].summary


def test_execution_emits_duration_and_age_metrics(monkeypatch):
    class FixedDateTime(mod.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 10, 17, 20, 10, 0, tzinfo=mod.timezone.utc)

    monkeypatch.setattr(mod, "datetime", FixedDateTime)
    results = list(mod.check_entra_cloudsync_execution(
        "example.test", {"freshness_intervals": ("fixed", (2.0, 3.0))}, section()
    ))
    metrics = {r.name: r.value for r in results if isinstance(r, Metric)}
    assert metrics["cloudsync_execution_duration"] == 5.0
    assert metrics["last_execution_age"] == 595.0
    assert State.CRIT not in states(results)


def test_objects_count_is_metric():
    results = list(mod.check_entra_cloudsync_objects("example.test", section()))
    assert any(isinstance(r, Metric) and r.name == "synchronized_user_to_user" and r.value == 3 for r in results)


def test_provisioning_unresolved_failure_is_crit():
    job = base_job()
    job["provisioning_logs"]["unresolved"] = {"total": 1, "failure": 1, "warning": 0}
    job["provisioning_logs"]["latest_problem"] = {
        "object": "user@example.test", "time": "2026-10-17T20:00:00Z", "action": "update",
        "status": "failure", "error_code": "Example", "reason": "Example reason"
    }
    results = list(mod.check_entra_cloudsync_provisioning("example.test", section(job)))
    assert any(isinstance(r, Result) and r.state == State.CRIT for r in results)


def test_dropped_and_property_services_are_informational():
    dropped = list(mod.check_entra_cloudsync_dropped("example.test", section()))
    properties = list(mod.check_entra_cloudsync_properties("example.test", section()))
    assert all(r.state == State.OK for r in dropped if isinstance(r, Result))
    assert all(r.state == State.OK for r in properties if isinstance(r, Result))
    assert any(isinstance(r, Result) and "7 property changes on 2 objects" in (r.summary or "") for r in properties)
