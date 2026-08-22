#!/usr/bin/env python3
"""Read-only AST/semantic audits for PLAN-007 Gate A.

The auditor intentionally ignores bare string literals. Legacy vocabulary only becomes a
finding when it participates in imports, identifiers, annotations, call keywords,
**kwargs data flow, positive conformance assertions, or canonical state comparisons.
This prevents rule declarations, negative fixtures, documentation, and absence tests from
being misclassified as API consumers.
"""

from __future__ import annotations

import argparse
import ast
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Finding:
    code: str
    file: str
    line: int
    category: str
    contract: str
    severity: str
    message: str
    suggestion: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


LEGACY_CORE_IDENTIFIERS = {
    "VideoMetadata": ("P07-002 MediaMetadata", "Replace with MediaMetadata."),
    "config_signature": (
        "P07-004 processing_fingerprint",
        "Use processing_fingerprint in domain/application; keep config_signature only as an isolated "
        "physical SQL name.",
    ),
    "transcription_signature": (
        "P07-004 processing_fingerprint",
        "Replace with processing_fingerprint.",
    ),
    "compute_config_signature": (
        "P07-004 processing_fingerprint",
        "Use the canonical processing fingerprint service/API.",
    ),
    "artifact_policy": (
        "P07-005 duration/artifact taxonomy",
        "Remove behavioral artifact_policy from Job/application/domain; a physical SQL column may remain "
        "only at persistence boundary.",
    ),
    "max_video_duration_min": (
        "P07-005 duration/artifact taxonomy",
        "Use max_media_duration_min internally. MAX_VIDEO_DURATION_MIN is only an external env alias.",
    ),
}

LEGACY_CALL_KEYS = {
    "config_signature": "P07-004 processing_fingerprint",
    "transcription_signature": "P07-004 processing_fingerprint",
    "artifact_policy": "P07-005 duration/artifact taxonomy",
    "max_video_duration_min": "P07-005 duration/artifact taxonomy",
}

LANGUAGE_FIELDS = {
    "requested_language",
    "transcription_language",
    "observed_language",
    "language_source",
}

CANONICAL_CALL_TARGETS = {
    "Job",
    "PipelineContext",
    "ProcessingProvenance",
    "MediaMetadata",
    "admit_youtube_submission",
    "transcribe_video",
    "TranscribeVideo",
}

ALLOWED_SQL_COMPAT_PREFIXES = (
    "src/yt_transcriber_bot/infrastructure/persistence/",
    "tests/unit/infrastructure/persistence/",
)

PYTHON_SCAN_PREFIXES = ("src", "tests", "scripts")


class ParsedFile:
    def __init__(self, root: Path, path: Path) -> None:
        self.root = root
        self.path = path
        self.rel = path.relative_to(root).as_posix()
        self.text = path.read_text(encoding="utf-8")
        self.tree = ast.parse(self.text, filename=self.rel)
        self.parents: dict[ast.AST, ast.AST] = {}
        for node in ast.walk(self.tree):
            for child in ast.iter_child_nodes(node):
                self.parents[child] = node

    def ancestor_iter(self, node: ast.AST) -> Iterable[ast.AST]:
        current = self.parents.get(node)
        while current is not None:
            yield current
            current = self.parents.get(current)

    def inside_pytest_raises(self, node: ast.AST) -> bool:
        for ancestor in self.ancestor_iter(node):
            if not isinstance(ancestor, ast.With):
                continue
            for item in ancestor.items:
                expr = item.context_expr
                if isinstance(expr, ast.Call) and call_name(expr.func) in {
                    "raises",
                    "pytest.raises",
                }:
                    return True
        return False


