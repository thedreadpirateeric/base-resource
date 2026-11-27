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

**Not verified:** no search was made for other repositories that import `baseresourcelib`. No original-library test suite was re-run. `k8ssdk.py` (929 lines) was classified from its public class, header, and identifier search. `rest_resources.py` is 1,552 lines. The task view from `BaseTaskResourceView` through `delete`, and the Celery helpers at the top of that file, were read. The rest of that module was not.

## Headline

**Verified:** the public repository's last code commit is 2025-04-15. The reference libraries, as attached, already require Python >=3.12, build with Hatchling, and depend on Marshmallow >=4.3.1,<5. `baseresourcelib` also requires Python >=3.12 and Hatchling, but it pins Marshmallow ==3.26.1 and still calls the Marshmallow 2 result attribute `.data`.

**Inference:** the generalization is not a thin copy of the November 2026 libraries. It is an earlier cut that both dropped generic framework behavior and never received the later schema-contract work. Modernization is a bounded restore plus that contract. It is not a new architecture, and it is not a tooling migration.

What is already in good shape: the Python 3.12 floor, Hatchling, tox 4 as the real runner, the mode/shim `BaseResource` design, and the field and exception vocabulary.

What is thin or wrong: empty `setup.py` and `noxfile.py`, a one-line README, a Marshmallow contract that does not match either Marshmallow 3 or 4, RPC get and task polling removed while the `rpc` mode and `RpcMapper` shell remain, a timeout helper that no longer preserves floats, two employer-identifying leftovers in the public connector, and a token stub that returns the caller’s password.

Owner review of this assessment: task submission, the RPC mode, and task polling stay first-class generic parts of this library. Section 1.3 and PR 4 record that. Celery and the product endpoint classes stay out of the client. The Flask library is not discarded. Section 6 treats it as the server companion, in a second package, after the client contract exists.

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
| `run_task` | (b) | Submit a named task through the active shim's `poll_task`. The generic payload is `args`, `kwargs`, optional `username`, `endpoint`, and `waitForResponse`. The `StorageCenterAPI` branch that renames the task field to `name`, and the `deviceNumber` top-level copy, are (c). See section 1.3. |
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
| `poll_task`, `_task_has_ended`, `_task_handle_poll_limit`, `_task_wait_for_response` | absent | (b) | Generic submit-and-poll on `ApiBase`. Fixed sleep, not exponential backoff. Terminal statuses do not exactly match `TASK_STATUSES`. Details in section 1.3. |
| `connectors/responseobjects.py` | `connectors/responseobjects.py` | (a) | Same mapper classes. This repo adds `MockAPIBase` and annotations. Method sets match. Not a line-by-line behavioral audit. |
| `connectors/storagecentermongo.py` | `connectors/mongobase.py` | (a), minus one constant | **Verified:** the only deletion is `BASE_COUNTER_META` (shard key `deviceNumber`, `component`, `componentID`, `counterTime`). That constant is (c). `BaseQuerySet` and `Pagination` match. |
| `connectors/mongo.py` `mongo_connect` | absent | optional (b) | 25-line `mongoengine.connect` wrapper. Env names `BS_MONGO_DB_NAME` and `BS_MONGO_DB_URI` are internal. Callers can connect without this helper. Not part of the core hole. |
| `connectors/mysql.py` `MySQL` | absent | (c) | Despite the docstring, construction requires Password Safe project and credential ids (`kpid`, `kcid`) and loads the password from that system. |
| `connectors/identity.py` | absent | (c) | Module docstring: "Rackspace Internal Identity REST API." Default URLs are internal. The extension point that should remain is `ApiBase._attach_identity_provider`. |
| `StorageCenterAPI`, `BackupCenterAPI`, `DcxGatewayAPI`, `PasswordSafeAPI`, `NewRelicLogApi`, `NewRelicEventApi` | absent | (c) | Product clients. Password Safe should become a credential-provider protocol, not a class with `https://passwordsafe.corp.rackspace.com` as the default. |
| `ApiBase` identity object | `MockIP` | (b) to replace | **Verified:** `MockIP.new_token` returns the password it was given, and `ApiBase.__init__` always installs `MockIP`. On token expiry the connector would send that password as the new token. The reference leaves `iP` unset until a subclass attaches a provider. |

**Verified by reading** `_check_response`: `502` is in `responseCodesGone`, which is handled first, as `UpstreamDependencyGone`. The later branch `status == 502 and apiName == "MbuAPI"` is unreachable. The same order exists in the reference `apibase.py`. The branch is (d), and the name `MbuAPI` is still an employer system name sitting in the public file. `QOperationFailed502` is only constructed there. The class can stay so the exception vocabulary does not shrink for no reason; nothing in this repo raises it once the branch is gone.

**Verified** live employer string, `connectors/base.py`: token exhaustion appends `"ATTN: SBDEVs have been automatically notified!"` The reference has the same sentence. It is not dead.

#### 1.3 Task, RPC, and polling

Owner decision, after review of this document: these three are generic library behavior and are restored. They are not product features to leave behind. The notes below separate the mechanism, which comes back, from the bindings, which do not.

`SBTasksApi` and `SBRpcApi` are named by the task-dispatch note and by tests. Those service repositories were not in the attached archives. **Not verified:** their source. The bindings below are what `bslib` and `bsapilib` actually contain.

##### What is already in this repo

**Verified:**

