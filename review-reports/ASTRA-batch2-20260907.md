# ASTRA-TEN: second batch delivery, September 7, 2026

Eleven existing Tarsnap PRs now contain published regression additions. Original C/Claude reports and production fixes remain credited. These are not eleven new bounty discoveries or new PRs. No upstream merge, award or payment is asserted.

## Published revisions

| PR | Exact head | Standalone script under tests/unit | Coverage |
|---|---|---|---|
| [840](https://github.com/Tarsnap/tarsnap/pull/840) | f0c72eb20a3b435ff347a46a6574c74e07c4f18d | fsck-metaindex.sh | 36 scenarios |
| [842](https://github.com/Tarsnap/tarsnap/pull/842) | 9e0191afebf32d1a47b263c8f39fdc990cfea7b1 | chunks-fsck.sh | 35 scenarios |
| [844](https://github.com/Tarsnap/tarsnap/pull/844) | 5638f94c353500e57ecfaa2d948d54fb19d33be0 | list-archives.sh | 16 scenarios |
| [846](https://github.com/Tarsnap/tarsnap/pull/846) | c630a4ca4e3c659d2b67999a17288a30f5cba83b | storage-directory.sh | 20 scenarios |
| [848](https://github.com/Tarsnap/tarsnap/pull/848) | 23ea42df198c74a979e1b24cce6d7dd7ab482805 | storage-commit.sh | 36 scenarios |
| [852](https://github.com/Tarsnap/tarsnap/pull/852) | 82e169b31a7443e95edac481bc6826c6618b4cf5 | chunks-directory.sh | 27 real-file scenarios |
| [854](https://github.com/Tarsnap/tarsnap/pull/854) | d705e605a1253a8f8c5bba5683586c888dcc22f0 | recrypt-durability.sh | 45 scenarios |
| [856](https://github.com/Tarsnap/tarsnap/pull/856) | 4158097161607f5e99e7fcb83f025eb206954ed3 | network-writeq.sh | 60 scenarios |
| [858](https://github.com/Tarsnap/tarsnap/pull/858) | 606758a62e6588e5679a05b348c82fb04dab4a80 | network-timeout.sh | 34 socketpair scenarios |
| [860](https://github.com/Tarsnap/tarsnap/pull/860) | 2dc28d0df423985dc31e0b0c01096306d7470b3b | sigquit.sh | Type guard and 64 SIGQUIT deliveries |
| [862](https://github.com/Tarsnap/tarsnap/pull/862) | 1bc8e0b53e823280db53dae2f3c110c3fc8cbd15 | patricia.sh | 261 keys and 34,191 prefix lookups |

Base: `0bf0b299fed91139044c81cc6fcdc5521c34d235`.

## Execution evidence

All eleven standalone suites pass on the exact published heads in isolated Linux/GCC14.2 and again on clean Ubuntu/GCC13.3. All eleven local controls with the same new tests but pre-fix production sources fail. For PR860, the distinguishing control is a compile-time volatile-type guard, not an observed production optimizer failure.

[Successful clean-runner verification](https://github.com/woahwhattheheck/tarsnap/actions/runs/34089849644), carrier `9f1ea08a4846431ee05a9a9226b6a4c935972554`.

[Evidence artifact 10006458005](https://github.com/woahwhattheheck/tarsnap/actions/runs/34089849644/artifacts/10006458005), SHA-256 `04ed3e3ac335a5e3e11f888235345cc4cbd56162b5b4ed7b9e4b7dfe03f54e97`.

Downloaded archive digest, component digests, eleven successful runner exit codes, six build/smoke exit codes and exact published test blob manifests were independently verified locally. This artifact expires September 21, 2026; the test source and this report remain on GitHub.

One combined composition of the eleven production patches (twelve source files) builds successfully. All five binaries pass version-only smoke checks: tarsnap, tarsnap-keygen, tarsnap-keymgmt, tarsnap-keyregen and tarsnap-recrypt. This is one combined native build, not eleven independent full builds or a live-server integration test.

The first clean-runner attempt stopped before tests because the ext2 development header was missing. The isolated verification workflow was corrected to install the normal native prerequisites and explicitly fetch the comparison base. No contribution branch or acceptance check was weakened.

## Replay and limits

On Ubuntu install libext2fs-dev, libbz2-dev, zlib1g-dev, libssl-dev, a C compiler, make, autoconf and automake. Python3 is needed by the recrypt harness. At a published revision:

```sh
autoreconf -i
./configure --without-lzma
sh tests/unit/patricia.sh .
```

Substitute that PR's script from the table. Tests use synthetic local fixtures; transport and allocation failures are explicitly injected. PR854 tests extracted source ordering and injected file-operation failures, not physical power-loss recovery. PR860 sends real SIGQUIT to its own process. PR862 uses UBSan. No real account, key material, hosted storage, network transaction or payment operation is involved.

## Publication state and credit

The eleven upstream PRs remain open and their existing branches contain the tests. CI carrier/evidence branches are not for master integration. An attempted validation comment on upstream PR862 returned HTTP403 from the GitHub integration; no comment was published. Older PR descriptions can therefore still say builds were not run. No alternate credential route was used.

[Canonical work and ownership thread](https://tokenjunkielabs.slack.com/archives/C0BVANHNB26/p1788757411895699).

LLM disclosure: ChatGPT/ASTRA-TEN prepared regression additions and validation for the same account owner. Discussion and revisions are available through active conversations; continuous autonomous monitoring is not asserted. C's original reporter/implementation credit, existing submission ownership and sponsor terms are unchanged.
