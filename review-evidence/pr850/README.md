# PR850: compiled exit-status validation

LATTICE-ETA / ChatGPT test-only contribution, 2026-09-07 UTC (September 6 in America/Chicago). The existing implementation/report remains C's work in [Tarsnap/tarsnap PR850](https://github.com/Tarsnap/tarsnap/pull/850), addressing issue849. This review did not modify that PR's source branch or open another upstream claim.

## Result

**24/24 expected process outcomes matched across two separately compiled, exact revisions.** This includes the negative control: the original program incorrectly returns success on the injected allocation failure. The candidate correctly returns failure. Twenty ordinary/control executions remain unchanged.

| Case | Base actual exit | Candidate actual exit | All case assertions |
| --- | ---: | ---: | --- |
| Version, no instrumentation | 0 | 0 | PASS |
| Version, interposer disabled | 0 | 0 | PASS |
| Version, fault armed but unrelated argument | 0 | 0 | PASS |
| Missing options | 1 | 1 | PASS |
| Missing keylist argument | 1 | 1 | PASS |
| Invalid key number 32 | 1 | 1 | PASS |
| Nonnumeric key | 1 | 1 | PASS |
| Marker argument without instrumentation | 1 | 1 | PASS |
| Marker argument, interposer disabled | 1 | 1 | PASS |
| Valid keylist followed by version | 0 | 0 | PASS |
| Keylist allocation failure | **0 (original defect)** | **1 (fixed)** | PASS |
| Allocation failure followed by version option | **0 (original defect)** | **1 (fixed)** | PASS |

For each of the four injected executions, captured stdout was empty and stderr was exactly:

```text
LATTICE_ETA_INJECTED_ENOMEM
tarsnap-keymgmt: Out of memory
```

Each case also checked the expected diagnostic, exact injection count, empty stdout, and absence of created files. The two fault cases per revision checked that invalid-argument handling did not run and later version processing did not execute. All assertions passed. The original exit0 is deliberately expected by the negative-control test; it is not a claim that the original behavior is correct.

## Exact provenance

- Base: `0bf0b299fed91139044c81cc6fcdc5521c34d235`
- Candidate: `f432ef4348360d0d2ff9546c8ebe255ab715251a`
- Candidate source blob, `keymgmt/keymgmt.c`: `d2b930c685d972591297e5a4eb963cfb505f76dd`
- Base source blob: `798840083b47acd435ece991bf0355665cf86f62`
- Successful harness/workflow commit: `5bcc9706245e3f8770be091dc825d58d3ef969a6`
- [Successful Actions run 34074276961](https://github.com/woahwhattheheck/tarsnap/actions/runs/34074276961), job101597269329, completed 2026-09-07T01:51:15Z.
- Artifact: `lattice-eta-pr850-exit-status`, ID `10001520958`, 29326 bytes, retention through 2026-10-07T01:51:13Z.
- Downloaded ZIP SHA256: `c79d803fec6ed6b6718dd0940ed6000ef9aeeaca9deac8810e06e4b26ab4470d` (matched GitHub's artifact digest).
- Raw `results.json` SHA256: `c3b94ac9f2f05bcd0564812e1d143d19aaf5c5fc9817b3e37e8af5e171a42bf3`.
- Base executable SHA256: `de22535b414556d1a0f4c30150f0d5a15b0bbcd8fab52ab20b277f07fbd097dd`.
- Candidate executable SHA256: `e098e0f648f923977b504a57a223d30cb8099ac5c1cc89beded1f94241496de3`.
- Environment: Ubuntu22.04 runner, Linux6.8.0-1064-azure x86_64, glibc2.35, GCC11.4.0, Python3.10.12.

The runner verifies the exact parent relationship, one changed source path, byte-exact one-character exit0-to-exit1 replacement, candidate Git blob, and absence of a build-time change to that source. Both revisions are built in detached worktrees, without patching production source for the test.

## Replay

Clone this fork normally and check out the successful harness commit above. With the dependencies from `BUILDING` installed:

```sh
python3 review-tests/keymgmt_exit_status.py --output /tmp/pr850-fresh-evidence
```

Use a nonexistent output directory. The runner executes, separately for each exact revision:

```sh
autoreconf -i
./configure
make -j2 apisupport-config.h cpusupport-config.h
make -j2 tarsnap-keymgmt
```

The replay source is [review-tests/keymgmt_exit_status.py](../../review-tests/keymgmt_exit_status.py). The artifact includes raw JSON with every process result and check, both full build logs, the instrumentation build log, and the replay/interposer sources and interposer binary.

## Scope and limits

Failure injection is Linux `LD_PRELOAD` instrumentation limited to `strdup()` of a unique synthetic `--keylist` argument with an explicit enabling environment variable. Other duplication calls delegate to the original function. No input key files, account credentials, production data, or service operation are used. This is deterministic CLI error-propagation validation, not natural memory-pressure testing, a security exploit, cross-platform certification, or a full Tarsnap test-suite run.

The first review run34074014025 failed before any application case because the standalone executable target did not generate Automake `BUILT_SOURCES` automatically. The replay harness was corrected to build the two generated headers explicitly. That failed run is retained as provenance, not counted as an application result. The successful run above was then inspected directly; no already-passed test was rerun.

No maintainer acceptance, merge, bounty amount, or payment is asserted by this evidence.
