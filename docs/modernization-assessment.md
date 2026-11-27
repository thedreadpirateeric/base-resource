# base-resource modernization assessment

Assessment only. No library code is changed by this document.

This is a look at how far `baseresourcelib` drifted from the two libraries it generalizes, what is actually dated, and what is old but still the right shape. The recommended work is a short sequence of reviewable changes. It is not a rewrite.

## How to read this

Claims are labeled:

- **Verified.** Read from a file in this checkout or in the attached reference trees, or observed by running a command in this environment on 2026-11-27.
- **Inference.** A conclusion from those facts. Not something a test executed.
- **Not verified.** Looked for, or relevant, but not established here.

The reference trees are the attached archives, extracted only for this review. They are not git checkouts. This assessment does not claim they match a GitHub commit. Their `AGENTS.md` files say command configuration was inspected on 2026-11-24, and their `pyproject.toml` files require Marshmallow 4. That is the content that was read.

## Sources

| Source | What was used |
| --- | --- |
| This repo, `HEAD` `93143d146fe57faecc1cd459b6fd9eddf6669e40` | Commit date 2025-04-15, message "Updates for base api". Branch `main`, clean before this document. |
| `sbdevs-bsLib` in the attached archive | Package `bslib`. Source, tests, docs, packaging, `PYTHON312.md`, `AGENTS.md`. |
| `sbdevs-bsApiLib` in the attached archive | Package `bsapilib`. Same kinds of files. |
| Workspace guidance in the attached archive | `AGENTS.md`, intake README, `PythonUpgrade/AGENTS_ROLLOUT.md`, Python 3.12 and Marshmallow 4 compatibility notes. |

**Verified:** `bslib` source is 6,466 lines across 38 Python files. `bsapilib` source is 3,206 lines across 14 Python files. `baseresourcelib` library Python is about 2,500 lines across 16 files. The whole tracked tree outside `.git`, including tests and `STYLEGUIDE.md`, is 3,461 lines.

**Not verified:** no search was made for other repositories that import `baseresourcelib`. No original-library test suite was re-run. `k8ssdk.py` (929 lines) and `rest_resources.py` (1,552 lines) were classified from their public classes, headers, and identifier search, not a line-by-line reading.

## Headline

**Verified:** the public repository's last code commit is 2025-04-15. The reference libraries, as attached, already require Python >=3.12, build with Hatchling, and depend on Marshmallow >=4.3.1,<5. `baseresourcelib` also requires Python >=3.12 and Hatchling, but it pins Marshmallow ==3.26.1 and still calls the Marshmallow 2 result attribute `.data`.

**Inference:** the generalization is not a thin copy of the November 2026 libraries. It is an earlier cut that both dropped generic framework behavior and never received the later schema-contract work. Modernization is a bounded restore plus that contract. It is not a new architecture, and it is not a tooling migration.

What is already in good shape: the Python 3.12 floor, Hatchling, tox 4 as the real runner, the mode/shim `BaseResource` design, and the field and exception vocabulary.

What is thin or wrong: empty `setup.py` and `noxfile.py`, a one-line README, a Marshmallow contract that does not match either Marshmallow 3 or 4, generic operations removed from `BaseResource`, a timeout helper that no longer preserves floats, two employer-identifying leftovers in the public connector, and a token stub that returns the caller’s password.

---

## 1. Inventory and diff

Classification:

| Tag | Meaning |
| --- | --- |
| (a) | Present, close enough to keep |
| (b) | Generic framework behavior that the strip removed or rewrote badly, and that should be restored |
| (c) | Employer or product integration. Leave it out, or replace it with a small interface |
| (d) | Dead or obsolete. Do not restore |

### 1.1 What this repository actually exports

**Verified** from `src/baseresourcelib/__init__.py` and the connector and field packages:

- `baseresourcelib.BaseResource`
- `baseresourcelib.connectors.ApiBase`
- `baseresourcelib.connectors.BRLBaseApi`
- Field types: `Boolean`, `DateTime`, `Dictionary`, `Integer`, `Float`, `List`, `String`, `ObjectId`

Exceptions live at `baseresourcelib.errors.errors` and are not re-exported. `errors/__init__.py` is a docstring only. `bases/__init__.py` is a docstring only, and that docstring still says "Handlers." Utilities are not part of `__all__`.

**Inference:** there is no compatibility promise to preserve yet if nothing else imports this package. The awkward `errors.errors` path is cheap to fix before a 0.1 tag and expensive after. That downstream-import claim was not verified by searching GitHub.

### 1.2 Module map

#### Resource core

| Reference | This repo | Tag | What the comparison showed |
| --- | --- | --- | --- |
| `bslib/handlers/basehandler.py` (`Mode`, `Base`, `BaseResource`, `PaginateSchema`, `PaginateSchemaFactory`) | `bases/base.py` | (a) for the class, (b) for the pieces below | Same metaclass, modes, and CRUD dispatch. AST: `BaseResource` has 80 methods in the reference and 73 here. |
| `bslib/schema.py` | absent; `base.py` subclasses `marshmallow.Schema` directly | (b) | Reference schema sets `unknown = EXCLUDE` and copies `load_from` aliases after pre-load hooks. |
| `bslib/handlers/pipelinejobs.py` `PipelineJobs` | absent | (b) | Generic Mongo aggregation helper used by `BaseResource.aggregate`. No employer names in the class. About 174 lines. |
| `bslib/runner.py`, `bslib/__main__.py` | absent | (d) | `main()` prints `argv` and returns 0. It is a Click packaging example, not a tool. |