- `Mode` still has an `rpc` mode, and `get` / `save` / `delete` still dispatch to `_get_from_rpc`, `_save_to_rpc`, and `_delete_from_rpc`.
- `RpcMapper` in `connectors/responseobjects.py` still stores `getall`, `getone`, `getid`, `rpcurl`, `shim`, `shimkwargs`, and `task`.
- `TaskException` and the status exceptions (`TaskRetry`, `TaskAborted`, `TaskIncompletedWarning`, `TaskIncompletedError`, `TaskFailed`, `TaskTerminated`, `TaskCrashed`) are in `errors/errors.py`.
- `TASK_STATUSES` is in `utils/constants.py`.
- `_get_from_rpc`, `_get_from_rpc_single`, and `_get_from_rpc_many` raise `HandlerMethodNotImplemented`. That is the strip. In the reference, those three methods are implemented.
- `_save_to_rpc` and `_delete_from_rpc` raise `HandlerMethodNotImplemented` here and in the reference. They were extension points, not deleted behavior. Leave them as overridable hooks.

##### Generic mechanism to restore

**Verified** from `bslib/connectors/apibase.py` and `bslib/handlers/basehandler.py`.

`poll_task` is an HTTP client, not a broker:

1. `POST` `endpoint` (default `"/tasks"`) with the caller's body. `passOnFailure` is forced off for that POST. A non-dict body, or a missing / blank / non-string `taskID`, raises `ApiRequestError`. No sleep and no follow-up GET happen in that case. The reference tests patch `post`, `get`, and `time.sleep`.
2. If `waitForResponse` is false, return the POST body.
3. If true, sleep 2 seconds (this pause is hardcoded, separate from the interval below), then GET `"{endpoint}/{taskID}"`. The first GET does not wait. Later GETs wait a fixed `taskCheckSleep` (default 2) and stop when `_task_has_ended` or the attempt limit is hit. There is no exponential backoff in this loop. `ApiBase.throttleBackoffFactor` is the HTTP retry backoff for status codes 429 and 502–504. It is a different mechanism. Do not merge the two.
4. Terminal statuses in `_task_has_ended` are `finished`, `failed`, `aborted`, `crashed`, `terminated`, and `successful`. Anything else, including a missing status, is still running.
5. Hitting the limit rewrites the task to `status="terminated"`, `results.success=False`, and a `results.response` string. It does not raise.

**Verified by reading** the limit lookup, not by running it with the variables set: `poll_task` reads `TASK_POLLING_LIMIT` and `TASK_POLLING_SLEEP`, then keeps the default unless the value `isinstance(..., int)`. `os.getenv` returns a string, so a normal environment value never passes that test. The reference wait test expects `taskCheckMax=1800` and `taskCheckSleep=2`. Restore the intended knobs by parsing the strings. Do not copy the `isinstance(..., int)` check.

`TASK_STATUSES` is `submitted`, `waitingretry`, `running`, `successful`, `aborted`, `incomplete`, `failed`, `terminated`, `crashed`. The poller also treats `finished` as terminal, and it does not treat `incomplete` as terminal. `incomplete` has `TaskIncompletedWarning` and `TaskIncompletedError`. **Inference:** those lists drifted. The restore should take the terminal set as an argument whose default is the poller's tuple, and keep `TASK_STATUSES` as the record vocabulary. Unifying them silently would change when a poll stops.

`run_task` builds one body and calls `poll_task` on the active mode's shim:

- `args` is the positional tuple as a list.
- Remaining keywords become `kwargs`, except `endpoint` (default `"/tasks"`), `waitForResponse` (default true), `deviceNumber`, and `username`, which are popped.
- `username`, when set, is copied to the top level.
- `deviceNumber`, when not `None`, is copied to the top level. The value `0` is sent. `None` is omitted.
- The task name is `payload["name"]` when `activeshim.apiName == "StorageCenterAPI"`, and `payload["task"]` otherwise. `test_run_task.py` locks that for `RPCApi`, `TasksApi`, and `StorageCenterAPI`.

The generic part is the envelope `{<task field>: name, "args": [...], "kwargs": {...}}` plus optional top-level `username` and an optional caller-supplied routing value. The class-name branch is the binding. Restore `run_task` with a `taskField` argument defaulting to `"task"`. A consumer who still speaks the old key passes `taskField="name"`. The library does not mention `StorageCenterAPI`.

`_get_from_rpc` is the RPC mode, and it is also generic once the routing keys are data:

- The mapper supplies `rpcurl`, `getall`, `getone`, and `getid`.
- Single-object get calls `run_task(getone or getall, id, endpoint=rpcurl, **query)`. Collection get calls `run_task(getall, ...)`.
- On `task["success"]` true, `results.response` becomes the mode data and is loaded through the schema. Otherwise the response string is stored on `RpcMapper.errors`.

The reference special-cases fields named `deviceNumber` and `commcellName`: they are required when declared, sent in the payload, and copied back onto each result row. That pair is the product binding. **Proposed:** the mapper gains an optional list of routing fields (the reference behavior is "whatever the resource declared under those two names"). A consumer sets `routingFields=("deviceNumber",)` or `("accountId",)`. Empty means "do not invent routing fields." `commcellName` in the reference `run_task` is not popped; it stays inside `kwargs`. The dispatch note says the same thing for the private APIs. Do not add a `commcellName` parameter.

`TaskBaseResource` in `handlers/basedevice.py` is the task record: `taskID`, `username`, `dateAdded`, `dateEnded`, `task`, `status` defaulting to `"submitted"`, `success` defaulting to false, `results`, `queue`, `kwargs`, plus `deviceNumber`. Concrete classes `TaskResource`, `AutoTaskResource`, `DataCollTaskResource`, `RpcResource`, and `AutoTaskLogResource` bind `StorageCenterAPI` and paths such as `/rpc/tasks`, `/automation/tasks`, and `/datacollections/tasks`. Their `model_default` callables use `datetime.utcnow()`.

**Proposed:** add `TaskRecord(BaseResource)` under `src/baseresourcelib/bases/task.py` with the generic fields only. No `deviceNumber`, no default URL, no shim. A consumer subclasses it, adds their own fields, and sets `_meta["api"]` to their shim and paths. Status defaults stay `"submitted"` and `False`. Timestamp defaults wait for an explicit naive-UTC decision. Do not copy `utcnow()` in just to match the old model.

