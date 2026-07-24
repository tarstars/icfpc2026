#!/usr/bin/env python3
"""Fail-closed preflight for ICFPC 2026 external-backed bulk roots."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LABEL = "medium_data"
DEFAULT_PROJECT_RELATIVE = Path("database/icfpc2026")
DEFAULT_LOGICAL_ROOTS = (
    Path("artifacts"),
    Path("outputs"),
    Path("yt_work"),
    Path("data/generated"),
    Path("data/external"),
)


class StoragePreflightError(RuntimeError):
    """The external storage layout is not safe for a bulk write."""


def _run_findmnt(arguments: Sequence[str]) -> list[str]:
    completed = subprocess.run(
        ["findmnt", "-rn", *arguments],
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode not in (0, 1):
        detail = completed.stderr.strip() or f"exit {completed.returncode}"
        raise StoragePreflightError(f"findmnt failed: {detail}")
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def find_mount_for_label(label: str) -> Path:
    mounts = _run_findmnt(["-S", f"LABEL={label}", "-o", "TARGET"])
    if not mounts:
        raise StoragePreflightError(
            f"no mounted filesystem with label {label!r}; bulk writes are blocked"
        )
    if len(mounts) != 1:
        raise StoragePreflightError(
            f"expected one mount for label {label!r}, found {len(mounts)}: {mounts}"
        )
    return Path(mounts[0])


def filesystem_label(path: Path) -> str:
    labels = _run_findmnt(["-T", str(path), "-o", "LABEL"])
    if len(labels) != 1 or not labels[0]:
        raise StoragePreflightError(f"cannot establish filesystem label for {path}")
    return labels[0]


def _beneath(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def validate_layout(
    *,
    repo_root: Path,
    mount_point: Path,
    label: str,
    project_relative: Path = DEFAULT_PROJECT_RELATIVE,
    logical_roots: Sequence[Path] = DEFAULT_LOGICAL_ROOTS,
    required_free_bytes: int = 0,
    label_for_path: Callable[[Path], str] = filesystem_label,
    disk_usage: Callable[[Path], Any] = shutil.disk_usage,
) -> dict[str, Any]:
    errors: list[str] = []
    links: dict[str, str] = {}

    if required_free_bytes < 0:
        raise ValueError("required_free_bytes must be non-negative")

    if not mount_point.is_dir():
        errors.append(f"mount point is not a directory: {mount_point}")
    else:
        try:
            actual_label = label_for_path(mount_point)
        except StoragePreflightError as error:
            errors.append(str(error))
        else:
            if actual_label != label:
                errors.append(
                    f"mount label mismatch for {mount_point}: "
                    f"expected {label!r}, got {actual_label!r}"
                )

    project_root = mount_point / project_relative
    if not project_root.is_dir():
        errors.append(f"physical project root is unavailable: {project_root}")
        resolved_project_root = project_root
        free_bytes = None
    else:
        resolved_project_root = project_root.resolve(strict=True)
        usage = disk_usage(resolved_project_root)
        free_bytes = int(usage.free)
        if free_bytes < required_free_bytes:
            errors.append(
                f"insufficient free space: need {required_free_bytes} bytes, "
                f"found {free_bytes}"
            )

    for relative in logical_roots:
        logical = repo_root / relative
        if not logical.is_symlink():
            errors.append(f"required logical root is not a symlink: {logical}")
            continue
        try:
            target = logical.resolve(strict=True)
        except FileNotFoundError:
            errors.append(f"logical root has a missing target: {logical}")
            continue
        links[str(relative)] = str(target)
        if not _beneath(target, resolved_project_root):
            errors.append(
                f"logical root escapes physical project root: {logical} -> {target}"
            )
            continue
        try:
            target_label = label_for_path(target)
        except StoragePreflightError as error:
            errors.append(str(error))
        else:
            if target_label != label:
                errors.append(
                    f"target label mismatch for {logical}: "
                    f"expected {label!r}, got {target_label!r}"
                )

    result = {
        "ok": not errors,
        "label": label,
        "mount_point": str(mount_point),
        "project_root": str(project_root),
        "required_free_bytes": required_free_bytes,
        "free_bytes": free_bytes,
        "links": links,
        "errors": errors,
    }
    if errors:
        raise StoragePreflightError("\n".join(errors))
    return result


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument(
        "--project-relative", type=Path, default=DEFAULT_PROJECT_RELATIVE
    )
    parser.add_argument(
        "--root",
        action="append",
        dest="logical_roots",
        type=Path,
        help="required repo-relative logical root; repeat to override defaults",
    )
    parser.add_argument("--required-free-gib", type=float, default=0.0)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.required_free_gib < 0:
        raise SystemExit("--required-free-gib must be non-negative")
    required_free_bytes = int(args.required_free_gib * (1024**3))
    logical_roots = tuple(args.logical_roots or DEFAULT_LOGICAL_ROOTS)
    try:
        mount_point = find_mount_for_label(args.label)
        result = validate_layout(
            repo_root=args.repo_root.resolve(),
            mount_point=mount_point,
            label=args.label,
            project_relative=args.project_relative,
            logical_roots=logical_roots,
            required_free_bytes=required_free_bytes,
        )
    except StoragePreflightError as error:
        if args.json:
            print(json.dumps({"ok": False, "error": str(error)}, indent=2))
        else:
            print(f"storage preflight: FAIL\n{error}")
        return 2

    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("storage preflight: PASS")
        print(f"label: {result['label']}")
        print(f"mount: {result['mount_point']}")
        print(f"project: {result['project_root']}")
        print(f"free bytes: {result['free_bytes']}")
        for logical, target in result["links"].items():
            print(f"{logical} -> {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