Methods present in the reference `BaseResource` and absent here:

| Method | Tag | Why |
| --- | --- | --- |
| `get_long_query` | (b) | Splits a long API filter into chunks. Database mode stays one query. Uses `chunkify_list`, which is still here. |
| `aggregate`, `get_aggregate_projection_extensions` | (b) | Mongo pipeline helper plus an empty hook so subclasses can add projection fields without editing the base. |
| `run_task` | split | The idea, "submit a task and optionally poll," is (b). The body special-cases `apiName == "StorageCenterAPI"` (`name` versus `task`) and takes `deviceNumber` and `commcellName`. Those keys are (c). Restore polling with a caller-supplied task field name. Do not copy the branch. |
| `_load_data` | (b) | Reference load/dump path is explicit: lists imply `many`, reads keep `ValidationError.valid_data`, writes return field errors, and dump errors of type `ValueError`, `TypeError`, and `OverflowError` are still reported as field errors. Current code folds this into `marshall_load` / `marshall_dump`, which always catch `ValidationError` and drop the error object on the read path. |
| `_make_object_class`, `_make_object_from_class` | (a) | Inlined into `_make_object` and `_make_objects`. Same construction: dynamic subclass, copy mode, token, and MySQL connector. Not a missing feature. |

**Verified by execution** on Marshmallow 3.26.1: loading `{"name": "a", "extra": 1}` through a generated `BaseResource` schema raises `ValidationError` for the unknown field. The reference schema is written to exclude that field. **Verified by reading** `serialize_data`: it returns `schema().dump(...).data`. **Verified by execution:** `dump()` on 3.26.1 returns a `dict`, and that `dict` has no `.data` attribute. `serialize_data` raises `AttributeError` if it is reached. No current unit test calls it.

**Verified by execution:** importing `bases/base.py` emits `RemovedInMarshmallow4Warning` because `PaginateSchema` still passes `missing=`. The reference pagination fields use `load_default` and `dump_only`.

#### Connectors

| Reference | This repo | Tag | Notes |
| --- | --- | --- | --- |
| `connectors/apibase.py` `ApiBase` | `connectors/base.py` `ApiBase` | (a), with leftovers | Request, retry, status mapping, and timeout wrapper are the same design. |
| `ApiBase.sb_api_paginated_request` | `connectors/brlbase.py` `BRLBaseApi` | (a) | Moved and renamed. Docstring says BaseResourceLib. "BRL" is not an employer name. |
| `set_internal_token` | `_get_internal_token_from_env` | (b) for one behavior | Reference returns no internal token when `supportInternalToken` is false, and clears the header. Current code always reads `INTERNAL_TOKEN`. |
| `poll_task`, `_task_has_ended`, `_task_handle_poll_limit`, `_task_wait_for_response` | absent | (b) | Generic task submit-and-poll. Status names match `TASK_STATUSES` and the task exceptions. About 80 lines plus tests. |
| `connectors/responseobjects.py` | `connectors/responseobjects.py` | (a) | Same mapper classes. This repo adds `MockAPIBase` and annotations. Method sets match. Not a line-by-line behavioral audit. |
| `connectors/storagecentermongo.py` | `connectors/mongobase.py` | (a), minus one constant | **Verified:** the only deletion is `BASE_COUNTER_META` (shard key `deviceNumber`, `component`, `componentID`, `counterTime`). That constant is (c). `BaseQuerySet` and `Pagination` match. |
| `connectors/mongo.py` `mongo_connect` | absent | optional (b) | 25-line `mongoengine.connect` wrapper. Env names `BS_MONGO_DB_NAME` and `BS_MONGO_DB_URI` are internal. Callers can connect without this helper. Not part of the core hole. |
| `connectors/mysql.py` `MySQL` | absent | (c) | Despite the docstring, construction requires Password Safe project and credential ids (`kpid`, `kcid`) and loads the password from that system. |
| `connectors/identity.py` | absent | (c) | Module docstring: "Rackspace Internal Identity REST API." Default URLs are internal. The extension point that should remain is `ApiBase._attach_identity_provider`. |
| `StorageCenterAPI`, `BackupCenterAPI`, `DcxGatewayAPI`, `PasswordSafeAPI`, `NewRelicLogApi`, `NewRelicEventApi` | absent | (c) | Product clients. Password Safe should become a credential-provider protocol, not a class with `https://passwordsafe.corp.rackspace.com` as the default. |
| `ApiBase` identity object | `MockIP` | (b) to replace | **Verified:** `MockIP.new_token` returns the password it was given, and `ApiBase.__init__` always installs `MockIP`. On token expiry the connector would send that password as the new token. The reference leaves `iP` unset until a subclass attaches a provider. |

**Verified by reading** `_check_response`: `502` is in `responseCodesGone`, which is handled first, as `UpstreamDependencyGone`. The later branch `status == 502 and apiName == "MbuAPI"` is unreachable. The same order exists in the reference `apibase.py`. The branch is (d), and the name `MbuAPI` is still an employer system name sitting in the public file. `QOperationFailed502` is only constructed there. The class can stay so the exception vocabulary does not shrink for no reason; nothing in this repo raises it once the branch is gone.

**Verified** live employer string, `connectors/base.py`: token exhaustion appends `"ATTN: SBDEVs have been automatically notified!"` The reference has the same sentence. It is not dead.

#### Fields, errors, utilities