##### Product bindings that stay out

| Piece | Where | Why it is not the generic mechanism |
| --- | --- | --- |
| `apiName == "StorageCenterAPI"` | `run_task` | Chooses JSON key `name` instead of `task`. |
| `deviceNumber` / `commcellName` required by name | `_get_from_rpc`, `TaskBaseResource`, `BaseTaskResourceView.fetch_data_from_request` | Routing identity for that platform. A truthy device is also prepended to Celery `args`. |
| `AutoTaskResource`, `DataCollTaskResource`, `RpcResource`, `AutoTaskLogResource` | `basedevice.py` | Shim and URL bindings. |
| `BaseTaskResourceView` | `bsapilib/rest_resources.py` | Flask view. Looks up a task definition, accepts key `task` or `name`, checks `ldapRoles` plus `storagecenter_automation`, and publishes to Celery. GET/PUT rehydrate `TaskResults` rows. |
| `add_celery_task`, `BSCelerySchema`, `_celery_payload` | `bsapilib/utils.py`, `rest_resources.py` | Prefixes names with `app.` unless they start with `bscelery` or `app`. One queue name is `bscelery_appsearch_tasks_queue`. |
| `celery_factory`, `CeleryConfig` | `bsapilib/connectors/rabbitmq.py` | Publisher. The default broker URL embeds a username, a password, and a vhost. Do not copy that URL into this repo. |
| `TaskDispatchError` | `bsapilib/errors.py` | Flask `ServiceUnavailable` for that publisher. |

The task-dispatch note describes the private server contract: POST returns 201 without waiting, the document is saved before publish, and the same UUID is Celery's `task_id`. That is the server. This library's job is the client: submit, poll, and read the RPC mode. A Flask or Celery extra is still a later product, and it is not required to make task, RPC, and polling real.

##### Proposed shape

**Proposed**, not implemented:

| Piece | Where | Role |
| --- | --- | --- |
| `poll_task` and the three helpers | `src/baseresourcelib/connectors/base.py` on `ApiBase` | HTTP submit and poll. Override `_task_has_ended` or pass `terminalStatuses`, `maxChecks`, and `intervalSeconds`. |
| `run_task` | `src/baseresourcelib/bases/base.py` on `BaseResource` | Build the envelope and call the active shim. `taskField` defaults to `"task"`. |
| `RpcMapper` | already in `connectors/responseobjects.py` | Consumer config: `shim`, `rpcurl`, `getall`, `getone`, `getid`, and optional `routingFields`. |
| `_get_from_rpc` and the single/many helpers | `bases/base.py` | Use the mapper. Apply `results.response` through the schema load path from PR 3. |
| `TaskRecord` | `src/baseresourcelib/bases/task.py` | Generic task document and schema. No endpoint. |
| `TASK_STATUSES` | `utils/constants.py` | Documented vocabulary. The poller's default terminal set stays separate and is tested. |

A consumer plugs in endpoints without editing the library:

```python
class Job(TaskRecord):
    _meta = {
        "uid": ("taskID",),
        "api": {
            "shim": MyApi,
            "urlget": "/jobs",
            "urlpost": "/jobs",
            "urlsingle": "/jobs/{taskID}",
        },
    }

class Widget(BaseResource):
    _meta = {
        "rpc": {
            "shim": MyApi,
            "rpcurl": "/jobs",
            "getall": "widgets.list",
            "getone": "widgets.get",
            "getid": "widgetId",
            "routingFields": ("widgetId",),
        }
    }
```

`MyApi` is their `ApiBase` subclass. Its `baseURL` is their host. `job.run_task("widgets.refresh", widget_id, taskField="task", endpoint="/jobs")` posts the envelope. `widget.get()` in rpc mode calls `run_task` with the mapper's method names. Nothing in the library names their service.

##### How to test without a service

Port the reference tests. They already mock the transport.

- `test_task_has_ended.py`: missing status is not terminal.
- `test_task_handle_poll_limit.py`: limit result is `terminated` with `results.success` false.
- `test_task_wait_for_response.py`: patch `get` and `sleep`. Assert the GET URL is `"{endpoint}/{taskID}"` and that `sleep` is the fixed interval.
- `test_poll_task.py`: patch `post`. A bad `taskID` raises `ApiRequestError` and does not sleep. `waitForResponse=False` does not poll. `passOnFailure=True` still fails the POST.
- `test_run_task.py`: patch `poll_task`. Assert the envelope uses `taskField` and does not add `deviceNumber` unless the caller passed a routing value. No API class name in the assertion.
- One `TaskRecord` test builds the schema from the class and dumps a dict. No MongoDB.
- One rpc-mode test uses a `SimpleNamespace` shim, as `test_run_task.py` does, and checks that `getone` receives the configured id.

Do not start Flask, Celery, RabbitMQ, or a socket. The reference poll tests import `ApiBase()` and therefore need `API_TOKEN`, which tox already sets.

#### Fields, errors, utilities

