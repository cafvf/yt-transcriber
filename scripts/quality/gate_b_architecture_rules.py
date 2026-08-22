#!/usr/bin/env python3
"""Blocking semantic audit for PLAN-007 Gate B."""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_ERROR_FIELDS = {"code", "category", "retryable", "safe_message"}
REQUIRED_ERROR_CODES = {
    "youtube.auth_required",
    "youtube.video_unavailable",
    "youtube.no_audio_stream",
    "media.duration_exceeded",
    "media.language_not_allowed",
    "transcription.out_of_memory",
    "transcription.language_not_allowed",
    "diarization.unavailable",
    "operation.cancelled",
    "delivery.failed",
    "internal.invariant_violation",
}
DIRECT_RENDER_IO = {"mkdir", "open", "replace", "unlink", "write_bytes", "write_text"}


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    file: str
    line: int
    message: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _parse(root: Path, rel: str) -> ast.Module:
    path = root / rel
    return ast.parse(path.read_text(encoding="utf-8"), filename=rel)


def _class_fields(tree: ast.AST, class_name: str) -> set[str]:
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef) or node.name != class_name:
            continue
        fields: set[str] = set()
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                fields.add(item.target.id)
        return fields
    return set()


def _call_tail(call: ast.Call) -> str:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def audit(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    op_rel = "src/yt_transcriber_bot/application/ports/operational_error.py"
    op_tree = _parse(root, op_rel)
    fields = _class_fields(op_tree, "OperationalErrorRecord")
    missing = sorted(REQUIRED_ERROR_FIELDS - fields)
    if missing:
        findings.append(Finding("GB-ERR-001", op_rel, 1, f"missing fields: {missing!r}"))
    if {"message", "context", "error_type"} & fields:
        findings.append(Finding("GB-ERR-002", op_rel, 1, "legacy error fields remain first-class"))

    taxonomy_rel = "src/yt_transcriber_bot/application/operational_errors.py"
    taxonomy = (root / taxonomy_rel).read_text(encoding="utf-8")
    missing_codes = sorted(code for code in REQUIRED_ERROR_CODES if code not in taxonomy)
    if missing_codes:
        findings.append(
            Finding("GB-ERR-004", taxonomy_rel, 1, f"missing stable codes: {missing_codes!r}")
        )

    steps_rel = "src/yt_transcriber_bot/application/pipeline/steps.py"
    steps_tree = _parse(root, steps_rel)
    render = next(
        (
            node
            for node in ast.walk(steps_tree)
            if isinstance(node, ast.ClassDef) and node.name == "RenderMarkdownStep"
        ),
        None,
    )
    if render is None:
        findings.append(Finding("GB-MD-000", steps_rel, 1, "RenderMarkdownStep not found"))
    else:
        for node in ast.walk(render):
            if isinstance(node, ast.Call) and _call_tail(node) in DIRECT_RENDER_IO:
                findings.append(
                    Finding(
                        "GB-MD-001",
                        steps_rel,
                        node.lineno,
                        f"RenderMarkdownStep owns direct filesystem call {_call_tail(node)}",
                    )
                )

    usecase_rel = "src/yt_transcriber_bot/application/use_cases/transcribe_video.py"
    usecase_tree = _parse(root, usecase_rel)
    deps = _class_fields(usecase_tree, "TranscribeVideoDependencies")
    if "markdown_writer" not in deps:
        findings.append(
            Finding(
                "GB-MD-003",
                usecase_rel,
                1,
                "TranscribeVideoDependencies lacks markdown_writer",
            )
        )
    usecase_text = (root / usecase_rel).read_text(encoding="utf-8")
    if 'f"{type(exc).__name__}: {exc}"' in usecase_text:
        findings.append(
            Finding(
                "GB-ERR-003",
                usecase_rel,
                1,
                "raw exception class/detail remains failure contract",
            )
        )

    runner_rel = "src/yt_transcriber_bot/application/pipeline/runner.py"
    runner_text = (root / runner_rel).read_text(encoding="utf-8")
    if "error_type=" in runner_text or "error_message=str(exc)" in runner_text:
        findings.append(
            Finding(
                "GB-AUDIT-001",
                runner_rel,
                1,
                "audit still emits provider exception identity",
            )
        )

    for rel in (
        "src/yt_transcriber_bot/application/pipeline/steps.py",
        "src/yt_transcriber_bot/application/use_cases/transcribe_video.py",
    ):
        text = (root / rel).read_text(encoding="utf-8")
        if 'add_diagnostic(f"Falha ao listar legendas: {exc}")' in text:
            findings.append(
                Finding("GB-EXC-002", rel, 1, "raw subtitle exception reaches diagnostic")
            )
        if 'add_diagnostic(f"Falha ao baixar legenda: {exc}")' in text:
            findings.append(
                Finding("GB-EXC-002", rel, 1, "raw subtitle exception reaches diagnostic")
            )
        if "OOM durante transcrição ({exc})" in text:
            findings.append(Finding("GB-EXC-002", rel, 1, "raw OOM detail reaches diagnostic"))

    for scan_root in (root / "src", root / "tests", root / "scripts"):
        if not scan_root.exists():
            continue
        for path in scan_root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if (
                    not isinstance(node, ast.Call)
                    or _call_tail(node) != "TranscribeVideoDependencies"
                ):
                    continue
                keywords = {item.arg for item in node.keywords if item.arg is not None}
                if "markdown_writer" not in keywords:
                    findings.append(
                        Finding(
                            "GB-MD-005",
                            path.relative_to(root).as_posix(),
                            node.lineno,
                            "TranscribeVideoDependencies consumer omits markdown_writer",
                        )
                    )
            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                base_names = {base.id for base in node.bases if isinstance(base, ast.Name)}
                if "CanonicalMarkdownWriter" not in base_names:
                    continue
                methods = {
                    item.name
                    for item in node.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                }
                if "write_new" not in methods:
                    findings.append(
                        Finding(
                            "GB-MD-006",
                            path.relative_to(root).as_posix(),
                            node.lineno,
                            f"{node.name} omits CanonicalMarkdownWriter.write_new",
                        )
                    )

    app_root = root / "src/yt_transcriber_bot/application"
    for path in app_root.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Import, ast.ImportFrom)):
                continue
            modules: list[str]
            if isinstance(node, ast.Import):
                modules = [item.name for item in node.names]
            else:
                modules = [node.module or ""]
            if any(module.startswith("yt_transcriber_bot.infrastructure") for module in modules):
                findings.append(
                    Finding(
                        "GB-LAYER-001",
                        path.relative_to(root).as_posix(),
                        node.lineno,
                        "application imports infrastructure",
                    )
                )
    return findings


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo", type=Path)
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()
    root = args.repo.resolve()
    findings = audit(root)
    if args.json is not None:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps([item.to_dict() for item in findings], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    for item in findings:
        print(f"[FAIL] {item.code} {item.file}:{item.line} {item.message}")
    if findings:
        print(f"Gate B architecture blockers: {len(findings)}")
        return 1
    print("Gate B architecture blockers: 0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