| Reference | This repo | Tag | Notes |
| --- | --- | --- | --- |
| `fields/fields.py` field classes | `fields/fields.py` | (a) classes, (b) adapter | Same eight types. Reference maps `missing` to `load_default`, `default` to `dump_default`, stores `load_from` in field metadata, and wraps validators that return `False`. This repo passes a smaller kwargs allow-list and dropped `_legacy_validator`. It also imports MongoEngine unconditionally; the reference tolerates a missing MongoEngine. For a library that already depends on MongoEngine, the unconditional import is fine. |
| `errors.py` `BSException` hierarchy | `errors/errors.py` `BaseResourceException` | (a) | Rename is the right generalization. |
| `PreferenceFetchError`, `BSIdentityException` | absent | (c) | Only meaningful with preferences and the identity client. |
| `constants.py` | `utils/constants.py` | (a) | **Verified:** files are identical. No hostnames. |
| `TIMEZONE_OFFSETS` | present, unreferenced | optional | Reference uses it only from `average_by_keys`. Nothing in this repo imports the module. **Verified** by search. |
| `TASK_STATUSES` | present, unreferenced | (d) as a binding | Defined in both trees and referenced by no Python file in either tree. The words themselves still match the task exceptions. Do not delete it in a drive-by; use it or drop it when polling is restored. |
| `chunkify_list`, `string_to_float_or_int` | `utils/utils.py` | (a) and (b) | `chunkify_list` matches. `string_to_float_or_int` was rewritten. |
| `marshall_load`, `marshall_dump` | only here | (a) for now | Small wrappers. The reference inlined the stricter policy on `BaseResource` instead. Keep them only if they still match the restored policy. |
| `average_by_keys`, `bucketize_list`, `convert_bytes`, `convert_megabytes`, `convert_gigabytes`, `inject_qry_param`, `make_uuid`, `make_truthy_falsy`, `string_to_list` | absent | optional (b) | Generic helpers with unit tests in the reference. None of them are required for `BaseResource` to function. Restore a helper when a caller in this repo needs it. Do not paste the module back to increase coverage. |
| `has_user_pass_env_vars` | absent | (c) | The error text requires `API_USER` and `API_PASS` specifically "to get a new token from Identity API." |
| `make_scapi_date_now`, `make_scapi_datetime_now` | absent | (c) / (d) | Names mean StorageCenter API. Both call `datetime.utcnow()`, which the compatibility notes call deprecated on 3.12. Do not restore these names. A naive-UTC helper is a separate decision and is not needed by any current caller. |
| `decorators.validate_timeout` | `utils/decorators.py` | (a) structure, (b) via the helper | Same parser. Docstring still says "BsLib Decorators." `BsLib` is the old package name, not the company. Low sensitivity. |

**Verified by execution** of the current helper on Python 3.12.3:

| Input | Result |
| --- | --- |
| `"120"` and timeout `"4"` | integer `120` / `4` |
| `"1.5"` and timeout `"2.12"` | `ValueError` / `TimeoutValueError` |
| timeout tuple `(3, 4.07)` | `(3, 4)` |

The reference helper does `float(str(value))` first and returns `int` only when `is_integer()` is true, so `1.5` and `4.07` stay fractional. The decorator's own error text says a float is valid. Integer strings work on this interpreter because `int` has `is_integer`; the float contract does not. This was observed here. It was not compared by running the reference tests.

`ByteScaleError` is the failure type for `convert_bytes`. Its docstring in both trees says "Byte Scaling (unit conversion) Exception." **Inference:** that is a unit-conversion name, not an identified product. It is not, by itself, an employer marker. Leave the class. Do not restore `convert_bytes` unless a caller needs it.

#### Domain handlers in `bslib` that this repo does not have

All (c) unless noted. Do not restore them into the core package.

| Module | Public types | Why it stays out |
| --- | --- | --- |
| `handlers/basedevice.py` | Device, tag, account, snapshot, and task resources | StorageCenter document model. `storagecenterSnapshotType` and `StorageCenterAPI` are hard-wired. |
| `handlers/preferences.py` | `Preference`, `StoragePreference`, `BackupPreference`, `fetch_preferences` | Product preference catalogs. |
| `handlers/passwordsafe.py`, `handlers/passwords.py` | Projects, credentials, service-account passwords | Internal credential store. Replace the idea with a provider interface. |
| `handlers/userinfo.py` | `UserInformation` | Identity user resource. |
| `handlers/datacollections.py`, `osversions.py`, `tally.py` | Timers, OS catalog, tally | Platform collections. |
| `handlers/newrelic.py` | `NewRelicApi` | Vendor client plus their log/event resources. The stdlib audit also records a separate `_timestamp` behavior bug at line 97. Do not import that bug. |
| `handlers/dockersdk.py` | `DockerSDK` | Job runner. Contains a Rackspace Jira URL and default Docker network `sbdevs_default`. |
| `handlers/k8ssdk.py` | `K8sSDK` | Job runner. The docstring example uses namespace `storagecenter`. |
| `config/search_fields.py` | `AppSearchStorageCenterKeys` | Product search keys. |

`K8sSDK` and `DockerSDK` are not the resource framework. If they are ever wanted, they are optional extras after the internal names are removed. They are not part of the restore sequence below.

#### `bsapilib` (the whole API library)

**Verified:** nothing from `bsapilib` was carried over. `baseresourcelib` has no Flask, Celery, Redis, or RabbitMQ dependency.