| Reference | This repo | Tag | Notes |
| --- | --- | --- | --- |
| `fields/fields.py` field classes | `fields/fields.py` | (a) classes, (b) adapter | Same eight types. Reference maps `missing` to `load_default`, `default` to `dump_default`, stores `load_from` in field metadata, and wraps validators that return `False`. This repo passes a smaller kwargs allow-list and dropped `_legacy_validator`. It also imports MongoEngine unconditionally; the reference tolerates a missing MongoEngine. For a library that already depends on MongoEngine, the unconditional import is fine. |
| `errors.py` `BSException` hierarchy | `errors/errors.py` `BaseResourceException` | (a) | Rename is the right generalization. |
| `PreferenceFetchError`, `BSIdentityException` | absent | (c) | Only meaningful with preferences and the identity client. |
| `constants.py` | `utils/constants.py` | (a) | **Verified:** files are identical. No hostnames. |
| `TIMEZONE_OFFSETS` | present, unreferenced | optional | Reference uses it only from `average_by_keys`. Nothing in this repo imports the module. **Verified** by search. |
| `TASK_STATUSES` | present, unreferenced | (b) when polling returns | Defined in both trees and referenced by no Python file in either tree. It is the status vocabulary for a task record. The poller uses a different terminal set. Keep the constant and pass an explicit terminal set into the poller. Do not pretend the two lists are the same. |
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
| `handlers/basedevice.py` device, tag, account, and snapshot classes | StorageCenter document model | `storagecenterSnapshotType` and `StorageCenterAPI` are hard-wired. Stay out. |
| `handlers/basedevice.py` `TaskBaseResource` and the concrete task classes | task record plus product URLs | The generic fields are restored as `TaskRecord` (section 1.3). The classes that bind `/rpc/tasks` and the other product paths stay out. |
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
| `rest_resources.py` | (c) for the Flask and Celery view | `BaseTaskResourceView` was read (from the class through `delete`). It is the private server: login, LDAP roles, definition lookup, and Celery publish. The client-side task and poll behavior is restored from `bslib` instead. The rest of this 1,552-line module was not read line by line. |
| `login.py` | (c) | Rackspace Identity URL default, Redis session, and role names `storagecenter_developers`, `storagecenter_techs`, `storagecenter_automation`, `storagecenter_admins`, `backupcenter_admins`. Account constant `storageautomation`. |
| `connectors/rabbitmq.py`, `redisclient.py` | (c) | Broker and session client for that API. |
| `connectors/database.py` | (c) | Second `mongo_connect`, with the library's env names. |
| `connectors/esclient.py` | (d) | Reference `pyproject.toml` says Elasticsearch is unused and its modernization is deferred. |
| `deco_utils.py`, `resources.py` `HealthCheckView`, `apilivenesscheck.py` | not a core restore | Small and partly generic, and useless without the Flask app. Do not add Flask to recover a health check. |
| `utils.py` | (c) | Celery publish, event-retention days, and a comment referencing ticket `SBDEV-2987`. Pagination helpers duplicate what `BaseResource` already has. |

**Inference, superseded by section 6:** the first pass of this assessment treated the Flask library as a product to leave out. The owner asked for it as a companion that belongs with this work. The table above is the module sketch. Section 6 is the recommendation. Copying the file tree unchanged would still copy the platform.

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
| `test_run_task.py` and the four `poll_task` / task-wait tests | absent | (b) | Already mock HTTP. Port them. Drop the `StorageCenterAPI` / `deviceNumber` cases or replace them with a caller-supplied task field name. |
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
| Flask, Celery, Redis, gunicorn, marshmallow-mongoengine | absent | `bsapilib` | Leave them out of `baseresourcelib`. Flask, Redis, and marshmallow-mongoengine belong to the companion in section 6. Celery stays out of both. |

The Marshmallow 4 compatibility note (tested 2026-10-27, Python 3.12.14) says a bridge probe of marshmallow 4.3.1, marshmallow-mongoengine 0.31.2, mongoengine 0.29.3, and pymongo 4.17.0 had **9 passed**. It also says that probe does not make application code which uses Marshmallow 2 result objects compatible with version 4. This repo is that second case: `serialize_data` uses `.data`, and pagination uses `missing`.

**Not verified:** current releases on PyPI as of 2026-11-27 were not queried. "Newer than 2.32.3" is taken from the reference pin, not from a fresh index lookup.

### Typing

The code mixes `list | None` and `typing.List`. On 3.12 both are valid. A sweep to builtin generics is cosmetic. The `brlbase.request` override is a real signature mismatch and should be fixed when that class is next edited, because mypy is right that the subclass does not accept what the base accepts. That is a small correctness fix, not a typing project.

### Public API shape

Keep:

- One resource metaclass, four modes (`api`, `rpc`, `db`, `direct`), shim mappers, and the field types that build both a Marshmallow schema and a MongoEngine document.
- `BaseResourceException`, including the task status exceptions.
- `ApiBase` as the HTTP mechanism, including `poll_task` once PR 4 restores it, with authentication plugged in through `_attach_identity_provider`.
- `BRLBaseApi` as the paginated client. It is already the generic form of `sb_api_paginated_request`.
- `run_task`, the RPC mapper, and `TaskRecord`, as the generic task and RPC surface. Endpoints and task-name keys are consumer configuration.

Change, once, before calling the API stable:

- Generated schemas should follow the reference contract: unknown fields excluded, legacy `missing` / `default` / `load_from` accepted, boolean-returning validators still rejecting values, reads keeping valid fields, writes returning field errors.
- `run_task` takes `taskField` (default `"task"`). It does not branch on an API class name.
- Token refresh should fail clearly when no provider is attached. It should not echo a password.
- Re-export exceptions from `baseresourcelib.errors` so callers do not import `errors.errors`.

Do not add, as part of modernization: a Flask layer, a Celery publisher, a CLI, product connectors, or a credential implementation. A credential provider, if added, is a protocol with `get_secret(key) -> str` (names up to the implementer) and no network default. Password Safe, Identity, and MySQL-via-vault stay outside the repository.

`STYLEGUIDE.md` is a Google-style sample, including example functions. It is documentation, not a module that tests import. Leave it. The camelCase field values are the public data contract (`totalItems`, `hasNext`, `per_page`). Keep them.

### Dated, versus old but fine

