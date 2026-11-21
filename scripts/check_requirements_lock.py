"""Compare pip-compile locks without depending on generator annotations."""

import re
import sys
from difflib import unified_diff
from pathlib import Path


def normalize_lock(path: Path) -> list[str]:
    lines = re.sub(r"[ \t]*\\\n[ \t]*", " ", path.read_text(encoding="utf-8"))
    normalized = []
    for line in lines.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # pip-compile resolves the extras either way; --strip-extras
            # changes their spelling on the pin, not its resolved dependencies.
            line = re.sub(r"^([\w.-]+)\[[\w., -]+\](?===)", r"\1", line)
            normalized.append(line + "\n")
    return normalized


if __name__ == "__main__":
    checked, compiled = map(Path, sys.argv[1:])
    diff = list(unified_diff(
        normalize_lock(checked), normalize_lock(compiled),
        fromfile=str(checked), tofile="regenerated lockfile",
    ))
    if diff:
        sys.stderr.writelines(diff)
        sys.exit("Python lockfile disagrees with requirements.in; run make requirements-lock.")