| Module | Tag | Notes |
| --- | --- | --- |
| `application.py` | (c) | Flask factory, CORS, rate limit, request log. Env prefix `BSAPI_`. Useful pattern, not a file to copy. |
| `rest_resources.py` | (c) | CRUD views, pagination, and task publication. Coupled to Celery ingest and snapshot fields such as `storagecenterSnapshotType`. Redesign later if a generic view extra is actually needed. |
| `login.py` | (c) | Rackspace Identity URL default, Redis session, and role names `storagecenter_developers`, `storagecenter_techs`, `storagecenter_automation`, `storagecenter_admins`, `backupcenter_admins`. Account constant `storageautomation`. |
| `connectors/rabbitmq.py`, `redisclient.py` | (c) | Broker and session client for that API. |
| `connectors/database.py` | (c) | Second `mongo_connect`, with the library's env names. |
| `connectors/esclient.py` | (d) | Reference `pyproject.toml` says Elasticsearch is unused and its modernization is deferred. |
| `deco_utils.py`, `resources.py` `HealthCheckView`, `apilivenesscheck.py` | not a core restore | Small and partly generic, and useless without the Flask app. Do not add Flask to recover a health check. |
| `utils.py` | (c) | Celery publish, event-retention days, and a comment referencing ticket `SBDEV-2987`. Pagination helpers duplicate what `BaseResource` already has. |

**Inference:** a public "base resource" library is the resource/mode/connector layer. A Flask framework is a second product. The compatibility notes describe a real, tested API contract for the private platform. Copying it would copy the platform.

#### Tests

**Verified** current suite, tox env `3.12`, 2026-11-27: **21 passed**. Coverage of the installed package: **45%** (`1131` statements, `626` missed). `mongobase.py` and `constants.py` are at 0%. `brlbase.py` is at 18%. `bases/base.py` is at 41%.

The 21 tests are the five `get` API-path tests, seven `Mode` tests, and nine `ApiBase` tests (exception text, token env, `request`). The connector tests construct `ApiBase()` with no arguments and therefore require `API_TOKEN` or `API_USER`/`API_PASS`. Those three variables are set in `tox.ini`. **Verified:** the same pytest command without them is **12 passed, 9 failed**, all nine at `ApiBase.__init__`.

| Reference test | This repo | Tag |
| --- | --- | --- |
| `tests/unit/connectors/apibase/apibase/test_request.py`, `test_get_token_from_env.py`, `test_get_exception_formatted_message.py` | `tests/unit/connectors/base/` same names | (a) |
| `handlers/basehandler/baseresource/test_get_from_api.py` | `tests/unit/bases/base/test_get_from_api.py` | (a) |
| `tests/unit/bases/base/test_mode_class.py` | only here | (a) |
| `test_marshmallow4.py`, `handlers/test_schema_contract.py`, `fields/test_defaults_contract.py` | absent | (b) with the schema restore |
| `test_get_long_query.py`, `test_aggregate.py`, `test_make_data.py`, `test_pipelinejobs.py` | absent | (b) with those methods |
| `test_run_task.py` and the four `poll_task` / task-wait tests | absent | (b), rewritten so they do not encode `StorageCenterAPI` |
| `test_decorators.py`, the `string_to_float_or_int` cases in `test_utils.py` | absent | (b) with the helper fix |
| Rest of `test_utils.py` | absent | optional, only if that helper returns |
| `test_backupcenterapi.py`, `test_storagecenterapi.py`, `test_identity.py`, `test_passwordsafe.py`, `test_dcxgatewayapi.py`, `test_k8ssdk.py` | absent | (c) |
| All eight `bsapilib` test modules | absent | (c) |

The compatibility notes say that on 2026-10-27 the reference suites were **133 passed** (`bslib`) and **25 passed** (`bsapilib`), with flake8 and pylint at 10.00/10. **Not verified here.** Those runs were not repeated. Private git dependencies, `mysqlclient`, and the Flask stack were not installed.

#### Docs, packaging, and deployment that were not carried over

| Reference | Tag | Notes |
| --- | --- | --- |
| `bslib/docs/*` resource, field, connector, and error guides | rewrite, do not copy | They are the best map of intended `BaseResource` behavior, and they are full of product URLs and connector names. Use them as evidence while restoring. Publish a new guide after the public API is settled. |
| `bsapilib/docs/*` | (c) | REST, defaults, and task-dispatch contracts for the private API. |
| `PYTHON312.md`, `ChangeLog` | do not copy | Useful history. `ChangeLog` is a `SBDEV-` ticket log. `PYTHON312.md` says Jira owns the version. |
| `AUTHORS` | (c), do not copy | Employee names, `@rackspace.com` addresses, and `*.local` hostnames. This public document does not repeat that list. |
| `deployment/`, Jenkins files, Dockerfiles | (c) | Internal image build, CA URL, and Jira labeling. |
| `.github/PULL_REQUEST_TEMPLATE.md` | do not copy as-is | The reference template is the private bumpversion flow. |

---

## 2. Modernization review

### Python version

**Verified:** this repo and both reference libraries set `requires-python` to `>=3.12`. This environment has Python 3.12.3 and does not have Python 3.13. `tox.ini` lists env `3.13`. That env was not run.

**Inference:** 3.12 is the right floor. The owner just finished a 3.12 migration of the private libraries. Raising the floor to 3.13, or adding a 3.11 compatibility line, is churn.