| Dated, and worth changing | Old, and fine |
| --- | --- |
| Marshmallow 3.26.1 plus `.data` and `missing=` | Python >=3.12 |
| Schema unknown-field and default behavior behind the reference | Hatchling and a static version |
| RPC get and `poll_task` removed; `rpc` mode is only a stub | tox 4, pytest, flake8, pylint |
| `get_long_query` and aggregate removed | `RpcMapper` and the task exception classes, which are already here |
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
| Product systems | handlers, connectors, login roles, the `StorageCenterAPI` branch inside `run_task` | StorageCenter, BackupCenter, MBU / `MbuAPI`, DCX Gateway, the internal Password Safe deployment, role names `storagecenter_*` and `backupcenter_admins`, account `storageautomation`. The task client itself is generic and is restored. |
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

The order is: stop publishing internal names, repair the timeout helper the HTTP layer already calls, restore the schema contract, then restore task submission, RPC get, and polling on top of that contract. Chunked GET and aggregation follow. Packaging and the README come after the client API stops moving. The Flask companion (section 6) starts only after that client surface exists. It is a second distribution in this repository, not a reason to delay PR 4, and not a module inside `baseresourcelib`.

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

### PR 4. Restore generic task submission, RPC get, and polling

**Change.** This is the owner-requested restore from section 1.3. It comes after PR 3 because RPC results and `TaskRecord` go through the schema load path. It does not wait on aggregation or on any server framework.

On `ApiBase`, add `poll_task`, `_task_has_ended`, `_task_handle_poll_limit`, and `_task_wait_for_response`. Parse `TASK_POLLING_LIMIT` and `TASK_POLLING_SLEEP` as integers. Keep the fixed interval. Accept `terminalStatuses`, `maxChecks`, and `intervalSeconds` so a consumer can override them. Default the terminal set to the reference poller tuple.

On `BaseResource`, add `run_task` with `taskField="task"`. Restore `_get_from_rpc`, `_get_from_rpc_single`, and `_get_from_rpc_many` against `RpcMapper`. Add optional `routingFields` on the mapper. Do not special-case a class name, `deviceNumber`, or `commcellName`.

Add `TaskRecord` in `src/baseresourcelib/bases/task.py` with the generic fields only, and export it from the package when PR 7 freezes the surface. Leave `_save_to_rpc` and `_delete_from_rpc` as the `HandlerMethodNotImplemented` hooks they already are in both trees.

Port the mocked poll tests and a rewritten `test_run_task.py`. Add the schema-only `TaskRecord` test and the rpc-mode test from section 1.3. No network, Flask, Celery, or RabbitMQ.

**Why.** The `rpc` mode, mapper, status exceptions, and `TASK_STATUSES` are already public surface, and the behavior behind them was stubbed. Polling is how a task client knows the work finished. Doing it after the schema PR means the result load uses `valid_data` and `load_default` instead of the Marshmallow 3 path PR 3 deletes.

**Tradeoff.** Callers must pass `taskField="name"` if their server uses that key. The old `StorageCenterAPI` branch will not exist. `incomplete` stays non-terminal under the default poller, matching the reference poller and not `TASK_STATUSES`. The env-var parse is a behavior fix relative to the reference source: string values will start to work. Document that in the PR.

**Verify.** `tox -e 3.12` passes the existing 21 tests plus the ported poll and `run_task` tests. A test sets `TASK_POLLING_SLEEP=5` and asserts the wait helper is called with interval 5. A test proves `sleep` is not called when the POST body has no `taskID`. Grep the diff for `StorageCenter`, `deviceNumber`, `commcellName`, `celery`, `amqp`, and `rackspace`. None of those strings are added.

### PR 5. Put back chunked GET and aggregation

**Change.** Restore `get_long_query`, `aggregate`, `PipelineJobs`, and `get_aggregate_projection_extensions`. Port their unit tests.

**Why.** These are the other generic `BaseResource` methods the strip removed. They do not depend on tasks. They were split out of the old combined PR so the task restore can be reviewed on its own.

**Tradeoff.** `PipelineJobs` is another public class. Export it in PR 7. Skip this whole PR if Mongo aggregation is out of scope. That skip does not change PR 4.

**Verify.** Ported tests pass under `tox -e 3.12`. The diff adds no host or product name from section 3.2.

### PR 6. Make packaging match the gates

**Change.** Delete empty `setup.py` and `noxfile.py`. Convert the four `brlbase.py` `%` formats to f-strings so pylint's configured check passes. Drop `type` and `3.13` from the default `env_list`. Keep the `type` env in the file for an explicit `tox -e type`. Keep the static version. Do not add hatch-vcs, Nox, Ruff, or a lockfile. Add GitHub Actions only for `tox -e 3.12` and `tox -e lint` after both are green.

**Why.** The empty files advertise tools that are not used. The lint gate already fails for a reason that is not a design question. mypy's 15 errors are not the modernization.

**Tradeoff.** `tox` with no `-e` will no longer try 3.13 or mypy. That is honest: 3.13 was not run, and mypy does not pass. Someone can still run them by name.

**Verify.** `tox -e 3.12` and `tox -e lint` both exit 0. `tox -e type` is allowed to fail and the PR description says so. `git grep` shows no `setup.py` and no `noxfile.py`. Build an sdist the way tox already does and install it.

### PR 7. Freeze the import surface and replace the README

**Change.** Re-export the exception classes from `baseresourcelib.errors`. Export `TaskRecord`. Export `PipelineJobs` only if PR 5 added it. Replace the one-line README with install, the Python floor, the four modes, and a short task example: subclass `TaskRecord` or set `RpcMapper` fields, pass your shim and paths, call `run_task` or `get`. Point at the mocked tests. Update `AGENTS.md` commands if a gate changed.

**Why.** After PR 3, PR 4, and PR 5 the public surface is knowable. Writing the README first would document APIs that those PRs change.

**Tradeoff.** Re-exports are a commitment. Do it once, at 0.1.0, together with the Marshmallow break if these PRs ship as a series. They can also be separate review units and one version bump at the end.

