#!/usr/bin/env python3
"""Compile the actual padme helper and compare it with an integer oracle.

This is helper-level validation for Tarsnap issue 835 / PR 836, not a claim
that the shipped client's small MAXCHUNK reaches the large-length boundary.
No chunk buffers, Tarsnap account, server, or network access are needed.

Example (from a checkout containing the original revision):
  python3 review-tests/padme_shift_replay.py \
      --baseline-ref 0bf0b299fed91139044c81cc6fcdc5521c34d235 \
      --output-dir /tmp/padme-evidence

The candidate helper is extracted byte-for-byte from tar/chunks/chunks_write.c.
The baseline is read from Git or an explicitly supplied source file. It is
never reconstructed by silently changing the candidate. GCC and Clang, when
available, are each exercised at -O0 and -O2 with undefined-behavior sanitizing.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import random
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path("tar/chunks/chunks_write.c")
SIGNATURE = re.compile(
    r"^static size_t\npadme\(size_t len, size_t maxlen\)\n\{\n", re.MULTILINE
)
HEADERS = """#include <assert.h>
#include <limits.h>
#include <stddef.h>
#include <stdint.h>
#include <stdio.h>
"""
DRIVER = r'''
int
main(int argc, char ** argv)
{
    size_t len, maxlen;
    int n;

    (void)argv;
    if (argc > 1) {
        printf("%zu %zu %zu\n", (size_t)SIZE_MAX,
            sizeof(size_t) * CHAR_BIT, sizeof(int) * CHAR_BIT);
        return (0);
    }
    for (;;) {
        n = scanf("%zu %zu", &len, &maxlen);
        if (n == EOF)
            return (ferror(stdin) ? 65 : 0);
        if ((n != 2) || (len == 0) || (len > maxlen))
            return (64);
        printf("%zu\n", padme(len, maxlen));
    }
}
'''


def extract_helper(data: bytes) -> bytes:
    """Select the one exact current helper, rejecting a missing/ambiguous match."""
    text = data.decode("utf-8")
    matches = list(SIGNATURE.finditer(text))
    if len(matches) != 1:
        raise ValueError(f"expected one padme definition, found {len(matches)}")
    start = matches[0].start()
    end = text.find("\n}\n", matches[0].end())
    if end < 0:
        raise ValueError("padme's top-level closing brace was not found")
    return text[start:end + 3].encode("utf-8")


def source_identity(data: bytes) -> dict[str, Any]:
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "git_blob_sha1": hashlib.sha1(
            b"blob " + str(len(data)).encode("ascii") + b"\0" + data
        ).hexdigest(),
        "helper_sha256": hashlib.sha256(extract_helper(data)).hexdigest(),
    }


def oracle(length: int, maximum: int) -> int:
    """Use bit lengths and integer ceiling division, rather than a C bit mask."""
    if length <= 8:
        return 0
    exponent = length.bit_length() - 1
    quantum = 2 ** (exponent - exponent.bit_length())
    rounded = ((length + quantum - 1) // quantum) * quantum
    return min(rounded, maximum) - length


def make_cases(size_max: int, size_bits: int) -> list[tuple[int, int]]:
    # The actual chunks_write_start() accepts maxchunksize <= SIZE_MAX / 2
    # and supplies zbuflen = maxchunksize + maxchunksize / 1000 + 13.
    max_chunk = size_max // 2
    max_buffer = max_chunk + max_chunk // 1000 + 13
    lengths = set(range(1, 513))
    for exponent in range(3, size_bits):
        power = 2 ** exponent
        quantum = 2 ** (exponent - exponent.bit_length())
        for delta in (-2, -1, 0, 1, 2, quantum - 1, quantum, quantum + 1):
            value = power + delta
            if 0 < value <= max_buffer:
                lengths.add(value)
    for delta in range(16):
        lengths.add(max_buffer - delta)
        lengths.add(max_chunk - delta)
    rng = random.Random(835)
    lengths.update(rng.randrange(1, max_buffer + 1) for _ in range(4096))
    cases: set[tuple[int, int]] = set()
    for length in lengths:
        exponent = length.bit_length() - 1
        quantum = 1 if length <= 8 else 2 ** (exponent - exponent.bit_length())
        for maximum in (
            length, min(max_buffer, length + 1),
            min(max_buffer, length + quantum - 1), max_buffer,
        ):
            if length <= maximum <= size_max:
                cases.add((length, maximum))
    return sorted(cases)


def run(command: list[str], *, data: str = "", timeout: int = 60) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["UBSAN_OPTIONS"] = "halt_on_error=1:print_stacktrace=0"
    return subprocess.run(
        command, input=data, text=True, capture_output=True, timeout=timeout,
        check=False, env=env,
    )


def retain(out: Path, label: str, result: subprocess.CompletedProcess[str]) -> None:
    (out / f"{label}.stdout.txt").write_text(result.stdout, encoding="utf-8")
    (out / f"{label}.stderr.txt").write_text(result.stderr, encoding="utf-8")


def verify_values(binary: Path, cases: list[tuple[int, int]], out: Path, label: str) -> int:
    data = "".join(f"{length} {maximum}\n" for length, maximum in cases)
    result = run([str(binary)], data=data)
    retain(out, label, result)
    if result.returncode != 0 or "runtime error:" in result.stderr:
        raise ValueError(f"{label}: native execution failed; see retained stderr")
    lines = result.stdout.splitlines()
    if len(lines) != len(cases):
        raise ValueError(f"{label}: got {len(lines)} results for {len(cases)} inputs")
    for number, ((length, maximum), line) in enumerate(zip(cases, lines)):
        expected = oracle(length, maximum)
        if not line.isdecimal() or int(line) != expected:
            raise ValueError(
                f"{label}: case {number}, len={length}, max={maximum}: "
                f"got {line!r}, expected {expected}"
            )
    return len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=ROOT / SOURCE)
    baseline = parser.add_mutually_exclusive_group()
    baseline.add_argument("--baseline-ref")
    baseline.add_argument("--baseline-source", type=Path)
    parser.add_argument("--cc", action="append", help="compiler executable; repeat to select a matrix")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "scope": "pure padme helper; no chunk allocation or full-client execution",
        "seed": 835, "python_version": sys.version.split()[0],
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "status": "failed", "configurations": [],
        "baseline_controls": "not requested",
    }
    try:
        candidate = args.source.read_bytes()
        report["candidate"] = source_identity(candidate)
        original: bytes | None = None
        if args.baseline_source:
            original = args.baseline_source.read_bytes()
            report["baseline_origin"] = "explicit source file"
        elif args.baseline_ref:
            if not re.fullmatch(r"[0-9a-fA-F]{40}", args.baseline_ref):
                raise ValueError("--baseline-ref must be a full 40-character commit ID")
            result = subprocess.run(
                ["git", "show", f"{args.baseline_ref}:{SOURCE.as_posix()}"],
                cwd=ROOT, capture_output=True, check=True, timeout=30,
            )
            original = result.stdout
            report["baseline_origin"] = {"git_ref": args.baseline_ref, "path": SOURCE.as_posix()}
        if original is not None:
            report["baseline"] = source_identity(original)
            report["baseline_controls"] = "requested"
        compilers = args.cc or [name for name in ("gcc", "clang") if shutil.which(name)]
        if not compilers:
            raise ValueError("no GCC or Clang found; supply --cc")
        names = set()
        for index, compiler in enumerate(compilers):
            path = shutil.which(compiler)
            if not path:
                raise ValueError(f"compiler is unavailable: {compiler}")
            tag = f"cc{index}-{Path(path).name}"
            if path in names:
                raise ValueError(f"duplicate compiler: {path}")
            names.add(path)
            version = run([path, "--version"])
            if version.returncode != 0:
                raise ValueError(f"could not read compiler version: {path}")
            for optimization in ("0", "2"):
                label = f"{tag}-O{optimization}"
                record: dict[str, Any] = {
                    "compiler": path, "version": version.stdout.splitlines()[0],
                    "optimization": f"-O{optimization}", "status": "failed",
                }
                report["configurations"].append(record)
                with tempfile.TemporaryDirectory(prefix="padme-native-") as temp_name:
                    temp = Path(temp_name)
                    binaries = {}
                    for kind, data in (("candidate", candidate), ("baseline", original)):
                        if data is None:
                            continue
                        c_text = HEADERS + extract_helper(data).decode("utf-8") + DRIVER
                        source = temp / f"{kind}.c"
                        source.write_text(c_text, encoding="utf-8")
                        (out / f"{kind}.c").write_text(c_text, encoding="utf-8")
                        binary = temp / kind
                        command = [
                            path, "-std=c99", f"-O{optimization}", "-Wall", "-Wextra",
                            "-Werror", "-pedantic", "-fsanitize=undefined",
                            "-fno-sanitize-recover=undefined", str(source), "-o", str(binary),
                        ]
                        built = run(command)
                        retain(out, f"{label}-{kind}-compile", built)
                        if built.returncode != 0:
                            raise ValueError(f"{label}: {kind} did not compile")
                        binaries[kind] = binary
                    limits = run([str(binaries["candidate"]), "--limits"])
                    if limits.returncode != 0:
                        raise ValueError(f"{label}: could not read integer widths")
                    size_max, size_bits, int_bits = map(int, limits.stdout.split())
                    if size_max != 2 ** size_bits - 1:
                        raise ValueError("this replay expects ordinary unsigned size_t without padding bits")
                    cases = make_cases(size_max, size_bits)
                    (out / f"inputs-size{size_bits}.tsv").write_text(
                        "".join(f"{a}\t{b}\t{oracle(a, b)}\n" for a, b in cases), encoding="utf-8"
                    )
                    record.update({"size_t_bits": size_bits, "int_bits": int_bits,
                                   "candidate_cases": verify_values(
                                       binaries["candidate"], cases, out, f"{label}-candidate")})
                    if original is not None:
                        thresholds = []
                        for shift in (int_bits - 1, int_bits):
                            exponents = [e for e in range(3, size_bits) if e - e.bit_length() == shift]
                            if not exponents:
                                raise ValueError("wide baseline controls require size_t wider than int")
                            thresholds.append(2 ** min(exponents))
                        safe = [case for case in cases if case[0] < thresholds[0]]
                        record["baseline_safe_cases"] = verify_values(
                            binaries["baseline"], safe, out, f"{label}-baseline-safe"
                        )
                        controls = []
                        for name, length in zip(("sign-bit", "shift-width"), thresholds):
                            result = run([str(binaries["baseline"])], data=f"{length} {length}\n")
                            retain(out, f"{label}-baseline-{name}", result)
                            if (result.returncode == 0 or "runtime error:" not in result.stderr
                                    or "shift" not in result.stderr.lower()):
                                raise ValueError(f"{label}: {name} did not reproduce a UBSan shift error")
                            controls.append({"case": name, "length": length,
                                             "returncode": result.returncode,
                                             "diagnostic": result.stderr.strip()})
                        record["baseline_undefined_shift_controls"] = controls
                    record["status"] = "passed"
        if original is not None:
            report["baseline_controls"] = "passed"
        report["candidate_evaluations"] = sum(
            item["candidate_cases"] for item in report["configurations"]
        )
        report["status"] = "passed"
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError) as exc:
        report["error"] = str(exc)
    report_path = out / "report.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