**Verified by search** of `src/`: no `datetime.utcnow`, no `utcfromtimestamp`, no `distutils`, `imp`, `asyncore`, or `strftime('%s')`. The stdlib audit's `bslib` hits are in `basedevice.py`, `datacollections.py`, `newrelic.py`, `osversions.py`, and `make_scapi_*`, none of which are in this repo. There is no stdlib-deprecation cleanup to do here. Do not import those call sites back under a "modernization" excuse.

### Packaging

**Verified:**

- `pyproject.toml` uses Hatchling and a static version `0.0.3`. Authors are the public maintainer address already in the file. Dependencies are exact pins.
- `setup.py` and `noxfile.py` are empty files (0 bytes).
- There is no `setup.cfg`, no `[project.optional-dependencies]`, no `[tool.hatch.version]`, and no package-path override.
- `tox -e 3.12 --notest` built `baseresourcelib-0.0.3.tar.gz` with Hatchling and installed it. Empty `setup.py` was not required.

The reference libraries use Hatchling plus `hatch-vcs`, `dynamic = ["version"]`, and `Private :: Do Not Upload`. `PYTHON312.md` says Jira remains the version source and Git tags are the hatch-vcs input.

**Inference:** static `0.0.3` is the right scheme for this public repository. `hatch-vcs` exists there to serve a Jira-to-git-tag release flow that does not apply here. Do not add it for fashion. Do delete the empty `setup.py` so a setuptools entry point cannot confuse a tool. Do delete the empty `noxfile.py` so Nox is not a second, broken runner.

Exact pins match the commit messages "lock versions" (history on `main`). Pinning is a choice, not a defect. The defect is that the pins are the pre-Marshmallow-4 set. Keep pins or the same style of upper bound the reference already tested. Do not introduce a second lockfile tool.

### Tooling

**Verified** from `tox.ini` and from running it:

| Env | Declared command | Result on 2026-11-27 |
| --- | --- | --- |
| `3.12` | pytest with coverage, package installed as a wheel/sdist | **21 passed**, 2 `RemovedInMarshmallow4Warning`, coverage **45%**. About 2 seconds after the env existed. |
| `lint` | `flake8 src`, then `pylint src` | flake8 exited 0. pylint **9.96/10**, exit 16, four `consider-using-f-string` (`C0209`) in `brlbase.py` lines 41, 43, 61, and 82. |
| `type` | `mypy src` | **15 errors in 4 files.** `utils.py` needs annotations on `errors`. `brlbase.request` does not match `ApiBase.request` and uses implicit optional defaults. `mongobase.py` annotates `iter` as a type and mis-infers `BASE_META`. `base.py` passes `dict_values` to `marshall_dump`. |
| `3.13` | same tests | **Not run.** No `python3.13` on this machine. |

`[tool.mypy.overrides]` only sets `follow_untyped_imports` for `dateutil`, `mongoengine`, `marshmallow`, and `requests`. There is no strict configuration. `.pylintrc` disables `C0103` (invalid name) and ignores imports for similarities. That matches the reference `.pylintrc`. The reference also has `setup.cfg` with flake8 `max-line-length = 80`. Flake8's default is 79, and it still passed on `src`. No line-length migration is required.

**Inference:** tox, pytest, flake8, and pylint are the right tools because they are already the project's tools and the reference's tools. Nox is not in use. Ruff, Black, or a strict mypy gate would be a second style system on top of `STYLEGUIDE.md`. That guide specifies snake_case functions, camelCase variables, and CapCase classes, with Google docstrings. The code follows it. Reformatting variables to snake_case would touch every public field name and break the resource contract. Do not do that.

The lint failure is four f-strings, not a quality program. Fix those lines in a packaging PR so the configured gate is green. Do not disable `C0209` to get there.

The mypy failure is mostly annotation debt of the existing style (`iter` as a type, implicit `None` defaults). Making mypy a merge gate before the Marshmallow restore will create a typing-only PR. Remove `type` from the default `env_list` until a change is already editing those signatures. Keep the env available for anyone who wants to run it.

There is no GitHub Actions workflow in this repo. **Inference:** add CI after `3.12` and `lint` are the gates and both pass, not before, and not as a matrix of Python versions nobody has run.

### Dependencies

**Verified** pins versus the reference `pyproject.toml` bounds:

| Package | This repo | Reference `bslib` | Assessment |
| --- | --- | --- | --- |
| marshmallow | `==3.26.1` | `>=4.3.1,<5` | This is the real upgrade. Do it with the schema contract, not as a lone bump. |
| requests | `==2.32.3` | `>=2.34.2,<3` | The reference bound is newer. A bump without a failing test is churn. |
| mongoengine | `==0.29.1` | `>=0.29.3,<0.30` | Patch difference. Move it only together with a tested Marshmallow 4 set if the field adapter needs it. |
| python-dateutil | `==2.9.0.post0` | `>=2.9.0.post0,<3` | Same generation. Fine. |
| pymongo | not direct | `>=4.17.0,<4.18` | The upper bound is documented as MongoDB 4.2 compatibility. That is an operational constraint of the private platform. Do not copy it unless this library still has to talk to MongoDB 4.2. |
| mysqlclient, docker, kubernetes, google-auth, click | absent | present | Only needed by modules tagged (c) or the dead CLI. Leave them out. |
| Flask, Celery, Redis, gunicorn, marshmallow-mongoengine | absent | `bsapilib` | Leave them out of the core package. |

