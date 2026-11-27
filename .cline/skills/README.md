# Cline Skills

This directory contains Cline skill definitions for the Fitness Assistant project.

## Skills

| Skill | File | Purpose | Executable |
|-------|------|---------|------------|
| **pr-writer** | `pr-writer/skill.yaml` | Generate conventional English PR descriptions from git diff | ⚠️ Depends on `git_diff_stat`/`git_diff_files` tools |
| **pr-reviewer** | `pr-reviewer/skill.yaml` | Code review template (TDD, best practices, LLM safety, security) | ⚠️ Depends on `git_diff_files` tool |
| **red-team** | `red-team/skill.yaml` | Garak-style LLM safety probe definitions and report template | Documentation template — run probes manually or via Garak CLI |
| **tdd-enforcer** | `tdd-enforcer/skill.yaml` | TDD guidance and validation checklist | ⚠️ Depends on `git_diff_files` tool |

## Format

All skills use `.yaml` (not `.md`) because Cline skills require structured YAML with defined `inputs`, `steps`, `outputs`, and `templates`. Markdown is suitable for documentation but not for executable skill definitions.

## Pre-commit Python Issue

Local `git commit` may fail with:
```
No Python at 'C:\Users\ayode\AppData\Local\Programs\Python\Python312\python.exe'
```

The project venv exists at `C:\Users\ayode\.virtualenvs\fitness_assistant-cy4ooJtL\Scripts\python.exe`, but pre-commit looks for a system Python that isn't installed.

**Workaround:** Use `git commit --no-verify` to bypass pre-commit hooks locally, or activate the venv before committing:

```cmd
"C:\Users\ayode\.virtualenvs\fitness_assistant-cy4ooJtL\Scripts\activate.bat"
git commit -m "your message"
```

## CI/CD

GitHub Actions workflows handle CI/CD instead of local pre-push hooks:
- `.github/workflows/pull-request-check.yaml` — Pre-commit + unit tests on PR
- `.github/workflows/keep-apps-awake.yml` — Streamlit app keep-alive
- `.github/workflows/keep-repo-active.yml` — Repository heartbeat