**Verify.** A fresh venv installs the sdist, imports `baseresourcelib.errors.TaskFailed` and `baseresourcelib.TaskRecord`, and the README's install command is the command that was just run. No internal URL in the README.

### PR 8. Second distribution for the HTTP companion

**Change.** After PR 7, add the layout in section 6.3: `api/pyproject.toml` and `api/src/baseresourceapi/`, depending on `baseresourcelib` and not imported by it. First slice is the app factory, health check, endpoint registration, and `ResourceView` get/post/put/delete with pagination and validation, tested with mongomock and a fake publisher. No Identity client, no Celery, no snapshot fields, no `taskslib`.

**Why.** The private API library is the server half of the same resource contract. Its own defaults note says HTTP and query policy stay out of the resource library. A second distribution keeps that boundary and still lets one pull request change both sides.

**Tradeoff.** This is a new public package with Flask, MongoEngine, and Marshmallow. It waits until the client package can be installed, so the view is not written against the broken `.data` path. Shipping it in the same pull request as PR 3 would mix the schema break with a new framework.

**Verify.** From a clean venv, install the client sdist, then the API package. `tox -e py` in `api/` passes without a network service. `baseresourcelib` does not import `baseresourceapi`. The API tree has none of the hosts or role names in section 3.

### Explicitly not scheduled

- Copying domain handlers, identity, Password Safe, MySQL-via-vault, Docker, Kubernetes, New Relic, or the private Celery, RabbitMQ, and Identity modules. `celery_factory` and `login.py` are not the companion's first slice. PR 8 builds the HTTP half. It does not vendor the broker.
- A credential-provider implementation. PR 1 only removes the password echo. A protocol can wait until a second backend exists. An interface with one fake implementation is not useful yet.
- `mongo_connect`, byte-size helpers, and `average_by_keys`, until a caller in this repo needs them.
- Putting Flask inside `baseresourcelib`, or opening a second repository before the client 0.1 surface exists. Section 6 records why.
- hatch-vcs, Jira versions, Nox, Ruff, Black, snake_case fields, a pymongo `<4.18` cap, and a `datetime.utcnow` sweep.
- Strict mypy as a default gate.

### What would falsify this plan

- A downstream importer of `0.0.3` that needs `missing=` to reject unknown fields, or that depends on `.data`. The bump then needs a migration note, and 0.1.0 is still the right place, but the exclusion change must be called out in the README.
- A decision that Mongo aggregation is out of scope. Skip PR 5. PR 4 still stands.
- A decision to keep supporting an internal API that really does want `QOperationFailed502` for one client name. The current branch cannot express that, because 502 never reaches it. It would be a new, tested mapping, not a restoration of the dead branch.
- Evidence that RPC save or delete had a real body in a tree newer than the attached archive. In the attached `basehandler.py` both methods only raise `HandlerMethodNotImplemented`. This plan leaves them as hooks.
- A decision that the HTTP library must version and release on its own calendar from the first public tag. Use a second repository then. The dependency direction does not change. Section 6.3 is the layout either way.

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

The `bsapilib` unit suite was not installed or run. Section 6 cites that library's own docs for its reported counts.

---

## 6. The HTTP companion (`bsapilib`)

The first sections are the client library (`bslib` to `baseresourcelib`). `bsapilib` is the server that sits on that client. The owner describes the pair as working together, and asked whether the public form is a second package in this repository or a second repository. This section answers that. It does not copy the private tree into either place.

### 6.1 What it provides, and how the two are used together

**Verified** from the attached `bsapilib` sources and docs.

`bsapilib` is a Flask-RESTful layer. `get_app_and_api` builds a Flask app, a rate limiter, CORS, request timing signals, and a `/healthcheck` route. `add_api_endpoint` registers a view class. `BaseResourceView` implements GET, POST, PUT, and DELETE over a MongoEngine document and a Marshmallow schema: pagination, distinct queries, validation failures as HTTP 400, duplicate keys as 409, and an optional post-save publish step. `BaseTaskResourceView` saves a task document before publication and, on GET, puts stored result rows back on `results.response`. `deco_utils.schema_without_model_build` stops a Marshmallow-MongoEngine schema from constructing a document during parse, so a query or a PUT body does not invent model defaults.

The dependency runs one way. `rest_resources.py` imports `bslib.schema.Schema`, `bslib.errors.NothingFound404`, `bslib.errors.DuplicateRecord409`, `bslib.utils.make_uuid`, and `bslib.config.search_fields.SEARCH_FIELDS`. `errors.py` subclasses `bslib.errors.BSException`. `utils.py` imports `bslib.schema` and three `bslib.utils` helpers. A search of `bslib` source found no import of `bsapilib`.

`pyproject.toml` also requires `taskslib` and `bsnotify` by private git URL. `rest_resources.py` imports `taskslib.resources.TaskResults` at module level, so the view module does not import without that package. A search of `bsapilib` source found no use of `bsnotify`. It is a declared dependency with no caller in this tree.

The defaults note draws the line the code follows. Field aliases, `model_default`, and schema generation belong to the resource library, because API, RPC, and direct callers share them. GET filter parsing, "do not build a Mongo document while reading a payload," and HTTP status mapping belong to the API library. It says a global default change in the resource library would not fix the HTTP behavior, and it says not to move HTTP policy into the resource library. StorageCenter's own helpers bypass the shared view. That bypass is named as follow-through for the private app, not as a reason to merge the two libraries.

The pair at runtime, **inferred** from those pieces:

1. A service subclasses the view, passes a document class and a schema built from the resource library's fields, and registers the paths with `add_api_endpoint`.
2. POST validates, saves, and may publish. The task view's contract is: the row exists before the broker call, and a publish failure stays on the row as `results.response`. POST returns 201, not the worker's result.
3. A caller using `BaseResource.run_task` or `poll_task` POSTs the envelope and GETs `{endpoint}/{taskID}` until the status is terminal. The server that stored the row is this library. The client that waits is the other one.