The Marshmallow 4 compatibility note (tested 2026-10-27, Python 3.12.14) says a bridge probe of marshmallow 4.3.1, marshmallow-mongoengine 0.31.2, mongoengine 0.29.3, and pymongo 4.17.0 had **9 passed**. It also says that probe does not make application code which uses Marshmallow 2 result objects compatible with version 4. This repo is that second case: `serialize_data` uses `.data`, and pagination uses `missing`.

**Not verified:** current releases on PyPI as of 2026-11-27 were not queried. "Newer than 2.32.3" is taken from the reference pin, not from a fresh index lookup.

### Typing

The code mixes `list | None` and `typing.List`. On 3.12 both are valid. A sweep to builtin generics is cosmetic. The `brlbase.request` override is a real signature mismatch and should be fixed when that class is next edited, because mypy is right that the subclass does not accept what the base accepts. That is a small correctness fix, not a typing project.

### Public API shape

Keep:

- One resource metaclass, four modes (`api`, `rpc`, `db`, `direct`), shim mappers, and the field types that build both a Marshmallow schema and a MongoEngine document.
- `BaseResourceException` and the status exceptions. The rename away from `BSException` is the generalization and should stay.
- `ApiBase` as the HTTP mechanism, with authentication plugged in through `_attach_identity_provider`.
- `BRLBaseApi` as the paginated client. It is already the generic form of `sb_api_paginated_request`.

Change, once, before calling the API stable:

- Generated schemas should follow the reference contract: unknown fields excluded, legacy `missing` / `default` / `load_from` accepted, boolean-returning validators still rejecting values, reads keeping valid fields, writes returning field errors.
- Task polling should not know the string `StorageCenterAPI`.
- Token refresh should fail clearly when no provider is attached. It should not echo a password.
- Re-export exceptions from `baseresourcelib.errors` so callers do not import `errors.errors`.

Do not add, as part of modernization: a Flask layer, a CLI, product connectors, or a credential implementation. A credential provider, if added, is a protocol with `get_secret(key) -> str` (names up to the implementer) and no network default. Password Safe, Identity, and MySQL-via-vault stay outside the repository.

`STYLEGUIDE.md` is a Google-style sample, including example functions. It is documentation, not a module that tests import. Leave it. The camelCase field values are the public data contract (`totalItems`, `hasNext`, `per_page`). Keep them.

### Dated, versus old but fine

| Dated, and worth changing | Old, and fine |
| --- | --- |
| Marshmallow 3.26.1 plus `.data` and `missing=` | Python >=3.12 |
| Schema unknown-field and default behavior behind the reference | Hatchling and a static version |
| `get_long_query`, aggregate, and task poll removed | tox 4, pytest, flake8, pylint |
| `string_to_float_or_int` float contract | Google docstrings and camelCase variables |
| Empty `setup.py` and `noxfile.py` | `ApiBase` retry loop and status map |
| Lint gate red on four f-strings | `C0103` disabled, because the style guide requires camelCase |
| `MockIP` returning the password | MongoEngine queryset pagination |
| Live "SBDEVs" sentence and dead `MbuAPI` branch | Identical timezone table, as long as it stays unused or regains a caller |
| 45% coverage that never builds a schema | No GitHub Actions yet, until the gates are honest |

---

## 3. Employer identifiers

The repository is public and MIT-licensed. Names below are for a keep-or-remove decision. Restoring a file "from upstream" will reintroduce the ones marked restore-hazard.

### 3.1 Already in this public tree

**Verified** by search of the tracked tree:

| Location | Text | Live? |
| --- | --- | --- |
| `src/baseresourcelib/connectors/base.py` token-expiry message | `ATTN: SBDEVs have been automatically notified!` | Yes. Raised as part of `TokenExpiredError`. |
| `src/baseresourcelib/connectors/base.py` `_check_response` | `apiName == "MbuAPI"` selects `QOperationFailed502` | No. `502` is already handled. The name is still in the file. |
| `src/baseresourcelib/utils/decorators.py` module docstring | `BsLib Decorators.` | Yes, docstring only. Old package name. Low sensitivity. |
| `src/baseresourcelib/bases/__init__.py` | docstring `Handlers.` | Stale rename, not an employer. |

No `rackspace` host, `RSS-Engineering` URL, `SBDEV-` ticket, or `@rackspace.com` address appears in the current file tree. **Verified** by search.

`pyproject.toml` and `LICENSE` name Eric Lewis and the public GitHub address. That is the repository owner, already published. It is not one of the leftovers.

**Verified** from `git log` on `main`: 11 of 12 commits are authored as `Eric Lewis <eric.lewis@rackspace.com>`. One commit uses the public Gmail address. Those commits are already on `origin/main`. This change does not rewrite them. Rewriting published history is a separate decision and would require a force-push. Leaving the commits as they are keeps the address in the public history.

### 3.2 Would come back if the wrong files were restored

Do not copy these. Where a behavior is worth having, reimplement it without the names.

