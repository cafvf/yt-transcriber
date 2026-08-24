CI_WORKFLOW = ".github/workflows/ci.yml"
AGENT_INSTRUCTIONS = "AGENTS.md"


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as stream:
        return stream.read()


def test_ci_checkout_steps_preserve_git_history() -> None:
    text = _read(CI_WORKFLOW)

    checkout_count = text.count("uses: actions/checkout@v4")
    full_history_count = text.count("fetch-depth: 0")

    assert checkout_count == 2, "expected test and security checkout steps"
    assert full_history_count == checkout_count, (
        "history-aware tests require fetch-depth: 0 in every CI checkout"
    )


def test_candidate_autofix_policy_is_persistent() -> None:
    text = _read(AGENT_INSTRUCTIONS)

    required = (
        "## Candidate Auto-fix Policy",
        "isolated candidate clone or worktree",
        "explicit task-owned path allowlist",
        "never run broad auto-fix commands such as `ruff check --fix .`",
        "recompute tracked and untracked changed paths",
        "final quality gates are strict and non-mutating",
        "CI is always non-mutating",
        "validated candidate bytes",
    )
    for phrase in required:
        assert phrase in text, f"missing persistent candidate auto-fix policy phrase: {phrase}"
