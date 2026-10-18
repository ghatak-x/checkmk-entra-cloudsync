#!/usr/bin/env python3

from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from cmk.agent_based.v2 import (
    AgentSection,
    CheckPlugin,
    Metric,
    Result,
    Service,
    State,
    get_value_store,
)


def parse_entra_cloudsync(string_table):
    raw = "\n".join(line[0] for line in string_table if line)
    if not raw:
        return None
    return json.loads(raw)


agent_section_entra_cloudsync = AgentSection(
    name="entra_cloudsync",
    parse_function=parse_entra_cloudsync,
)


def _jobs(section: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not section:
        return []
    return list(section.get("jobs") or [])


def _job_item(job: dict[str, Any]) -> str:
    return str(job.get("configuration_name") or job.get("id") or "Cloud Sync")


def _find_job(section: dict[str, Any] | None, item: str) -> dict[str, Any] | None:
    for job in _jobs(section):
        if _job_item(job) == item:
            return job
    return None


def _discover_jobs(section):
    for job in _jobs(section):
        yield Service(item=_job_item(job))


def _parse_time(value: Any) -> datetime | None:
    if not value:
        return None

    text = str(value).strip()
    if text.startswith("0001-01-01"):
        return None

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    text = re.sub(r"(\.\d{6})\d+(?=[+-]\d{2}:\d{2}$)", r"\1", text)

    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _age_seconds(value: Any) -> float | None:
    parsed = _parse_time(value)
    if parsed is None:
        return None
    return max(0.0, (datetime.now(timezone.utc) - parsed).total_seconds())


def _duration_seconds(start: Any, end: Any) -> float | None:
    start_dt = _parse_time(start)
    end_dt = _parse_time(end)
    if start_dt is None or end_dt is None:
        return None
    return max(0.0, (end_dt - start_dt).total_seconds())


def _interval_seconds(value: Any) -> int | None:
    if not value:
        return None

    match = re.fullmatch(
        r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?",
        str(value),
    )
    if not match:
        return None

    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    total = hours * 3600 + minutes * 60 + seconds
    return total or None


def _human_age(seconds: float | int | None) -> str:
    if seconds is None:
        return "unknown"

    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.0f}s"
    if seconds < 3600:
        return f"{seconds / 60:.0f}m"
    if seconds < 86400:
        return f"{seconds / 3600:.1f}h"
    return f"{seconds / 86400:.1f}d"