| Kind | Where it was seen | Examples, so they are not copied blindly |
| --- | --- | --- |
| Organization | reference `pyproject.toml`, docs, `AGENTS.md`, connector log line | Storage and Backup Developers, `sbdevs@rackspace.com`, `RSS-Engineering`, SBDEVs, handbook URL under that org |
| People | both `AUTHORS` files | Names, corporate emails, and `*.local` hostnames. Not reproduced here. |
| Hosts and URLs | `bslib` docs `api-reference.md` and `getting-started.md`, connector defaults, `bsapilib` README and `login.py` | `identity-internal.api.rackspacecloud.com`, `staging.identity-internal.api.rackspacecloud.com`, `api.storage.rackspace.com`, `mbuapi.storage.rackspace.com`, `api.identity.rackspace.corp`, `passwordsafe.corp.rackspace.com`, `api.dcx.rackspace.com`, `ssltool.rackspace.com` |
| Tickets | `ChangeLog`, `dockersdk.py`, `bsapilib/utils.py` | Prefix `SBDEV-`, host `rackspace.atlassian.net` |
| Product systems | handlers, connectors, login roles, `run_task` | StorageCenter, BackupCenter, MBU / `MbuAPI`, DCX Gateway, the internal Password Safe deployment, role names `storagecenter_*` and `backupcenter_admins`, account `storageautomation` |
| Internal defaults | `dockersdk.py`, `k8ssdk.py` docstring | Docker network `sbdevs_default`, example namespace `storagecenter` |
| Release process | `PYTHON312.md`, `AGENTS.md` | Jira as the version authority, private Git install URLs for `bslib`, `taskslib`, and `bsnotify` |

`X-Auth-Token` and `X-Auth-Internal-Token` are set in `connectors/identity.py`, not in the current `ApiBase` (`tokenHeader` is `None`). They come back only if that identity client is copied.

### 3.3 Decision list

1. Remove the SBDEVs sentence. A token failure can say the retry limit was reached.
2. Delete the unreachable `MbuAPI` branch.
3. Do not restore `AUTHORS`, `ChangeLog`, `deployment/`, connector clients, or the reference `AGENTS.md` links.
4. Decide separately whether the public README should say, in the owner's words, that the design descends from private work. This assessment does not put that sentence in the README. There is no README content yet beyond the title.
5. `ByteScaleError` and `BRLBaseApi` are not, on the evidence above, employer names.
6. The corporate author email is in published git history, not in the working tree. Decide whether that history stays. Do not "fix" it inside a feature PR.

---

## 4. Incremental plan

Each step is one PR. Later steps assume the earlier behavior is in place. Do not start step 3 by deleting the mode/shim design.

The order is: stop publishing internal names, repair a helper the HTTP layer already calls, restore the schema contract that the reference already proved, put back the generic resource operations, then make the existing gates tell the truth. Documentation of the public API comes after the API stops moving.

### PR 1. Scrub the public connector

**Change.** In `connectors/base.py`, remove the SBDEVs sentence. Delete the unreachable `MbuAPI` branch. Stop installing `MockIP`. If a refresh is required and no identity provider is attached, raise the existing token error instead of returning the password.

**Why.** These are the only employer strings and the only credential footgun already in the public tree. They are independent of Marshmallow.

**Tradeoff.** Anything that depended on "expired token becomes the password" will start failing. No current test covers that path. `QOperationFailed502` stays defined and unused.

**Verify.** `python3.12 -m tox -e 3.12` still passes the 21 tests. Add one test that a 502 is `UpstreamDependencyGone` for any `apiName`, and one test that token exhaustion does not use the password as a token. Search the tree again for `SBDEV`, `MbuAPI`, and `rackspace`.

### PR 2. Restore the float timeout contract

**Change.** Put `string_to_float_or_int` back to the reference algorithm (`float` first, `int` only when the float is integral). Port the reference tests for that function and the float cases in `test_decorators.py`.

**Why.** `ApiBase._api_request` is wrapped in `validate_timeout`. The wrapper's message accepts floats. The current helper rejects `"2.12"` and truncates `4.07` to `4`.

**Tradeoff.** Callers who passed a float string and caught `TimeoutValueError` will start sending a float timeout. That is the documented contract.

**Verify.** The ported tests pass under `tox -e 3.12`. Include `"2.12"` and `(3, 4.07)` as cases. Do not port `make_scapi_*` or `has_user_pass_env_vars`.

### PR 3. Restore the Marshmallow contract, and bump with it

**Change.** Bring over the behavior of `bslib/schema.py`, the field kwargs adapter, and `_legacy_validator`. Teach `BaseResource` the reference load/dump rules (`_load_data`, partial read data, write errors, `many` for lists). Update `PaginateSchema` to `load_default` and `dump_only`. Remove `.data` from `serialize_data`.

In the same PR, set Marshmallow to the bound the reference already uses (`>=4.3.1,<5`), or to an exact 4.3.1 pin if the owner wants to keep exact pins. Do not bump requests or pymongo in this PR.

Port `test_marshmallow4.py`, `test_defaults_contract.py`, and `test_schema_contract.py` onto `baseresourcelib`, dropping any fixture that names a product.

**Why.** This is the modernization the private libraries finished and this repo missed. A version bump without these edits will fail at import on `missing=`. These edits without the bump leave the code on a series whose pagination API is already warning.

**Tradeoff.** Unknown fields will be excluded instead of rejected. Callers using `schema.dump(...).data` will break, and `serialize_data` is already broken on 3.26.1. **Inference:** version `0.0.3` is the time to do this. It should be `0.1.0` when it lands, not `1.0.0`. No downstream users were searched for.

**Verify.** The three ported modules pass on the installed sdist (`tox -e 3.12`). Importing `bases/base.py` no longer emits `RemovedInMarshmallow4Warning`. One test loads an unknown field and asserts it is dropped. One test calls `serialize_data` on a small preloaded resource and asserts a dict. Do not claim the private 133-test run was reproduced.

### PR 4. Put back the generic resource operations