That is the fit. The client does not embed Flask. The server does not reimplement field defaults. The six expected failures in `test_defaults_contract.py` are labeled as core and Marshmallow 4 gaps that reach the API boundary. The test's docstring says the API wrappers do not repair them. The xfail reasons are: core default overrides `model_default`, Marshmallow 4 rejects `required` with a load default, renaming `default` drops the Mongo fallback, load defaults skip conversion, dump defaults serialize differently from Marshmallow 2, and load defaults skip validation. **Verified** by reading the marks. The suite was not run here.

Reported suite sizes, from the attached docs, **not re-run**:

| Document | Claim |
| --- | --- |
| Compatibility note, 2026-10-27 | 25 passed, including the app factory and fakeredis limiter tests |
| `docs/defaults-contract.md` | 108 passed, six expected failures |
| `docs/rest-resource-contract.md` | Full tox on Python 3.12.16: 219 passed, six expected failures. An earlier battery is described as 237 passed and six expected failures. Pylint 10.00/10 |

The counts differ because the docs describe different points in the work. This assessment does not pick one as the current upstream total.

The contract doc shows how the authors already test the pair: `PYTHONPATH=src:../sbdevs-bsLib/src` and `tox --skip-pkg-install`. Authentication and the broker are mocked. mongomock stands in for MongoDB. That is the usage pattern to keep.

### 6.2 Generic, employer-specific, and dead

Same tags as section 1. "Restore" here means "carry into the public companion," not "merge into `baseresourcelib`."

| Piece | Tag | Why |
| --- | --- | --- |
| `get_app_and_api`, `/healthcheck`, CORS from an env list, request timing | (b) | Generic Flask assembly. The required env name today is `BSAPI_APP`. Rename the prefix when porting. Default CORS origins in the factory are localhost ports. |
| `create_limiter` | (b) | Redis storage when `BSAPI_REDIS_URI` answers, otherwise in-process memory. Tests cover that fallback. The default limit string `"200 per second"` can stay overridable. |
| `add_api_endpoint`, `add_aggregator` | (b) | Register a view and, when the class asks, a POST `.../aggregator` route. |
| `BaseResourceView` get/post/put/delete, pagination, distinct, 400/409 mapping | (b) | The HTTP contract. Depends on the resource library's schema and on `NothingFound404` / `DuplicateRecord409`. |
| `schema_without_model_build`, `deco_marshal_data`, query partial-load in `make_args` | (b) | Keeps parse separate from document construction. The defaults note assigns this to the API library on purpose. |
| `ModifiedResourceView` | (b) if the fields are generic | Adds modification metadata on write. Port only the hook. Do not bring product field names with it. |
| `SnapshotResourceView`, `SnapModResourceView` | (c) | Snapshot soft-delete. The view initializes filters with `storagecenterSnapshotType` and `storagecenterSnapshotTime`. |
| `BaseResourceView._has_search_field_change` | (c) | Reads `bslib.config.search_fields.SEARCH_FIELDS`. That module's enum is App Search keys for storage arrays. |
| `BaseTaskResourceView` save-then-publish and result rehydration | (b) for the sequence, (c) for the bindings | The sequence matches the client poller. The body looks up task definitions, accepts `task` or `name`, checks `ldapRoles` plus `storagecenter_automation`, prepends `deviceNumber` to args, and stores rows through `taskslib.TaskResults`. |
| `login.py` | (c) | Default identity URL is `https://identity-internal.api.rackspacecloud.com/v2.0`. Roles include `storagecenter_*` and `backupcenter_admins`. Account constant `storageautomation`. `PYTHON312.md` says verification is on, and the private image adds a private CA. |
| `require_login` as a seam | (b) as a hook only | Views call it. The companion should take a callable the application supplies. The Rackspace implementation stays out. |
| `add_celery_task`, `BSCelerySchema`, `_celery_payload`, `rabbitmq.py` | (c) | Queue name `bscelery_appsearch_tasks_queue`, task-name prefixes `app.` and `bscelery`, and a default broker URL that embeds a username, a password, and a vhost. Do not copy that URL. |
| `TaskDispatchError` | (c) as written | The message says the task could not be added to the RabbitMQ queue. A generic publish failure can exist later, without that wording, once a publisher interface exists. |
| `connectors/database.py` `mongo_connect` | optional (b) | Same shape as the client helper, with `BSAPI` env names. |
| `connectors/redisclient.py` | optional (b) | Session cache used by login. Useful if an application brings its own auth. Not part of the first slice. `utcnow` is used here. |
| `connectors/esclient.py`, `bulk()` | (d) | `pyproject.toml` says Elasticsearch is unused, kept as an extra, and still on the 7.x client. `bulk()` is called from POST when `self.bulk` is set, so the call site is live and the integration is declared deferred. Leave it out. |
| `apilivenesscheck.py` | (c) | Reads cgroup files and writes logs to `/proc/1/fd/1`. That is a cluster probe, not the library health check. `/healthcheck` is the generic one. |
| `resources.py` `HealthCheckView` | (b) | Returns `{"health": true, "code": 200}` when the Flask app exists. Small, and it belongs with the factory. |
| Pagination helpers in `utils.py` | (a) overlap | The resource library already has `PaginateSchema`. The API copy should call that, not grow a second field grammar. The defaults note says the same thing. |

### 6.3 Same repository or a separate one

**Recommendation:** one repository, two distributions. The HTTP code lives under `api/` and imports `baseresourcelib`. `baseresourcelib` does not import it. This is not a submodule of the client package, and it is not a second GitHub repository for the first public version.

Why that shape:

