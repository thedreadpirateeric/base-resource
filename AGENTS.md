# base-resource

Public, MIT-licensed Python library. Package name `baseresourcelib`. It is a generalized resource framework: one metaclass, modes (`api`, `rpc`, `db`, `direct`), shims, Marshmallow schemas, and MongoEngine documents. Task submission, the RPC mode, and task polling are part of that framework. It is not a product client, a Flask application, or a Celery broker.

This file is the working guide for people and coding assistants. `docs/modernization-assessment.md` is the inventory and the planned sequence. Both are evidence of what was true when they were written. The source and the tests are the behavior.

## How to work in this repository

Investigate the code that a change will touch before describing it. Read the function, its callers in this repo, and the tests that hit it.

Treat this guide, `STYLEGUIDE.md`, `README.md`, and the assessment as evidence. They go stale. When a document and the code disagree, the code is the observed behavior and the document is a claim. Say which one you used.

Separate what you verified from what you inferred. A file you did not open is not a finding. A command you did not run is not a result. If the environment cannot run a check, say that, and do not weaken the check to hide the gap.

Prefer the smallest change that preserves the existing design. Modes and shims, field classes that build both a schema and a document, `BaseResourceException`, and the task / RPC / poll path are the architecture. Extend those. A consumer supplies the shim, the endpoint paths, and the task-name field. The library does not name a product API, and it does not grow a Flask or Celery publisher to make polling work. Do not replace this with a second resource stack or a new directory layout.

Work in small steps. The assessment's PR sequence is the default order for modernization. Skip a step when a later look shows it is unnecessary, and say why. Do not start a later step by rewriting an earlier one.

Think about how the library is used. It is installed by other code, the tests construct connectors with environment variables, and a wrong default URL or a helpful stub can run against a real service. Do not add network defaults, sample credentials, or a token implementation that returns a password.

Do not commit, push, tag, or publish a release unless the task asks for that action.

## What does not apply here

The private workspace guide, its intake scripts, research checkouts, and platform handbook are not part of this repository. Do not link to private organization docs from this public tree. Do not copy `AUTHORS`, changelogs, Jenkins files, Dockerfiles, or product connectors from the private libraries. The assessment lists the names and URLs that must stay out.

Jira is not the version source here. The version is the static `version` in `pyproject.toml`.

`STYLEGUIDE.md` is the local style: snake_case functions, camelCase variables, CapCase classes, Google docstrings. Field names such as `hasNext` and `per_page` are part of the data contract. Do not reformat the library to a different variable style.

## Repository map

- `src/baseresourcelib/bases/base.py` is `Mode`, the metaclass, `BaseResource`, and pagination schemas. RPC get currently raises `HandlerMethodNotImplemented`. The assessment's PR 4 restores it, plus `run_task`.
- `src/baseresourcelib/connectors/base.py` is `ApiBase`. `poll_task` is not here yet. PR 4 puts it on this class.
- `src/baseresourcelib/connectors/brlbase.py` is the paginated client `BRLBaseApi`.
- `src/baseresourcelib/connectors/mongobase.py` is the MongoEngine queryset and pagination helper.
- `src/baseresourcelib/connectors/responseobjects.py` is the mode mappers and `ApiResponse`. `RpcMapper` already holds `getall`, `getone`, `getid`, and `rpcurl`.
- `src/baseresourcelib/fields/fields.py` is the dual schema and document fields.
- `src/baseresourcelib/errors/errors.py` is the exception hierarchy, including the task status exceptions. The package `__init__` does not re-export it yet.
- `src/baseresourcelib/utils/` holds timeout parsing, chunking, and marshal helpers. `utils/constants.py` holds `TASK_STATUSES`. Nothing in the package reads that list yet.
- `tests/unit/` is the suite tox runs.
- `docs/modernization-assessment.md` records what was compared and what to do next.

Python requirement is `>=3.12`. Packaging is Hatchling. `setup.py` and `noxfile.py` exist and are empty; they are not the build. Do not fill them in. The assessment recommends deleting them.

## Commands

Run these from the repository root with Python 3.12. `tox` installs the project into its own environments.

| Check | Command | Last observed result |
| --- | --- | --- |
| Show configured commands | `python3.12 -m tox c -e 3.12,lint,type -k commands` | Resolved `3.12`, `lint`, and `type` on 2026-11-27. This does not run the tests. |
| Unit tests | `python3.12 -m tox -e 3.12` | 21 passed. Coverage of the installed package was 45%. Importing the pagination schema emitted two `RemovedInMarshmallow4Warning` messages. |
| Lint | `python3.12 -m tox -e lint` | flake8 passed. pylint scored 9.96/10 and exited 16 on four `consider-using-f-string` findings in `src/baseresourcelib/connectors/brlbase.py`. |
| Types | `python3.12 -m tox -e type` | mypy reported 15 errors in 4 files. This env is not a green gate. |
| One test file, still inside tox | `python3.12 -m tox -e 3.12 -- tests/unit/connectors/base/test_request.py` | Not re-run as a separate command on 2026-11-27. The file is part of the 21 passing tests. |

`tox.ini` sets `API_TOKEN`, `API_USER`, and `API_PASS` for the test env. The connector tests need those. A bare pytest without them failed 9 of 21 tests on 2026-11-27, all while constructing `ApiBase`. Prefer tox so the variables and the installed package match what CI should do later.

`tox.ini` also lists a `3.13` factor. Python 3.13 was not installed in the environment that produced the results above, and that env was not run.

When a change alters a command or a gate, update this table with the command you actually ran and its result. Do not mark pylint or mypy as passing while their exits are non-zero. Do not disable a check to make the table green. The four f-string findings get fixed in a change that is already editing that file, or in the packaging step described in the assessment.

## Tests and behavior changes

A bug fix starts with a regression test that fails for the reason the bug fails. A restored behavior starts by porting or writing the test that describes it, then making that test pass. Do not lower an assertion to match a broken helper.

The schema and default contract is not fully covered by the current 21 tests. `docs/modernization-assessment.md` names the reference tests that belong with that work. Port the behavior, not product names, hostnames, or ticket ids.

Keep secrets, tokens, and live payloads out of tests and docs. Use the env vars tox already sets, or pass a token argument.

## Public tree

Before finishing a change, search the diff for employer and product identifiers: organization names, internal hosts, ticket prefixes, and private URLs. The known live leftover, the dead branch, and the author email already published in git history are recorded in the assessment. Do not reintroduce the strings. Do not rewrite published history unless that is the task.

Do not add deployment certificates, git+ssh dependencies, or author lists from the private libraries.