def _safe_metric_suffix(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return text or "objects"


# ---------------------------------------------------------------------------
# Job state
# ---------------------------------------------------------------------------


def discover_entra_cloudsync_job(section):
    yield from _discover_jobs(section)


def check_entra_cloudsync_job(item, params, section):
    if not section:
        yield Result(state=State.UNKNOWN, summary="No Cloud Sync data received")
        return

    collector_error = section.get("collector_error")
    if collector_error:
        yield Result(state=State.CRIT, summary=f"Collector error: {collector_error}")
        return

    job = _find_job(section, item)
    if job is None:
        yield Result(state=State.CRIT, summary="AD2AADProvisioning job not found")
        return

    schedule = job.get("schedule") or {}
    status = job.get("status") or {}
    schedule_state = str(schedule.get("state") or "unknown")
    status_code = str(status.get("code") or "unknown")

    interval_text = schedule.get("interval")
    interval = _interval_seconds(interval_text)
    value_store = get_value_store()

    if schedule_state == "Active" and status_code == "Active":
        value_store.pop("notrun_since", None)
        state = State.OK
        status_summary = f"Schedule: {schedule_state}, status: {status_code}"

    elif schedule_state == "Active" and status_code == "NotRun":
        now = time.time()
        first_seen = value_store.get("notrun_since")
        if first_seen is None:
            first_seen = now
            value_store["notrun_since"] = now

        notrun_age = max(0.0, now - float(first_seen))
        grace_multiplier = float(params.get("notrun_grace_intervals", 2.0))
        grace = interval * grace_multiplier if interval else 2400.0

        if notrun_age >= grace:
            state = State.CRIT
            status_summary = (
                "Schedule: Active, status: NotRun, "
                f"no execution for {_human_age(notrun_age)} "
                f"(grace {_human_age(grace)})"
            )
        else:
            state = State.WARN
            status_summary = (
                "Schedule: Active, status: NotRun, "
                f"waiting for execution after start/restart for {_human_age(notrun_age)} "
                f"(grace {_human_age(grace)})"
            )
    else:
        value_store.pop("notrun_since", None)
        state = State.CRIT
        status_summary = f"Schedule: {schedule_state}, status: {status_code}"

    yield Result(state=state, summary=status_summary)

    failures = int(status.get("successive_failures") or 0)
    yield Metric("successive_failures", failures)

    if failures == 0:
        failure_state = State.OK
    elif failures == 1:
        failure_state = State.WARN
    else:
        failure_state = State.CRIT

    yield Result(state=failure_state, summary=f"Successive failures: {failures}")

    quarantine = status.get("quarantine")
    if quarantine:
        yield Result(
            state=State.CRIT,
            summary="Configuration is quarantined",
            details=json.dumps(quarantine, indent=2, default=str),
        )
    else:
        yield Result(state=State.OK, summary="Not quarantined")


check_plugin_entra_cloudsync_job = CheckPlugin(
    name="entra_cloudsync_job",
    sections=["entra_cloudsync"],
    service_name="Entra Cloud Sync Job %s",
    discovery_function=discover_entra_cloudsync_job,
    check_function=check_entra_cloudsync_job,
    check_default_parameters={"notrun_grace_intervals": 2.0},
    check_ruleset_name="entra_cloudsync_job",
)


# ---------------------------------------------------------------------------
# Execution health / freshness
# ---------------------------------------------------------------------------


def discover_entra_cloudsync_execution(section):
    yield from _discover_jobs(section)


def check_entra_cloudsync_execution(item, params, section):
    job = _find_job(section, item)
    if job is None:
        yield Result(state=State.UNKNOWN, summary="Provisioning job not found")
        return

    status = job.get("status") or {}
    schedule = job.get("schedule") or {}
    execution = status.get("last_execution")

    if not execution:
        yield Result(state=State.UNKNOWN, summary="No completed execution reported yet")
        return

    execution_state = str(execution.get("state") or "unknown")
    ended = execution.get("time_ended")
    age = _age_seconds(ended)
    duration = _duration_seconds(execution.get("time_began"), execution.get("time_ended"))

    if age is None:
        yield Result(state=State.UNKNOWN, summary="No completed execution reported yet")
        return

    exec_state = State.OK if execution_state == "Succeeded" else State.CRIT
    yield Result(
        state=exec_state,
        summary=f"Last execution: {execution_state}, {_human_age(age)} ago",
    )

    if duration is not None:
        yield Metric("cloudsync_execution_duration", duration)
        yield Result(state=State.OK, summary=f"Execution duration: {duration:.2f}s")

    yield Metric("last_execution_age", age)

    interval_text = schedule.get("interval")
    interval = _interval_seconds(interval_text)
    if interval:
        levels_mode, levels = params.get("freshness_intervals", ("fixed", (2.0, 3.0)))

        if levels_mode == "fixed" and levels is not None:
            warn_multiplier, crit_multiplier = levels
            warn = int(interval * float(warn_multiplier))
            crit = int(interval * float(crit_multiplier))

            if age >= crit:
                freshness_state = State.CRIT
            elif age >= warn:
                freshness_state = State.WARN
            else:
                freshness_state = State.OK

            yield Result(
                state=freshness_state,
                summary=(
                    f"Execution freshness: {_human_age(age)}, interval {interval_text}"
                ),
            )
            yield Result(
                state=State.OK,
                notice=(
                    f"Freshness levels: WARN {_human_age(warn)}, CRIT {_human_age(crit)} "
                    f"({float(warn_multiplier):g}x/{float(crit_multiplier):g}x interval)"
                ),
            )
        else:
            yield Result(state=State.OK, notice="Execution freshness levels disabled")
    else:
        yield Result(
            state=State.UNKNOWN,
            summary=f"Unable to determine schedule interval ({interval_text or 'not reported'})",
        )

    error = execution.get("error")
    if error:
        yield Result(
            state=State.CRIT,
            summary="Last execution contains an error",
            details=json.dumps(error, indent=2, default=str),
        )


check_plugin_entra_cloudsync_execution = CheckPlugin(
    name="entra_cloudsync_execution",
    sections=["entra_cloudsync"],
    service_name="Entra Cloud Sync Execution %s",
    discovery_function=discover_entra_cloudsync_execution,
    check_function=check_entra_cloudsync_execution,
    check_default_parameters={
        "freshness_intervals": ("fixed", (2.0, 3.0)),
    },
    check_ruleset_name="entra_cloudsync_execution",
)


# ---------------------------------------------------------------------------
# Synchronized object counts
# ---------------------------------------------------------------------------


def discover_entra_cloudsync_objects(section):
    yield from _discover_jobs(section)


def check_entra_cloudsync_objects(item, section):
    job = _find_job(section, item)
    if job is None:
        yield Result(state=State.UNKNOWN, summary="Provisioning job not found")
        return

    status = job.get("status") or {}
    counts = status.get("object_counts") or []

    if not counts:
        yield Result(state=State.OK, summary="No synchronized object counts reported")
        return

    parts = []
    for entry in counts:
        key = str(entry.get("key") or "objects")
        try:
            value = int(entry.get("value") or 0)
        except (TypeError, ValueError):
            value = 0
        parts.append(f"{key}: {value}")
        yield Metric(f"synchronized_{_safe_metric_suffix(key)}", value)

    yield Result(state=State.OK, summary=", ".join(parts))


check_plugin_entra_cloudsync_objects = CheckPlugin(
    name="entra_cloudsync_objects",
    sections=["entra_cloudsync"],
    service_name="Entra Cloud Sync Objects %s",
    discovery_function=discover_entra_cloudsync_objects,
    check_function=check_entra_cloudsync_objects,
)


# ---------------------------------------------------------------------------
# Provisioning status / unresolved object failures
# ---------------------------------------------------------------------------


def discover_entra_cloudsync_provisioning(section):
    yield from _discover_jobs(section)


def check_entra_cloudsync_provisioning(item, section):
    job = _find_job(section, item)
    if job is None:
        yield Result(state=State.UNKNOWN, summary="Provisioning job not found")
        return

    logs = job.get("provisioning_logs") or {}
    if logs.get("error"):
        yield Result(
            state=State.UNKNOWN,
            summary="Unable to retrieve provisioning logs",
            details=str(logs["error"]),
        )
        return

    counts = logs.get("counts") or {}
    unresolved = logs.get("unresolved") or {}
    actions = logs.get("actions") or {}
    window = int(logs.get("window_minutes") or 60)

    successes = int(counts.get("success") or 0)
    historical_warnings = int(counts.get("warning") or 0)
    historical_failures = int(counts.get("failure") or 0)
    total = int(counts.get("total") or 0)
    unresolved_failures = int(unresolved.get("failure") or 0)
    unresolved_warnings = int(unresolved.get("warning") or 0)

    yield Metric("provisioning_operations", total)
    yield Metric("provisioning_successes", successes)
    yield Metric("provisioning_failures", historical_failures)
    yield Metric("provisioning_warnings", historical_warnings)
    yield Metric("provisioning_unresolved_failures", unresolved_failures)
    yield Metric("provisioning_unresolved_warnings", unresolved_warnings)

    if unresolved_failures > 0:
        state = State.CRIT
    elif unresolved_warnings > 0:
        state = State.WARN
    else:
        state = State.OK

    yield Result(
        state=state,
        summary=(
            f"{unresolved_failures} unresolved failures, "
            f"{unresolved_warnings} unresolved warnings"
        ),
    )

    yield Result(
        state=State.OK,
        notice=(
            f"Last {window} minutes: {historical_failures} failures, "
            f"{historical_warnings} warnings, {successes} successes"
        ),
    )

    if total == 0:
        yield Result(state=State.OK, notice="No provisioning operations in monitoring window")

    if actions:
        action_text = ", ".join(
            f"{name}: {count}" for name, count in sorted(actions.items())
        )
        yield Result(state=State.OK, notice=f"Actions: {action_text}")

    problem = logs.get("latest_problem")
    if problem:
        reason = (problem.get("reason") or "No error reason provided").replace("\r", "").strip()
        details = (
            f"Object: {problem.get('object', 'unknown')}\n"
            f"Time: {problem.get('time', 'unknown')}\n"
            f"Action: {problem.get('action', 'unknown')}\n"
            f"Status: {problem.get('status', 'unknown')}\n"
            f"Error code: {problem.get('error_code', 'unknown')}\n\n"
            f"Reason:\n{reason}"
        )
        yield Result(
            state=State.OK,
            notice=(
                "Latest unresolved error: "
                f"{problem.get('error_code', 'unknown')}"
            ),
            details=details,
        )


check_plugin_entra_cloudsync_provisioning = CheckPlugin(
    name="entra_cloudsync_provisioning",
    sections=["entra_cloudsync"],
    service_name="Entra Cloud Sync Provisioning %s",
    discovery_function=discover_entra_cloudsync_provisioning,
    check_function=check_entra_cloudsync_provisioning,
)


# ---------------------------------------------------------------------------
# Dropped/deprovisioned objects
# ---------------------------------------------------------------------------


def discover_entra_cloudsync_dropped(section):
    yield from _discover_jobs(section)


def check_entra_cloudsync_dropped(item, section):
    job = _find_job(section, item)
    if job is None:
        yield Result(state=State.UNKNOWN, summary="Provisioning job not found")
        return

    logs = job.get("provisioning_logs") or {}
    if logs.get("error"):
        yield Result(
            state=State.UNKNOWN,
            summary="Unable to retrieve provisioning logs",
            details=str(logs["error"]),
        )
        return

    dropped = logs.get("dropped_objects") or {}
    counts = dropped.get("counts") or {}

    deleted = int(counts.get("delete") or 0)
    staged = int(counts.get("stageddelete") or 0)
    disabled = int(counts.get("disable") or 0)
    skipped = int(counts.get("skipped") or 0)

    yield Metric("cloudsync_deleted_objects", deleted)
    yield Metric("cloudsync_staged_deleted_objects", staged)
    yield Metric("cloudsync_disabled_objects", disabled)
    yield Metric("cloudsync_skipped_objects", skipped)

    yield Result(
        state=State.OK,
        summary=(
            f"Deleted: {deleted}, staged delete: {staged}, "
            f"disabled: {disabled}, skipped: {skipped}"
        ),
    )

    events = dropped.get("events") or []
    if events:
        details = "\n".join(
            (
                f"{event.get('time', 'unknown')} - "
                f"{event.get('object', 'unknown')} - "
                f"{event.get('action', 'unknown')} - "
                f"{event.get('status', 'unknown')}"
            )
            for event in events
        )
        yield Result(
            state=State.OK,
            notice="Recent dropped/deprovisioned objects available",
            details=details,
        )


check_plugin_entra_cloudsync_dropped = CheckPlugin(
    name="entra_cloudsync_dropped",
    sections=["entra_cloudsync"],
    service_name="Entra Cloud Sync Dropped Objects %s",
    discovery_function=discover_entra_cloudsync_dropped,
    check_function=check_entra_cloudsync_dropped,
)


# ---------------------------------------------------------------------------
# Property synchronization activity
# ---------------------------------------------------------------------------


def discover_entra_cloudsync_properties(section):
    yield from _discover_jobs(section)


def check_entra_cloudsync_properties(item, section):
    job = _find_job(section, item)
    if job is None:
        yield Result(state=State.UNKNOWN, summary="Provisioning job not found")
        return

    logs = job.get("provisioning_logs") or {}
    if logs.get("error"):
        yield Result(
            state=State.UNKNOWN,
            summary="Unable to retrieve provisioning logs",
            details=str(logs["error"]),
        )
        return

    properties = logs.get("property_changes") or {}
    total = int(properties.get("total_changes") or 0)
    objects = int(properties.get("objects_changed") or 0)
    window = int(logs.get("window_minutes") or 60)

    yield Metric("cloudsync_property_changes", total)
    yield Metric("cloudsync_objects_with_property_changes", objects)

    object_word = "object" if objects == 1 else "objects"
    yield Result(
        state=State.OK,
        summary=(
            f"{total} property changes on {objects} {object_word} "
            f"in last {window} minutes"
        ),
    )

    attributes = properties.get("attributes") or []
    if attributes:
        attribute_text = ", ".join(
            f"{entry.get('name', 'unknown')}: {entry.get('count', 0)}"
            for entry in attributes[:20]
        )
        yield Result(
            state=State.OK,
            notice="Changed attributes available",
            details="Changed attribute counts:\n" + attribute_text,
        )


check_plugin_entra_cloudsync_properties = CheckPlugin(
    name="entra_cloudsync_properties",
    sections=["entra_cloudsync"],
    service_name="Entra Cloud Sync Property Changes %s",
    discovery_function=discover_entra_cloudsync_properties,
    check_function=check_entra_cloudsync_properties,
)