class Audit:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()
        self.findings: list[Finding] = []
        self.parsed: list[ParsedFile] = []

    def add(
        self,
        *,
        code: str,
        file: str,
        line: int,
        category: str,
        contract: str,
        severity: str,
        message: str,
        suggestion: str,
    ) -> None:
        self.findings.append(
            Finding(
                code=code,
                file=file,
                line=max(1, line),
                category=category,
                contract=contract,
                severity=severity,
                message=message,
                suggestion=suggestion,
            )
        )

    def parse_files(self) -> None:
        for prefix in PYTHON_SCAN_PREFIXES:
            base = self.root / prefix
            if not base.exists():
                continue
            for path in sorted(base.rglob("*.py")):
                if any(part in {".venv", "__pycache__", ".git"} for part in path.parts):
                    continue
                try:
                    self.parsed.append(ParsedFile(self.root, path))
                except (OSError, UnicodeDecodeError, SyntaxError) as exc:
                    line = exc.lineno if isinstance(exc, SyntaxError) and exc.lineno else 1
                    self.add(
                        code="GA-PARSE-001",
                        file=path.relative_to(self.root).as_posix(),
                        line=line,
                        category="syntax",
                        contract="Gate A diagnosability",
                        severity="error",
                        message=f"AST parse failed: {exc}",
                        suggestion="Fix syntax/encoding so semantic audits can inspect this file.",
                    )

    def run(self) -> list[Finding]:
        self.check_canonical_files()
        self.parse_files()
        for pf in self.parsed:
            self.check_layer_imports(pf)
            self.check_legacy_identifiers(pf)
            self.check_legacy_noncore_consumers(pf)
            self.check_direct_call_consumers(pf)
            self.check_kwargs_consumers(pf)
            self.check_typed_language_consumers(pf)
            self.check_positive_stale_assertions(pf)
        self.check_canonical_types()
        self.check_audio_track_selection()
        self.check_config_taxonomy()
        self.check_sql_physical_mapping()
        return sorted(self.findings, key=lambda f: (f.file, f.line, f.code, f.message))

    def check_canonical_files(self) -> None:
        required = {
            "src/yt_transcriber_bot/domain/entities/media_metadata.py": "P07-002 MediaMetadata",
            "src/yt_transcriber_bot/application/services/processing_fingerprint.py": "P07-004 processing_fingerprint",
        }
        forbidden = {
            "src/yt_transcriber_bot/domain/entities/video_metadata.py": "P07-002 MediaMetadata",
            "src/yt_transcriber_bot/application/services/config_signature.py": "P07-004 processing_fingerprint",
        }
        for rel, contract in required.items():
            if not (self.root / rel).is_file():
                self.add(
                    code="GA-FILE-MISSING",
                    file=rel,
                    line=1,
                    category="canonical-file",
                    contract=contract,
                    severity="error",
                    message="Required canonical module is missing.",
                    suggestion="Restore the canonical module without resurrecting the legacy API.",
                )
        for rel, contract in forbidden.items():
            if (self.root / rel).exists():
                self.add(
                    code="GA-FILE-LEGACY",
                    file=rel,
                    line=1,
                    category="canonical-file",
                    contract=contract,
                    severity="error",
                    message="Legacy core/application module still exists.",
                    suggestion="Remove the legacy module and migrate real consumers to the canonical API.",
                )

    def check_layer_imports(self, pf: ParsedFile) -> None:
        rel = pf.rel
        forbidden_layers: tuple[str, ...]
        if rel.startswith("src/yt_transcriber_bot/domain/"):
            forbidden_layers = ("application", "infrastructure")
        elif rel.startswith("src/yt_transcriber_bot/application/"):
            forbidden_layers = ("infrastructure",)
        else:
            return
        for node in ast.walk(pf.tree):
            modules: list[str] = []
            if isinstance(node, ast.Import):
                modules = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                modules = [node.module or ""]
            else:
                continue
            for module in modules:
                normalized = module.lstrip(".")
                for layer in forbidden_layers:
                    if (
                        normalized.startswith(f"yt_transcriber_bot.{layer}")
                        or f".{layer}." in normalized
                        or normalized == layer
                    ):
                        self.add(
                            code="GA-LAYER-DEP",
                            file=rel,
                            line=node.lineno,
                            category="layer-dependency",
                            contract="PLAN-007 layer direction",
                            severity="error",
                            message=f"{rel.split('/')[2]} layer imports forbidden {layer} layer: {module}",
                            suggestion=(
                                "Invert the dependency through a domain/application port or move boundary "
                                "conversion outward."
                            ),
                        )

    def check_legacy_identifiers(self, pf: ParsedFile) -> None:
        rel = pf.rel
        in_core = rel.startswith("src/yt_transcriber_bot/domain/") or rel.startswith(
            "src/yt_transcriber_bot/application/"
        )
        if not in_core:
            return
        for node in ast.walk(pf.tree):
            identifier: str | None = None
            if isinstance(node, ast.Name):
                identifier = node.id
            elif isinstance(node, ast.Attribute):
                identifier = node.attr
            elif isinstance(node, ast.arg):
                identifier = node.arg
            if identifier not in LEGACY_CORE_IDENTIFIERS:
                continue
            contract, suggestion = LEGACY_CORE_IDENTIFIERS[identifier]
            self.add(
                code="GA-CORE-LEGACY",
                file=rel,
                line=getattr(node, "lineno", 1),
                category="taxonomy",
                contract=contract,
                severity="error",
                message=f"Legacy identifier '{identifier}' is consumed inside domain/application.",
                suggestion=suggestion,
            )

    def check_legacy_noncore_consumers(self, pf: ParsedFile) -> None:
        rel = pf.rel
        if not (rel.startswith("tests/") or rel.startswith("scripts/")):
            return
        for node in ast.walk(pf.tree):
            identifier: str | None = None
            semantic = False
            if isinstance(node, ast.Attribute):
                identifier = node.attr
                semantic = True
            elif isinstance(node, ast.alias):
                identifier = node.asname or node.name.split(".")[-1]
                semantic = True
            elif isinstance(node, ast.Name) and node.id in {
                "VideoMetadata",
                "compute_config_signature",
            }:
                identifier = node.id
                semantic = True
            if not semantic or identifier not in LEGACY_CORE_IDENTIFIERS:
                continue
            if rel.startswith("tests/unit/infrastructure/persistence/") and identifier in {
                "config_signature",
                "artifact_policy",
            }:
                continue
            contract, suggestion = LEGACY_CORE_IDENTIFIERS[identifier]
            self.add(
                code="GA-CONSUMER-LEGACY",
                file=rel,
                line=getattr(node, "lineno", 1),
                category="test-script-consumer",
                contract=contract,
                severity="error",
                message=f"Test/script code consumes legacy API identifier '{identifier}'.",
                suggestion=suggestion,
            )

    def check_direct_call_consumers(self, pf: ParsedFile) -> None:
        rel = pf.rel
        for node in ast.walk(pf.tree):
            if not isinstance(node, ast.Call):
                continue
            target = call_name(node.func)
            for kw in node.keywords:
                if kw.arg not in LEGACY_CALL_KEYS:
                    continue
                if self._allowed_physical_sql_usage(rel, target):
                    continue
                if pf.inside_pytest_raises(node):
                    continue
                self.add(
                    code="GA-CALL-LEGACY",
                    file=rel,
                    line=kw.value.lineno,
                    category="direct-call-consumer",
                    contract=LEGACY_CALL_KEYS[kw.arg],
                    severity="error",
                    message=f"Call '{target or '<dynamic>'}' passes legacy keyword '{kw.arg}'.",
                    suggestion="Rename the call-site contract to the canonical field before Gate A closes.",
                )

    def check_kwargs_consumers(self, pf: ParsedFile) -> None:
        scopes: list[ast.AST] = [pf.tree]
        scopes.extend(
            node
            for node in ast.walk(pf.tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        for scope in scopes:
            mappings: dict[str, tuple[set[str], int]] = {}
            for node in ast.walk(scope):
                if not self._belongs_to_scope(node, scope, pf.parents):
                    continue
                if isinstance(node, (ast.Assign, ast.AnnAssign)):
                    name, value = assignment_name_and_value(node)
                    if name and isinstance(value, ast.Dict):
                        keys = {
                            key.value
                            for key in value.keys
                            if isinstance(key, ast.Constant) and isinstance(key.value, str)
                        }
                        legacy = keys & LEGACY_CALL_KEYS.keys()
                        if legacy:
                            mappings[name] = (legacy, node.lineno)
            if not mappings:
                continue
            for node in ast.walk(scope):
                if not isinstance(node, ast.Call) or not self._belongs_to_scope(
                    node, scope, pf.parents
                ):
                    continue
                if pf.inside_pytest_raises(node):
                    continue
                target = call_name(node.func)
                for kw in node.keywords:
                    if kw.arg is not None or not isinstance(kw.value, ast.Name):
                        continue
                    mapping = mappings.get(kw.value.id)
                    if mapping is None:
                        continue
                    legacy_keys, producer_line = mapping
                    if self._allowed_physical_sql_usage(pf.rel, target):
                        continue
                    for key in sorted(legacy_keys):
                        self.add(
                            code="GA-KWARGS-CONSUMER",
                            file=pf.rel,
                            line=node.lineno,
                            category="kwargs-consumer",
                            contract=LEGACY_CALL_KEYS[key],
                            severity="error",
                            message=(
                                f"Mapping '{kw.value.id}' defined at line {producer_line} contains legacy key '{key}' "
                                f"and is expanded into call '{target or '<dynamic>'}'."
                            ),
                            suggestion=(
                                "Migrate the mapping producer to the canonical key; one producer may feed "
                                "multiple consumers, "
                                "so validate every **kwargs expansion."
                            ),
                        )

    @staticmethod
    def _belongs_to_scope(node: ast.AST, scope: ast.AST, parents: dict[ast.AST, ast.AST]) -> bool:
        current = node
        while current in parents:
            parent = parents[current]
            if parent is scope:
                return True
            if (
                isinstance(
                    parent, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)
                )
                and parent is not scope
            ):
                return False
            current = parent
        return scope is current

    @staticmethod
    def _allowed_physical_sql_usage(rel: str, target: str) -> bool:
        if not rel.startswith(ALLOWED_SQL_COMPAT_PREFIXES):
            return False
        core_targets = {name.lower() for name in CANONICAL_CALL_TARGETS}
        return target.split(".")[-1].lower() not in core_targets

    def check_typed_language_consumers(self, pf: ParsedFile) -> None:
        rel = pf.rel
        core = rel.startswith("src/yt_transcriber_bot/domain/") or rel.startswith(
            "src/yt_transcriber_bot/application/"
        )
        config_boundary = rel == "src/yt_transcriber_bot/application/config.py"
        for node in ast.walk(pf.tree):
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and core
                and not config_boundary
            ):
                for arg in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs):
                    if arg.arg not in LANGUAGE_FIELDS or arg.annotation is None:
                        continue
                    annotation = normalized_annotation(arg.annotation)
                    if is_string_annotation(annotation):
                        self.add(
                            code="GA-LANG-RAW-ANNOTATION",
                            file=rel,
                            line=arg.lineno,
                            category="typed-boundary",
                            contract="P07-003 typed language",
                            severity="error",
                            message=f"Core parameter '{arg.arg}' is annotated as raw string ({annotation}).",
                            suggestion=(
                                "Convert str at the external/infrastructure boundary and pass "
                                "Language/LanguageSource inward."
                            ),
                        )
            if isinstance(node, ast.Call):
                if pf.inside_pytest_raises(node):
                    continue
                target = call_name(node.func)
                target_leaf = target.split(".")[-1]
                if target_leaf not in CANONICAL_CALL_TARGETS and not core:
                    continue
                for kw in node.keywords:
                    if kw.arg not in LANGUAGE_FIELDS:
                        continue
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        self.add(
                            code="GA-LANG-RAW-CALL",
                            file=rel,
                            line=kw.value.lineno,
                            category="typed-boundary",
                            contract="P07-003 typed language",
                            severity="error",
                            message=f"Call '{target or '<dynamic>'}' passes raw string to '{kw.arg}'.",
                            suggestion=(
                                "Construct Language/LanguageSource explicitly at the boundary before calling "
                                "core APIs."
                            ),
                        )
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and core and not config_boundary:
                name, value = assignment_name_and_value(node)
                if (
                    name in LANGUAGE_FIELDS
                    and isinstance(value, ast.Constant)
                    and isinstance(value.value, str)
                ):
                    self.add(
                        code="GA-LANG-RAW-ASSIGN",
                        file=rel,
                        line=node.lineno,
                        category="typed-boundary",
                        contract="P07-003 typed language",
                        severity="error",
                        message=f"Core state '{name}' is assigned a raw string literal.",
                        suggestion="Assign a Language/LanguageSource value object/enum instead.",
                    )
            if (
                isinstance(node, ast.Compare)
                and core
                and not config_boundary
                and comparison_uses_language_field_and_string(node)
            ):
                self.add(
                    code="GA-LANG-RAW-COMPARE",
                    file=rel,
                    line=node.lineno,
                    category="typed-boundary",
                    contract="P07-003 typed language",
                    severity="error",
                    message="Core language state is compared directly with a string literal.",
                    suggestion="Compare typed Language/LanguageSource values, converting only at boundaries.",
                )

    def check_positive_stale_assertions(self, pf: ParsedFile) -> None:
        if not pf.rel.startswith("tests/"):
            return
        for node in ast.walk(pf.tree):
            if not isinstance(node, ast.Assert):
                continue
            test = node.test
            if is_negative_assertion(test):
                continue
            legacy = legacy_literals_in_semantic_assert(test)
            for token in sorted(legacy):
                if pf.rel.startswith("tests/unit/infrastructure/persistence/") and token in {
                    "config_signature",
                    "artifact_policy",
                }:
                    continue
                contract = (
                    LEGACY_CALL_KEYS.get(token)
                    or LEGACY_CORE_IDENTIFIERS.get(token, ("PLAN-007 taxonomy", ""))[0]
                )
                self.add(
                    code="GA-CONFORMANCE-STALE",
                    file=pf.rel,
                    line=node.lineno,
                    category="conformance-expectation",
                    contract=contract,
                    severity="error",
                    message=f"Positive test assertion appears to require legacy token '{token}'.",
                    suggestion=(
                        "Rewrite the expectation around the canonical API. Negative absence assertions may "
                        "retain the legacy string."
                    ),
                )

    def check_canonical_types(self) -> None:
        expectations = [
            (
                "src/yt_transcriber_bot/application/pipeline/context.py",
                "PipelineContext",
                {
                    "requested_language": {
                        "Language | None",
                        "None | Language",
                        "Optional[Language]",
                    },
                    "transcription_language": {
                        "Language | None",
                        "None | Language",
                        "Optional[Language]",
                    },
                    "observed_language": {
                        "Language | None",
                        "None | Language",
                        "Optional[Language]",
                    },
                    "language_source": {"LanguageSource"},
                },
                {"language_source": "LanguageSource.UNKNOWN"},
                "P07-003 typed language",
            ),
            (
                "src/yt_transcriber_bot/domain/entities/job.py",
                "Job",
                {
                    "requested_language": {
                        "Language | None",
                        "None | Language",
                        "Optional[Language]",
                    },
                    "processing_fingerprint": {"str", "str | None", "None | str", "Optional[str]"},
                },
                {},
                "P07-003/P07-004 canonical Job",
            ),
            (
                "src/yt_transcriber_bot/domain/value_objects/provenance.py",
                "ProcessingProvenance",
                {
                    "language_source": {
                        "LanguageSource | None",
                        "None | LanguageSource",
                        "Optional[LanguageSource]",
                    }
                },
                {},
                "P07-003 typed language",
            ),
        ]
        parsed_by_rel = {pf.rel: pf for pf in self.parsed}
        for rel, class_name, fields, defaults, contract in expectations:
            pf = parsed_by_rel.get(rel)
            if pf is None:
                continue
            cls = next(
                (n for n in pf.tree.body if isinstance(n, ast.ClassDef) and n.name == class_name),
                None,
            )
            if cls is None:
                self.add(
                    code="GA-CANONICAL-CLASS-MISSING",
                    file=rel,
                    line=1,
                    category="typed-contract",
                    contract=contract,
                    severity="error",
                    message=f"Canonical class '{class_name}' was not found.",
                    suggestion="Restore the canonical class definition before closing Gate A.",
                )
                continue
            annotations: dict[str, str] = {}
            values: dict[str, str] = {}
            for stmt in cls.body:
                if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                    annotations[stmt.target.id] = normalized_annotation(stmt.annotation)
                    if stmt.value is not None:
                        values[stmt.target.id] = ast.unparse(stmt.value).replace(" ", "")
            for field, allowed in fields.items():
                actual = annotations.get(field)
                normalized_allowed = {value.replace(" ", "") for value in allowed}
                if actual is None or actual.replace(" ", "") not in normalized_allowed:
                    self.add(
                        code="GA-CANONICAL-TYPE",
                        file=rel,
                        line=cls.lineno,
                        category="typed-contract",
                        contract=contract,
                        severity="error",
                        message=f"{class_name}.{field} annotation is {actual!r}; expected one of {sorted(allowed)}.",
                        suggestion="Use the canonical typed field exactly at the domain/application boundary.",
                    )
            for field, expected_default in defaults.items():
                actual_default = values.get(field)
                if actual_default != expected_default.replace(" ", ""):
                    self.add(
                        code="GA-CANONICAL-DEFAULT",
                        file=rel,
                        line=cls.lineno,
                        category="typed-contract",
                        contract=contract,
                        severity="error",
                        message=f"{class_name}.{field} default is {actual_default!r}; expected {expected_default}.",
                        suggestion="Restore the canonical default semantics.",
                    )

    def check_audio_track_selection(self) -> None:
        matches: list[tuple[ParsedFile, ast.ClassDef]] = []
        for pf in self.parsed:
            if not pf.rel.startswith("src/yt_transcriber_bot/"):
                continue
            for node in ast.walk(pf.tree):
                if isinstance(node, ast.ClassDef) and node.name == "AudioTrackSelection":
                    matches.append((pf, node))
        if not matches:
            self.add(
                code="GA-AUDIO-ENUM-MISSING",
                file="src/yt_transcriber_bot",
                line=1,
                category="audio-taxonomy",
                contract="P07-001 AudioTrackSelection",
                severity="error",
                message="AudioTrackSelection enum/class not found.",
                suggestion="Keep the A1 canonical enum with ORIGINAL, DEFAULT, UNKNOWN.",
            )
            return
        for pf, cls in matches:
            members = {
                stmt.targets[0].id
                for stmt in cls.body
                if isinstance(stmt, ast.Assign)
                and len(stmt.targets) == 1
                and isinstance(stmt.targets[0], ast.Name)
            }
            required = {"ORIGINAL", "DEFAULT", "UNKNOWN"}
            missing = required - members
            if missing:
                self.add(
                    code="GA-AUDIO-ENUM-MEMBERS",
                    file=pf.rel,
                    line=cls.lineno,
                    category="audio-taxonomy",
                    contract="P07-001 AudioTrackSelection",
                    severity="error",
                    message=f"AudioTrackSelection is missing canonical members: {sorted(missing)}.",
                    suggestion="Restore ORIGINAL, DEFAULT, UNKNOWN as the successful/unknown canonical taxonomy.",
                )
            if "AUTO_DUB" in members:
                self.add(
                    code="GA-AUDIO-AUTODUB",
                    file=pf.rel,
                    line=cls.lineno,
                    category="audio-taxonomy",
                    contract="P07-001 AudioTrackSelection",
                    severity="error",
                    message="AUTO_DUB exists as a canonical AudioTrackSelection state.",
                    suggestion=(
                        "Represent alternative-track existence as metadata; do not expose AUTO_DUB as "
                        "canonical success."
                    ),
                )

    def check_config_taxonomy(self) -> None:
        rel = "src/yt_transcriber_bot/application/config.py"
        path = self.root / rel
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        for token, contract in [
            ("max_media_duration_min", "P07-005 internal config"),
            ("MAX_MEDIA_DURATION_MIN", "P07-005 canonical env"),
            ("MAX_VIDEO_DURATION_MIN", "COMPAT-004 external env alias"),
        ]:
            if token not in text:
                self.add(
                    code="GA-CONFIG-TOKEN-MISSING",
                    file=rel,
                    line=1,
                    category="configuration-taxonomy",
                    contract=contract,
                    severity="error",
                    message=f"Expected configuration token '{token}' is absent.",
                    suggestion=(
                        "Keep canonical internal naming and the documented external alias with canonical "
                        "precedence."
                    ),
                )

    def check_sql_physical_mapping(self) -> None:
        rel = "src/yt_transcriber_bot/infrastructure/persistence/sqlalchemy/job_repository.py"
        pf = next((item for item in self.parsed if item.rel == rel), None)
        if pf is None:
            return
        write_ok = False
        read_ok = False
        for node in ast.walk(pf.tree):
            if isinstance(node, ast.keyword) and node.arg == "config_signature":
                value = ast.unparse(node.value).replace(" ", "")
                if value.endswith(".processing_fingerprint") or value == "processing_fingerprint":
                    write_ok = True
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute) and target.attr == "config_signature":
                        value = ast.unparse(node.value).replace(" ", "")
                        if (
                            value.endswith(".processing_fingerprint")
                            or value == "processing_fingerprint"
                        ):
                            write_ok = True
            if isinstance(node, ast.keyword) and node.arg == "processing_fingerprint":
                value = ast.unparse(node.value).replace(" ", "")
                if value.endswith(".config_signature"):
                    read_ok = True
        if not write_ok:
            self.add(
                code="GA-SQL-COMPAT-WRITE",
                file=rel,
                line=1,
                category="persistence-compatibility",
                contract="COMPAT-003 SQL physical config_signature",
                severity="error",
                message="Could not prove canonical processing_fingerprint -> physical config_signature write mapping.",
                suggestion=(
                    "Keep the legacy SQL column isolated and map job.processing_fingerprint explicitly when "
                    "persisting."
                ),
            )
        if not read_ok:
            self.add(
                code="GA-SQL-COMPAT-READ",
                file=rel,
                line=1,
                category="persistence-compatibility",
                contract="COMPAT-003 SQL physical config_signature",
                severity="error",
                message="Could not prove physical config_signature -> canonical processing_fingerprint read mapping.",
                suggestion=(
                    "Map model.config_signature explicitly into processing_fingerprint when hydrating the "
                    "domain Job."
                ),
            )


