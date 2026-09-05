from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def git(*args: str, capture: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
        check=False,
    )
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "git command failed").strip()
        raise RuntimeError(detail)
    return (result.stdout or "").strip()


def main() -> int:
    branch = git("branch", "--show-current")
    if branch != "main":
        raise RuntimeError(f"sync recusado: branch atual é {branch!r}, esperado 'main'")

    dirty = git("status", "--porcelain")
    if dirty:
        raise RuntimeError(
            "sync recusado: existem mudanças locais. Faça commit/stash antes de atualizar."
        )

    git("fetch", "origin", "main", capture=False)
    local = git("rev-parse", "HEAD")
    remote = git("rev-parse", "origin/main")

    if local == remote:
        print(f"ICDASQuiz já está atualizado: {local[:12]}")
        return 0

    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", local, remote],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0:
        git("merge", "--ff-only", "origin/main", capture=False)
        print(f"ICDASQuiz atualizado: {local[:12]} -> {remote[:12]}")
        return 0

    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", remote, local],
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    ).returncode == 0:
        raise RuntimeError(
            f"sync recusado: esta cópia possui commit(s) locais não publicados ({local[:12]})."
        )

    raise RuntimeError(
        "sync recusado: histórico local e origin/main divergiram; faça reconciliação manual."
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ERRO: {exc}")
        raise SystemExit(2)
