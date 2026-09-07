#!/usr/bin/env python3
"""Reproduce Tarsnap #849 / validate PR #850 using two real compiled revisions.

Run inside a full Git clone with the documented build dependencies installed:
    python3 review-tests/keymgmt_exit_status.py --output /tmp/keymgmt-evidence

The only induced failure is strdup() of a unique, synthetic --keylist argument.
No key files, account credentials, network service, or production data are used.
The production sources are never patched; each revision gets a detached worktree.
Linux/glibc LD_PRELOAD is test instrumentation, not a portability claim.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

BASE = "0bf0b299fed91139044c81cc6fcdc5521c34d235"
HEAD = "f432ef4348360d0d2ff9546c8ebe255ab715251a"
HEAD_BLOB = "d2b930c685d972591297e5a4eb963cfb505f76dd"
MARKER = "LATTICE_ETA_KEYLIST_FAULT_850"
INJECTED = "LATTICE_ETA_INJECTED_ENOMEM"
SOURCE = "keymgmt/keymgmt.c"

INTERPOSER = r'''#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

char *strdup(const char *s)
{
    static char *(*original)(const char *);
    const char *enabled = getenv("LATTICE_ETA_FAIL_STRDUP");
    if (enabled != NULL && strcmp(enabled, "1") == 0 &&
        strcmp(s, "LATTICE_ETA_KEYLIST_FAULT_850") == 0) {
        static const char message[] = "LATTICE_ETA_INJECTED_ENOMEM\n";
        ssize_t ignored = write(STDERR_FILENO, message, sizeof(message) - 1);
        (void)ignored;
        errno = ENOMEM;
        return NULL;
    }
    if (original == NULL) {
        original = (char *(*)(const char *))dlsym(RTLD_NEXT, "strdup");
        if (original == NULL)
            _exit(98);
    }
    return original(s);
}
'''


@dataclass(frozen=True)
class Case:
    name: str
    arguments: tuple[str, ...]
    exit_code: int
    diagnostic: str
    preload: bool = False
    inject: bool = False
    fault: bool = False


def cases(expected_fault_exit: int) -> tuple[Case, ...]:
    return (
        Case("version_uninstrumented", ("--version",), 0, "tarsnap-keymgmt "),
        Case("version_interposer_disabled", ("--version",), 0, "tarsnap-keymgmt ", True),
        Case("version_fault_armed_but_unrelated", ("--version",), 0, "tarsnap-keymgmt ", True, True),
        Case("missing_options", (), 1, "usage:"),
        Case("missing_keylist_argument", ("--keylist",), 1, "Missing argument"),
        Case("invalid_key_number", ("--keylist", "32"), 1, "Not a valid key number", True, True),
        Case("nonnumeric_key", ("--keylist", "not_a_key"), 1, "Not a valid key number", True, True),
        Case("marker_without_instrumentation", ("--keylist", MARKER), 1, "Not a valid key number"),
        Case("marker_interposer_disabled", ("--keylist", MARKER), 1, "Not a valid key number", True),
        Case("valid_keylist_then_version", ("--keylist", "0,1", "--version"), 0, "tarsnap-keymgmt ", True, True),
        Case("keylist_allocation_failure", ("--keylist", MARKER), expected_fault_exit, "Out of memory", True, True, True),
        Case("allocation_failure_stops_argument_processing", ("--keylist", MARKER, "--version"), expected_fault_exit, "Out of memory", True, True, True),
    )


def command(argv: Sequence[str], *, cwd: Path, log: Path, timeout: int = 600) -> None:
    with log.open("a", encoding="utf-8") as stream:
        stream.write("\nCOMMAND " + json.dumps(list(argv)) + "\n")
        stream.flush()
        result = subprocess.run(list(argv), cwd=cwd, stdout=stream, stderr=subprocess.STDOUT,
                                timeout=timeout, check=False)
        stream.write(f"EXIT {result.returncode}\n")
    if result.returncode:
        tail = log.read_text(encoding="utf-8", errors="replace")[-12000:]
        raise RuntimeError(f"Command failed ({result.returncode}): {argv!r}\n{tail}")


def git(repo: Path, *arguments: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *arguments], text=True).strip()


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def verify_revisions(repo: Path) -> dict[str, str]:
    if git(repo, "rev-parse", f"{HEAD}^") != BASE:
        raise RuntimeError("Candidate is not a direct child of the recorded base")
    if git(repo, "diff", "--name-only", BASE, HEAD) != SOURCE:
        raise RuntimeError("Candidate diff includes a different source scope")
    before = subprocess.check_output(["git", "-C", str(repo), "show", f"{BASE}:{SOURCE}"])
    after = subprocess.check_output(["git", "-C", str(repo), "show", f"{HEAD}:{SOURCE}"])
    old = b'warn0("Out of memory");\n\t\t\t\texit(0);'
    new = b'warn0("Out of memory");\n\t\t\t\texit(1);'
    if before.count(old) != 1 or before.replace(old, new, 1) != after:
        raise RuntimeError("Expected exact one-character production change was not found")
    if git(repo, "rev-parse", f"{HEAD}:{SOURCE}") != HEAD_BLOB:
        raise RuntimeError("Candidate source blob does not match the reviewed source")
    return {"base": BASE, "candidate": HEAD,
            "base_source_blob": git(repo, "rev-parse", f"{BASE}:{SOURCE}"),
            "candidate_source_blob": HEAD_BLOB,
            "base_source_sha256": hashlib.sha256(before).hexdigest(),
            "candidate_source_sha256": hashlib.sha256(after).hexdigest()}


def exercise(binary: Path, library: Path, case: Case, cwd: Path) -> dict[str, object]:
    environment = os.environ.copy()
    environment.pop("LD_PRELOAD", None)
    environment.pop("LATTICE_ETA_FAIL_STRDUP", None)
    environment["LC_ALL"] = "C"
    if case.preload:
        environment["LD_PRELOAD"] = str(library)
    if case.inject:
        environment["LATTICE_ETA_FAIL_STRDUP"] = "1"
    outcome = subprocess.run([str(binary), *case.arguments], cwd=cwd, env=environment,
                             capture_output=True, text=True, timeout=10, check=False)
    files = sorted(str(p.relative_to(cwd)) for p in cwd.rglob("*"))
    checks = {
        "expected_exit": outcome.returncode == case.exit_code,
        "expected_diagnostic": case.diagnostic in outcome.stderr,
        "empty_stdout": outcome.stdout == "",
        "exact_injection_count": outcome.stderr.count(INJECTED) == int(case.fault),
        "no_files_created": not files,
    }
    if case.fault:
        checks["not_argument_validation"] = "Not a valid key number" not in outcome.stderr
        checks["out_of_memory_once"] = outcome.stderr.count("Out of memory") == 1
        checks["no_later_version_output"] = len(outcome.stderr.splitlines()) == 2
    return {"name": case.name, "arguments": list(case.arguments),
            "expected_exit": case.exit_code, "exit": outcome.returncode,
            "preload": case.preload, "inject": case.inject,
            "stdout": outcome.stdout, "stderr": outcome.stderr,
            "created_files": files, "checks": checks, "pass": all(checks.values())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    repo = arguments.repository.resolve()
    output = arguments.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report: dict[str, object] = {"scope": "Tarsnap #849 / PR850 ordinary CLI exit-status regression",
                              "platform": platform.platform(), "python": sys.version,
                              "working_checkout": git(repo, "rev-parse", "HEAD"),
                              "revisions": [], "complete": False}
    report_file = output / "results.json"
    status = 1
    worktrees: list[Path] = []
    try:
        if platform.system() != "Linux":
            raise RuntimeError("This instrumentation requires Linux LD_PRELOAD")
        report["source_verification"] = verify_revisions(repo)
        cc = os.environ.get("CC", "cc")
        report["compiler"] = subprocess.check_output([cc, "--version"], text=True)
        report["libc"] = list(platform.libc_ver())
        (output / "strdup_fault.c").write_text(INTERPOSER, encoding="utf-8")
        library = output / "strdup_fault.so"
        command([cc, "-std=c99", "-Wall", "-Wextra", "-Werror", "-shared", "-fPIC",
                 str(output / "strdup_fault.c"), "-ldl", "-o", str(library)],
                cwd=repo, log=output / "instrumentation-build.log")
        report["instrumentation_sha256"] = digest(library)
        with tempfile.TemporaryDirectory(prefix="lattice-eta-850-") as temporary:
            temporary_root = Path(temporary)
            for label, revision, fault_exit in (("base", BASE, 0), ("candidate", HEAD, 1)):
                source = temporary_root / label
                log = output / f"{label}-build.log"
                command(["git", "worktree", "add", "--detach", str(source), revision], cwd=repo, log=log)
                worktrees.append(source)
                command(["autoreconf", "-i"], cwd=source, log=log)
                command(["./configure"], cwd=source, log=log)
                command(["make", "-j2", "tarsnap-keymgmt"], cwd=source, log=log)
                binary = source / "tarsnap-keymgmt"
                if git(source, "diff", "--", SOURCE):
                    raise RuntimeError("Build changed the reviewed production source")
                results = []
                for case in cases(fault_exit):
                    case_directory = temporary_root / f"{label}-{case.name}"
                    case_directory.mkdir()
                    result = exercise(binary, library, case, case_directory)
                    results.append(result)
                    print(f"{label} {case.name}: exit={result['exit']} expected={case.exit_code} "
                          f"{'PASS' if result['pass'] else 'FAIL'}", flush=True)
                report["revisions"].append({"label": label, "commit": revision,
                                            "source_blob": git(source, "hash-object", SOURCE),
                                            "binary_sha256": digest(binary), "cases": results})
                report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
            all_cases = [c for revision in report["revisions"] for c in revision["cases"]]
            report["total_cases"] = len(all_cases)
            report["passed_cases"] = sum(bool(c["pass"]) for c in all_cases)
            report["complete"] = True
            report["pass"] = bool(all_cases) and all(c["pass"] for c in all_cases)
            status = 0 if report["pass"] else 1
    except (OSError, subprocess.SubprocessError, RuntimeError) as error:
        report["error"] = str(error)
        report["pass"] = False
        print(str(error), file=sys.stderr)
    finally:
        for worktree in worktrees:
            subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(worktree)],
                           capture_output=True, check=False)
        subprocess.run(["git", "-C", str(repo), "worktree", "prune"], capture_output=True, check=False)
        report_file.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        shutil.copyfile(Path(__file__), output / "keymgmt_exit_status.py")
        print(json.dumps({"complete": report["complete"], "pass": report.get("pass", False),
                          "cases": report.get("total_cases", 0)}, sort_keys=True), flush=True)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
