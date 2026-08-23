"""Current public documentation layout and engineering-spec preservation."""

from pathlib import Path


def test_historical_public_docs_are_removed() -> None:
    paths = (
        Path("docs/00-auditoria-da-documentacao.md"),
        Path("docs/05-plano-de-execucao.md"),
        Path("docs/gate-reports"),
        Path("docs/patches"),
    )
    for path in paths:
        assert not path.exists(), path


def test_current_canonical_docs_exist() -> None:
    paths = (
        "docs/01-contrato-funcional.md",
        "docs/02-arquitetura.md",
        "docs/03-manual-de-uso.md",
        "docs/04-manual-de-instalacao.md",
        "docs/06-funcionalidades-futuras.md",
        "docs/07-glossario-e-decisoes.md",
        "docs/08-seguranca-e-segredos.md",
        "docs/09-production-readiness.md",
        "docs/10-recovery-semantics-adr.md",
        "docs/11-operator-runbook.md",
        "docs/12-deprecacoes-e-compatibilidade.md",
    )
    for path in paths:
        assert Path(path).is_file(), path


def test_specs_requirements_tasks_and_use_cases_remain() -> None:
    assert Path("specs/007-production-coherence/REQUIREMENTS.md").is_file()
    assert Path("specs/007-production-coherence/TASKS.md").is_file()
    assert Path("specs/001-use-cases/README.md").is_file()
    assert Path("specs/003-atomic-requirements/REQUIREMENT-INDEX.md").is_file()
