#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright (C) 2026 Sudhir Chauhan

"""Build the Microsoft Entra Cloud Sync Checkmk MKP from this repository."""

from __future__ import annotations

import io
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "manifest.json"
PLUGIN_ROOT = ROOT / "cmk_addons" / "plugins"
AGENTS_ROOT = ROOT / "agents"
DIST = ROOT / "dist"
FIXED_MTIME = 1_700_000_000

REQUIRED_MANIFEST_KEYS = {
    "name",
    "title",
    "version",
    "version.min_required",
    "version.usable_until",
    "version.packaged",
    "author",
    "description",
    "download_url",
    "license",
}


def _load_manifest() -> dict[str, object]:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    missing = sorted(REQUIRED_MANIFEST_KEYS - manifest.keys())
    if missing:
        raise ValueError(f"manifest.json is missing required keys: {', '.join(missing)}")
    if manifest["license"] != "GPL-2.0-only":
        raise ValueError("Checkmk Exchange packages in this repository must use GPL-2.0-only")
    return manifest


def _files_under(root: Path, base: Path) -> list[str]:
    if not root.is_dir():
        return []
    return sorted(
        str(path.relative_to(base))
        for path in root.rglob("*")
        if path.is_file()
        and "__pycache__" not in path.parts
        and path.suffix not in {".pyc", ".pyo"}
    )


def _normalized_tarinfo(source: Path, arcname: str) -> tarfile.TarInfo:
    stat = source.stat()
    info = tarfile.TarInfo(arcname)
    info.size = stat.st_size
    info.mtime = FIXED_MTIME
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mode = 0o755 if stat.st_mode & 0o111 else 0o644
    return info


def _component_tar(root: Path, files: list[str]) -> bytes:
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w") as archive:
        for rel in files:
            source = root / rel
            if not source.is_file():
                raise FileNotFoundError(source)
            info = _normalized_tarinfo(source, rel)
            with source.open("rb") as handle:
                archive.addfile(info, handle)
    return buffer.getvalue()


def _add_bytes(archive: tarfile.TarFile, name: str, content: bytes, mode: int = 0o644) -> None:
    info = tarfile.TarInfo(name)
    info.size = len(content)
    info.mtime = FIXED_MTIME
    info.uid = 0
    info.gid = 0
    info.uname = "root"
    info.gname = "root"
    info.mode = mode
    archive.addfile(info, io.BytesIO(content))


def build() -> Path:
    manifest = _load_manifest()
    name = str(manifest["name"])
    version = str(manifest["version"])

    plugin_dir = PLUGIN_ROOT / name
    if not plugin_dir.is_dir():
        raise FileNotFoundError(f"Plugin source tree does not exist: {plugin_dir}")

    files = {
        "agents": _files_under(AGENTS_ROOT, AGENTS_ROOT),
        "cmk_addons_plugins": _files_under(plugin_dir, PLUGIN_ROOT),
    }

    info = {
        "author": manifest.get("author", ""),
        "description": manifest.get("description", ""),
        "download_url": manifest.get("download_url", ""),
        "files": files,
        "name": name,
        "title": manifest["title"],
        "version": version,
        "version.min_required": manifest["version.min_required"],
        "version.packaged": manifest["version.packaged"],
        "version.usable_until": manifest["version.usable_until"],
    }

    components = {
        "agents.tar": _component_tar(AGENTS_ROOT, files["agents"]),
        "cmk_addons_plugins.tar": _component_tar(PLUGIN_ROOT, files["cmk_addons_plugins"]),
    }

    DIST.mkdir(exist_ok=True)
    output = DIST / f"{name}-{version}.mkp"
    output.unlink(missing_ok=True)

    info_repr = (repr(info) + "\n").encode("utf-8")
    info_json = (json.dumps(info, indent=2, sort_keys=False) + "\n").encode("utf-8")

    with tarfile.open(output, mode="w:gz") as archive:
        _add_bytes(archive, "info", info_repr)
        _add_bytes(archive, "info.json", info_json)
        for component_name in ("agents.tar", "cmk_addons_plugins.tar"):
            _add_bytes(archive, component_name, components[component_name])

    return output


if __name__ == "__main__":
    print(build())
