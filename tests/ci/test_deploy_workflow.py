"""Regression tests for the CI deploy workflow (spec S2/S3).

The build job must generate presentaciones_html bundles from the seed
before copying them into web/public/presentaciones_html, otherwise every
presentation iframe 404s on GitHub Pages.
"""

from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "deploy.yml"


def _load():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps(job: dict) -> list:
    return list(job.get("steps", []))


def test_build_job_generates_bundles_between_seed_copy_and_public_copy():
    wf = _load()
    build = wf["jobs"]["build"]
    names = [step.get("name", "") for step in _steps(build)]
    order = [
        "Set up runtime data from seeds",
        "Generate presentacion bundles from seed",
        "Copy presentaciones assets to public",
        "Export data from SQLite to JSON for Astro",
        "Build site",
    ]
    indices = [names.index(name) for name in order]
    assert indices == sorted(indices), f"unexpected step order: {names}"


def test_generate_step_uses_module_invocation_and_project_dir_env():
    wf = _load()
    build = wf["jobs"]["build"]
    step = next(
        s
        for s in _steps(build)
        if s.get("name") == "Generate presentacion bundles from seed"
    )
    assert "python -m src.generators.generar_desde_composicion --fecha" in step["run"]
    assert step.get("env", {}).get("CCE_PROJECT_DIR") == "${{ github.workspace }}"
    assert "PYTHONPATH=src:scripts:." in step["run"]


def test_build_job_has_weasyprint_system_dependencies():
    wf = _load()
    build = wf["jobs"]["build"]
    names = [step.get("name", "") for step in _steps(build)]
    assert "Install system dependencies for WeasyPrint" in names


def test_setup_python_steps_are_identical_across_jobs():
    wf = _load()
    for name in ("Set up Python", "Install Python dependencies", "Install system dependencies for WeasyPrint"):
        a = next(s for s in _steps(wf["jobs"]["lint-and-test"]) if s.get("name") == name)
        b = next(s for s in _steps(wf["jobs"]["build"]) if s.get("name") == name)
        assert a == b, f"step {name!r} differs between lint-and-test and build"
