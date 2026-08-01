from __future__ import annotations

import hashlib
import json
import zipfile
from collections import Counter
from pathlib import Path, PurePosixPath
from typing import Any

EXCLUDED_PARTS = {"cache", "raw", "__pycache__"}
EXCLUDED_NAMES = {".env", ".DS_Store", "manifest.json"}
FIXED_ZIP_TIME = (2020, 1, 1, 0, 0, 0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def collect_files(root: Path) -> list[Path]:
    files = []
    for path in root.rglob("*"):
        relative = path.relative_to(root)
        if path.is_symlink() or not path.is_file():
            continue
        if path.name in EXCLUDED_NAMES or any(part in EXCLUDED_PARTS for part in relative.parts):
            continue
        files.append(path)
    return sorted(files, key=lambda item: item.relative_to(root).as_posix())


def export_topic(root: Path, output: Path) -> dict[str, Any]:
    root, output = root.resolve(), output.resolve()
    if root == output or root in output.parents:
        raise ValueError("topic package output must be outside the topic workspace")
    if not (root / "topic.toml").exists() or not (root / "state.json").exists():
        raise ValueError("not a valid topic workspace")
    entries, payloads = [], []
    for path in collect_files(root):
        data = path.read_bytes()
        relative = path.relative_to(root).as_posix()
        entries.append({"path": relative, "size": len(data), "sha256": sha256_bytes(data)})
        payloads.append((relative, data))
    manifest = {"format": "deep-research-topic", "format_version": 1, "topic": root.name, "files": entries}
    manifest_bytes = (json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for relative, data in payloads + [("manifest.json", manifest_bytes)]:
            info = zipfile.ZipInfo(relative, FIXED_ZIP_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    return {"output": str(output), "file_count": len(entries), "archive_sha256": sha256_bytes(output.read_bytes()), "manifest": manifest}


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts and "\\" not in name


def verify_package(path: Path) -> dict[str, Any]:
    errors = []
    try:
        with zipfile.ZipFile(path, "r") as archive:
            listed = archive.namelist()
            duplicates = sorted(name for name, count in Counter(listed).items() if count > 1)
            if duplicates:
                errors.append(f"duplicate archive members: {duplicates}")
            unsafe = sorted(name for name in listed if not safe_member(name))
            if unsafe:
                errors.append(f"unsafe archive members: {unsafe}")
            names = set(listed)
            if "manifest.json" not in names:
                return {"valid": False, "errors": errors + ["manifest.json missing"]}
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("format") != "deep-research-topic" or manifest.get("format_version") != 1:
                errors.append("unsupported package format")
            expected_list = manifest.get("files", [])
            expected_names = [item.get("path") for item in expected_list]
            if len(expected_names) != len(set(expected_names)):
                errors.append("duplicate paths in manifest")
            expected = {item["path"]: item for item in expected_list if item.get("path")}
            for name, item in expected.items():
                if not safe_member(name):
                    errors.append(f"unsafe manifest path: {name}")
                elif name not in names:
                    errors.append(f"missing file: {name}")
                else:
                    data = archive.read(name)
                    if len(data) != item.get("size") or sha256_bytes(data) != item.get("sha256"):
                        errors.append(f"checksum mismatch: {name}")
            extras = names - set(expected) - {"manifest.json"}
            if extras:
                errors.append(f"unlisted files: {sorted(extras)}")
    except (OSError, zipfile.BadZipFile, json.JSONDecodeError, KeyError, TypeError) as exc:
        errors.append(f"invalid package: {exc}")
    return {"valid": not errors, "errors": errors, "archive_sha256": sha256_bytes(path.read_bytes()) if path.exists() else None}