**Change.** Restore `get_long_query`. Restore `poll_task` and its three helpers on `ApiBase`. Restore `aggregate`, `PipelineJobs`, and `get_aggregate_projection_extensions`. Add a task-name field argument with a default, and do not special-case an API class name. Do not add `deviceNumber` or `commcellName` parameters.

Port the unit tests that match those methods. Rewrite `test_run_task.py` if a public `run_task` is added; it should assert the configured field name, not `StorageCenterAPI`.

**Why.** These are framework methods. Chunked GET and aggregation are mode-aware. Polling is connector-level and is what a task method needs. They are the main "the strip went too far" gap that is not the schema work.

**Tradeoff.** `PipelineJobs` is another public class. Export it from a clear module and mention it in the README in PR 6. Leave it out if the owner does not want Mongo aggregation in the core; in that case do not restore `aggregate` either. The hook alone is pointless.

**Verify.** Ported tests pass under tox. A grep of the PR diff finds none of the hosts or product names in section 3.2.

### PR 5. Make packaging match the gates

**Change.** Delete empty `setup.py` and `noxfile.py`. Convert the four `brlbase.py` `%` formats to f-strings so pylint's configured check passes, or fix the `request` signature at the same time if PR 4 did not. Drop `type` and `3.13` from the default `env_list`. Keep the `type` env in the file for an explicit `tox -e type`. Keep the static version. Do not add hatch-vcs, Nox, Ruff, or a lockfile. Add GitHub Actions only for `tox -e 3.12` and `tox -e lint` after both are green.

**Why.** The empty files advertise tools that are not used. The lint gate already fails for a reason that is not a design question. mypy's 15 errors are not the modernization.

**Tradeoff.** `tox` with no `-e` will no longer try 3.13 or mypy. That is honest: 3.13 was not run, and mypy does not pass. Someone can still run them by name.

**Verify.** `tox -e 3.12` and `tox -e lint` both exit 0. `tox -e type` is allowed to fail and the PR description says so. `git grep` shows no `setup.py` and no `noxfile.py`. Build an sdist the way tox already does and install it.

### PR 6. Freeze the import surface and replace the README

**Change.** Re-export the exception classes from `baseresourcelib.errors`. Export `PipelineJobs` only if PR 4 added it. Replace the one-line README with install, the Python floor, the four modes, and a pointer at the tests that define the schema contract. Update `AGENTS.md` commands if a gate changed.

**Why.** After PR 3 and PR 4 the public surface is knowable. Writing the README first would document APIs that those PRs change.

**Tradeoff.** Re-exports are a commitment. Do it once, at 0.1.0, together with the Marshmallow break if these PRs ship as a series. They can also be separate review units and one version bump at the end.

**Verify.** A fresh venv installs the sdist, imports `baseresourcelib.errors.TokenExpiredError`, and the README's install command is the command that was just run. No internal URL in the README.

### Explicitly not scheduled

- Copying domain handlers, identity, Password Safe, MySQL-via-vault, Docker, Kubernetes, New Relic, or `bsapilib`.
- A credential-provider implementation. PR 1 only removes the password echo. A protocol can wait until a second backend exists. An interface with one fake implementation is not useful yet.
- `mongo_connect`, byte-size helpers, and `average_by_keys`, until a caller in this repo needs them.
- A Flask extra. Revisit only if the owner wants a second package. Design it from the mode/shim API. Do not start from `rest_resources.py`.
- hatch-vcs, Jira versions, Nox, Ruff, Black, snake_case fields, a pymongo `<4.18` cap, and a `datetime.utcnow` sweep.
- Strict mypy as a default gate.

### What would falsify this plan

- A downstream importer of `0.0.3` that needs `missing=` to reject unknown fields, or that depends on `.data`. The bump then needs a migration note, and 0.1.0 is still the right place, but the exclusion change must be called out in the README.
- A decision that Mongo aggregation is out of scope. Skip `PipelineJobs` and `aggregate` in PR 4. The rest of PR 4 still stands.
- A decision to keep supporting an internal API that really does want `QOperationFailed502` for one client name. The current branch cannot express that, because 502 never reaches it. It would be a new, tested mapping, not a restoration of the dead branch.

---

## 5. Checks run for this assessment

Environment: Linux, CPython 3.12.3, venv under `/tmp`, tox 4. Packages installed were the pins in `pyproject.toml` plus pytest 9.2.0 and the tox lint/type tools. No system package of the library was used; tox built an sdist.

| Command | Result |
| --- | --- |
| `python3.12 -m tox c -e 3.12,lint,type -k commands` | Resolved the three command lists from `tox.ini`. |
| `python3.12 -m tox -e 3.12` | **21 passed**, coverage 45%, two `RemovedInMarshmallow4Warning`. |
| `python3.12 -m tox -e lint` | flake8 passed. pylint 9.96/10, four `C0209` in `brlbase.py`. |
| `python3.12 -m tox -e type` | mypy, 15 errors in 4 files. |
| pytest without `API_TOKEN` / `API_USER` / `API_PASS` | 12 passed, 9 failed in `ApiBase.__init__`. |
| Probe script against the installed pins | `serialize_data`'s `.data` access fails on a dict. Unknown fields raise. Float timeout inputs fail or truncate, as in section 1. |

**Not run:** `tox -e 3.13`, Nox, the reference libraries' suites, Docker image builds, and any network call to a real API. `pip index` was not queried.

Generated `.tox/`, `.coverage`, and `coverage.xml` are gitignored. They are not part of the documentation change.
