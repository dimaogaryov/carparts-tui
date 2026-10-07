"""Проверяет минимальную версию macOS у Mach-O файлов (бинарник, libpython, модули).

    python packaging/check_macos_min.py 12.0 dist/carparts <python prefix> ...

Падает, если хоть один файл требует macOS новее заданной: так сборка гарантированно
запускается на Monterey (12) и Intel-маках.
"""
import os
import re
import subprocess
import sys

MACHO_MAGIC = {b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe"}


def is_macho(path: str) -> bool:
    try:
        with open(path, "rb") as f:
            return f.read(4) in MACHO_MAGIC
    except OSError:
        return False


def parse_min_versions(otool_output: str) -> list[tuple[int, ...]]:
    """minos из LC_BUILD_VERSION (платформа macOS) и version из LC_VERSION_MIN_MACOSX."""
    found = []
    for block in otool_output.split("Load command")[1:]:
        if "cmd LC_BUILD_VERSION" in block:
            platform = re.search(r"platform\s+(\w+)", block)
            m = re.search(r"minos\s+(\d+(?:\.\d+)*)", block)
            if m and platform and platform.group(1) in ("1", "MACOS"):
                found.append(m.group(1))
        elif "cmd LC_VERSION_MIN_MACOSX" in block:
            m = re.search(r"\bversion\s+(\d+(?:\.\d+)*)", block)
            if m:
                found.append(m.group(1))
    return [tuple(map(int, v.split("."))) for v in found]


def min_versions(path: str) -> list[tuple[int, ...]]:
    out = subprocess.run(["otool", "-l", path], capture_output=True, text=True).stdout
    return parse_min_versions(out)


def walk(paths):
    for p in paths:
        if os.path.isfile(p):
            yield p
        for root, _, files in os.walk(p):
            for name in files:
                yield os.path.join(root, name)


def main() -> int:
    limit = tuple(map(int, sys.argv[1].split(".")))
    worst, checked, bad = (0,), 0, []
    for path in walk(sys.argv[2:]):
        if os.path.islink(path) or not is_macho(path):
            continue
        for v in min_versions(path):
            checked += 1
            worst = max(worst, v)
            if v > limit:
                bad.append((path, v))
    print(f"checked {checked} Mach-O load commands, highest minimum macOS: "
          f"{'.'.join(map(str, worst))}")
    for path, v in bad:
        print(f"TOO NEW ({'.'.join(map(str, v))}): {path}")
    return 1 if bad or not checked else 0


if __name__ == "__main__":
    sys.exit(main())