- The private defaults note already forbids moving HTTP policy into the resource library. An optional extra inside `baseresourcelib` makes that import too easy, and it puts Flask on the client's dependency horizon the moment someone imports the wrong module.
- A second repository repeats the problem `PYTHON312.md` describes: the API package cannot resolve until the resource package is published, and the private tree still points TasksLib at an unversioned git URL. The contract tests already cheat by putting both trees on `PYTHONPATH`.
- The owner keeps both in one workspace and changes them against each other. One pull request can update a schema rule and the view test that locks it.

| | Two distributions, this repo | Second repository |
| --- | --- | --- |
| Versioning | Two `pyproject.toml` versions. The API depends on a range of the client (`baseresourcelib>=0.1,<0.2` once 0.1 exists). They can tag on different days. | Same range, published on PyPI. Closest to today's 0.9.0 client and 0.5.0 API split. |
| Release coupling | A schema break is reviewed with the view that consumes it. Publishing the client wheel still has to happen before the API wheel if the index install is the test. Local tox can install `../` first. | Every contract change is two reviews and a client release before API CI is honest. That delay is what the private migration hit. |
| Dependency direction | API depends on the client. A CI check fails if the client imports the API. | Same direction, harder to see in one diff. |
| Tests | `api/tox.ini` installs the sibling client, then mongomock and fakeredis. No broker. | Same tests, plus a published or git pin. |
| Discoverability | One GitHub project, two pip names, one README section. Someone looking for the HTTP half finds the client it requires. | Easy to miss the pair. Two issue trackers. |

**Proposed** layout for this repository:

```text
pyproject.toml                      # distribution baseresourcelib
src/baseresourcelib/                # client, modes, poll, no Flask
tests/unit/
api/pyproject.toml                  # distribution baseresourceapi
api/src/baseresourceapi/
    __init__.py                     # get_app_and_api, add_api_endpoint
    views.py                        # ResourceView
    marshal.py                      # model_build_obj isolation
    tasks.py                        # save, then call a publisher
api/tests/unit/
api/tox.ini
```

A publisher is a callable the application passes in, `(envelope) -> id`. The first tests use a list. Celery, if anyone still wants it, is an application, not this package.

**Proposed** layout if a second repository is chosen later:

```text
base-resource-api/pyproject.toml    # depends on baseresourcelib from PyPI
base-resource-api/src/baseresourceapi/
```

No `git+ssh` URL. No private package index. Open that repository only after `baseresourcelib` 0.1 is on PyPI and the view tests pass against the released wheel. Until then the sibling tree is the honest build.

Names are proposals. `baseresourceapi` is the placeholder so the package is not called `bsapilib`.

### 6.4 Modernization, specific to this library

**Verified** from its `pyproject.toml` and `PYTHON312.md`. It already requires Python >=3.12, Hatchling, hatch-vcs, Marshmallow `>=4.3.1,<5`, and marshmallow-mongoengine `>=0.31.2,<0.32`. Tox 4 runs unittest and lint. Those are not the work.

What is dated or bound to the private platform:

| Item | Evidence | What to do in the companion |
| --- | --- | --- |
| Marshmallow 4 gaps at the HTTP boundary | Six strict xfails in `test_defaults_contract.py` | Fix them in the client field adapter (PR 3), then delete the xfails here if the API test still applies. Do not patch them only in the view. |
| `datetime.utcnow` | Stdlib audit lists `application.py`, `login.py`, `rest_resources.py`, `redisclient.py` | The audit's rule stands: do not swap in aware datetimes without a test of the existing naive contract. The first slice can avoid new `utcnow()` calls. A sweep of the private modules is not a reason to copy them. |
| PyMongo `>=4.17,<4.18` | `PYTHON312.md`: MongoDB 4.2.12 | Do not copy the cap unless the public package still claims that server. |
| Flask-RESTful `>=0.3.10,<0.4` | `pyproject.toml` | The attached code is written against it. Replacing the view framework was not evaluated. Keep it for the first port. A later replacement is a rewrite, not this modernization. |
| Elasticsearch 7 extra | `pyproject.toml` comment | Leave it out. Tag (d). |
| Private git requirements and hatch-vcs / Jira tags | `pyproject.toml`, `PYTHON312.md` | Same decision as the client. Static versions. Public index. No git URL. |
| Identity TLS and a private CA | `PYTHON312.md` | Stays with the identity client that is not ported. The companion's auth hook does not open that URL. |
| Module-level `taskslib` import | `rest_resources.py` line 33 | The public view must import without `taskslib`. Result storage is a parameter. |

`gunicorn`, `blinker`, `flask-cors`, and `Flask-Limiter` are current enough to keep when the factory is ported. Redis is optional at runtime because the limiter already falls back. Do not add a broker client to the install requires.

This assessment did not run `pip index` and did not install the Flask stack.

### 6.5 Where it sits in the plan

PR 8 in section 4 is the first HTTP slice. It starts after PR 7 so the client package installs, the schema contract is the Marshmallow 4 one, and `run_task` / `poll_task` exist for the view tests to target.

Order inside that later work, each still its own review:

1. Factory, health check, registration, and CRUD view. Tests from `test_application_factory.py` and the non-task, non-snapshot parts of `test_rest_resource_contract.py`, rewritten onto `baseresourceapi` and mongomock.
2. Marshal helper and the GET/PUT default rules from the defaults note. Reuse the client's pagination schema.
3. Task view as save-then-call-publisher, with a fake publisher. Assert the row remains when the publisher raises, and that GET returns the stored response. Do not port `login.py` or `rabbitmq.py` to make this pass.

The client PRs 1 through 7 do not gain a Flask dependency while this waits. If the HTTP package is rejected, those PRs are unchanged.

**Not verified:** no public importer of `bsapilib` was searched. No statement here says the private package can be published as-is under the MIT license. The employer strings in section 3 apply to every file this section marks (c).