def assignment_name_and_value(
    node: ast.Assign | ast.AnnAssign,
) -> tuple[str | None, ast.expr | None]:
    if isinstance(node, ast.Assign):
        if len(node.targets) != 1:
            return None, node.value
        target = node.targets[0]
        value: ast.expr | None = node.value
    else:
        target = node.target
        value = node.value
    if isinstance(target, ast.Name):
        return target.id, value
    if isinstance(target, ast.Attribute):
        return target.attr, value
    return None, value


def call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = call_name(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


def normalized_annotation(node: ast.expr) -> str:
    return ast.unparse(node).replace("typing.", "")


def is_string_annotation(annotation: str) -> bool:
    compact = annotation.replace(" ", "")
    return compact in {"str", "str|None", "None|str", "Optional[str]"}


def expression_name(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def comparison_uses_language_field_and_string(node: ast.Compare) -> bool:
    operands: list[ast.expr] = [node.left, *node.comparators]
    has_field = any(expression_name(item) in LANGUAGE_FIELDS for item in operands)
    has_str = any(
        isinstance(item, ast.Constant) and isinstance(item.value, str) for item in operands
    )
    return has_field and has_str


def is_negative_assertion(node: ast.expr) -> bool:
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        return True
    return isinstance(node, ast.Compare) and any(
        isinstance(op, (ast.NotIn, ast.IsNot)) for op in node.ops
    )


def legacy_literals_in_semantic_assert(node: ast.expr) -> set[str]:
    legacy_tokens = set(LEGACY_CALL_KEYS) | set(LEGACY_CORE_IDENTIFIERS)
    found: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call) and call_name(child.func).endswith("hasattr"):
            for arg in child.args[1:]:
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, str)
                    and arg.value in legacy_tokens
                ):
                    found.add(arg.value)
        elif isinstance(child, ast.Compare) and any(
            isinstance(op, (ast.In, ast.Eq, ast.Is)) for op in child.ops
        ):
            for operand in [child.left, *child.comparators]:
                if (
                    isinstance(operand, ast.Constant)
                    and isinstance(operand.value, str)
                    and operand.value in legacy_tokens
                ):
                    found.add(operand.value)
    return found


def audit_repository(root: Path) -> list[Finding]:
    return Audit(root).run()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repo", type=Path)
    parser.add_argument("--json", type=Path, default=None)
    args = parser.parse_args()
    findings = audit_repository(args.repo)
    payload = [finding.to_dict() for finding in findings]
    if args.json:
        args.json.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    for finding in findings:
        print(
            f"{finding.code} {finding.file}:{finding.line} [{finding.severity}] "
            f"{finding.category} — {finding.contract} — {finding.message}"
        )
    return 1 if any(f.severity in {"error", "critical"} for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
