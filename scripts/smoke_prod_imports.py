"""Import smoke test for the production-only dependency set.

Run with ONLY the packages from ``[project] dependencies`` installed.
Exits 1 if any runtime import is missing — this is the guard against
runtime dependencies accidentally living in the dev extra.
"""

import os
import sys
import tempfile


def main() -> int:
    # Keep any composition-root side effects (upload dirs, databases)
    # out of the caller's working directory.
    os.chdir(tempfile.mkdtemp(prefix="psf-smoke-"))

    failures: list[str] = []
    for module in ("psf_reasoner.cli", "psf_reasoner.bootstrap", "psf_reasoner.api.app"):
        try:
            __import__(module)
        except Exception as exc:  # report every import problem, then exit
            failures.append(f"{module}: {type(exc).__name__}: {exc}")

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1

    from psf_reasoner.api.app import create_app
    from psf_reasoner.bootstrap import create_default_runner
    from psf_reasoner.cli import app as cli_app

    # Default composition roots must build and the app must be creatable.
    create_app(create_default_runner())
    assert cli_app is not None
    print("prod import smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
