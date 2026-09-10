REQUIREMENTS: UNIVERSAL CONTROLLER TO SERVICENOW TABLE SYNCHRONIZATION
Date: 2026-09-10
Audience: Coding agent building a Stonebranch Universal Extension

1. BUILD OBJECTIVE

Build a Python Universal Extension that reads Universal Controller (UAC) data
through REST APIs and updates dedicated ServiceNow Decision Tables and existing
customer/account tables. Users must discover and select ServiceNow tables through
Universal Controller's native Dynamic Choice fields on the Universal Task form.

The user explicitly confirmed that "Customer Tables" means existing customer/
account tables. Do not reinterpret this as a request to create custom tables.
Existing related tables may be used when they already hold customer-specific
Controller inventory. Discover actual table and field names from the instance.

Required source datasets: agents, loaded calendars, scripts, and SAP/ABAP jobs
defined in Controller. Business Services are also required for discovery and
optional customer association. Allow additional source collectors without
redesigning the synchronization engine.

Work within this servicenow/ directory, follow applicable AGENTS.md instructions,
and reuse existing implementation here if present. Deliver working UE source,
template, import package, mapping examples, documentation, and tests.
This requirements document itself does not authorize live deployment or writes.

2. SCOPE AND ASSUMPTIONS

- Synchronization direction is UAC -> ServiceNow. Controller access is read-only.
- "Loaded calendars" means calendar definitions currently available in UAC,
  including configured business/custom days when requested. Calculating future
  schedules or extracting SAP factory calendars is not assumed.
- "ABAP jobs" means UAC SAP task definitions and their ABAP steps. Discovering all
  jobs directly from SAP or collecting runtime history requires a separate source
  specification and, for history, a time range.
- Target tables, Decision Tables, and destination columns already exist. Report
  missing schema; do not silently create tables, columns, or customer accounts.
- Default writes update existing records. Explicit configuration may allow
  creation of missing integration-owned decision rows or related inventory rows.
  Customer/account master record creation is outside this version's scope.
- Do not delete records, deactivate customers, launch jobs, execute scripts,
  modify calendars, or alter unrelated decision rules.
- Use Python 3.11 and a supported UE starter unless the selected Agent/SDK requires
  a different runtime. Verify compatibility before packaging.

3. USER WORKFLOW AND TASK ACTIONS

1) Select the Universal Agent that will execute the extension and discovery.
2) Configure UAC and ServiceNow connections using Controller credential fields.
3) Select a source dataset and optionally restrict it by Business Service,
   supported filters, or a dynamically selected source object.
4) Select target mode: Customer/Account Tables, Decision Tables, or Both.
5) Load ServiceNow targets using native Dynamic Choice lookups. Select the tables
   and discover their fields, decision inputs/results, and account records.
6) Configure source-to-destination mappings and explicit customer association.
7) Run Preview to inspect proposed changes without writing them.
8) Run Synchronize manually or through normal Controller scheduling/workflows.

Implement these task actions:
- Validate Configuration: verify connectivity, readable sources, target existence,
  mappings, field compatibility, account matching, and Decision Table capabilities.
  Do not test write access by changing records; report unverified permissions.
- Preview: collect current data and report proposed changes and mapping errors.
- Synchronize: collect current data, validate it, apply configured changes, and
  verify the resulting records.

One task may synchronize one source dataset to one or both target modes. Use
multiple task definitions for different datasets/dedicated tables. Do not require
a separate web application or browser automation.

4. NATIVE DYNAMIC CHOICE FIELDS

Use native Choice fields with Dynamic Choice enabled and UE SDK handlers such as
@dynamic_choice_command("customer_table"). Handler names must match template
field names and return the installed SDK's supported ExtensionResult format.
These commands run on the selected Agent during task configuration. [1]

Required dynamic discovery:
- customer_table: eligible existing customer/account and related target tables,
  fetched from ServiceNow REST metadata within the configured target scope.
- decision_table: actual Decision Table definitions with stable unique IDs.
- target_field: columns of the selected customer/related table, including inherited
  columns; expose type/reference information where useful.
- decision_input and decision_result: the selected decision's input/result schema.
- customer_record: existing accounts for explicit single-account selection.
- business_service: Business Services retrieved from UAC.
- source_object: UAC objects for the selected dataset when scope is Selected
  Object. All/Filtered scopes must collect the current objects at runtime.

Declare every handler's required dependent fields: URLs, authentication settings,
credentials, target/source selections, and search/filter inputs. Do not assume a
callback receives every task field. Verify credential delivery and variable
resolution during both discovery and task launch.

Use technical table names as table identifiers and ServiceNow sys_id values as
record/decision identifiers. Display readable labels with distinguishing details.
If the SDK accepts strings only, use a documented reversible label/ID format;
do not invent unsupported label/value objects. Reject ambiguous selections.

Discovery must:
- Make actual REST calls; no fixed ServiceNow table list or exported snapshots.
- Support filtering/search and pagination within documented SDK result limits.
- Indicate result truncation and require a narrower filter when limits are reached.
- Distinguish no matches from authentication, permission, network, and API errors.
- Perform no ServiceNow writes or UAC mutations.
- Reject stale choices after dependent settings change and revalidate saved IDs
  at execution time. Do not rely on in-memory lookup state from an earlier callback.

5. UNIVERSAL CONTROLLER REST SOURCES

Verify request methods, schemas, accepted filter values, and response shapes
against the target Controller's /resources/openapi.json before live calls.
The workspace snapshot ../openapi.json identifies itself as UAC 8.0.0.0. [2]
It documents these operations relative to the configured Controller base URL:

Dataset              Operation
Agents               GET /resources/agent/list
Agent filtering      GET /resources/agent/listadv
Calendars            GET /resources/calendar/list
Calendar details     GET /resources/calendar?calendarid=<id>
Calendar custom days GET /resources/calendar/customdays?calendarid=<id>
Scripts              GET /resources/script/list
Business Services    GET /resources/businessservice/list
Task discovery       POST /resources/task/list with TaskQueryFilterWsData JSON
Advanced task list   GET /resources/task/listadv with documented query parameters
Task details         GET /resources/task?taskid=<id>

Do not assume GET for /resources/task/list: this snapshot specifies POST.
Its SAP task schema is TaskSapWsData, described as type=taskSap. Verify the accepted
SAP filter representation for the chosen list endpoint; display labels and
serialized type values may differ. Respect configured URL context paths; do not
append /uc blindly.

Collect these logical attributes when exposed:
- All datasets: stable source ID, name, description, source type, Controller
  identity, Business Service associations, and source update time if available.
- Agents: host name, OS/type, version, current status, suspended/decommissioned
  state. Exclude credential-related response fields.
- Calendars: business days, custom/local custom day configuration, and requested
  details. Keep dates distinct from timestamps.
- Scripts: scriptName, scriptType, description, update metadata. Exclude script
  bodies by default; never execute scripts or resolve their embedded variables.
- SAP/ABAP jobs: UAC task ID/name, jobName where configured, Agent/connection
  reference, and ABAP step ID/order, programName, variantName where present.
  Read task details if lists omit jobSteps and preserve multiple ABAP steps.
  Do not label every SAP task as ABAP, invent missing program names, or confuse
  a task definition ID with a runtime SAP job ID.

Use explicit source field allowlists and normalize response shapes. Never export
complete task, Agent, script, or SAP connection responses. Preserve unavailable
values and report them without inventing data. Use only pagination/filter
parameters supported by each UAC endpoint; several snapshot list endpoints do
not define pagination parameters.

6. SERVICENOW CUSTOMER/ACCOUNT TABLES

Use the Table API for record retrieval and partial updates:
GET /api/now/table/{tableName}
GET /api/now/table/{tableName}/{sys_id}
PATCH /api/now/table/{tableName}/{sys_id}
Use POST only for explicitly enabled creation of eligible related records. [3]

Discover table metadata through sys_db_object and field metadata through
sys_dictionary where permitted. Resolve inheritance and validate identifiers.
If metadata access is restricted, support an authenticated scoped REST discovery
endpoint returning the authorized catalog. Choices must still be fetched over
REST. Metadata visibility alone does not prove write permission.

Actual table names and relationships depend on the ServiceNow instance.
customer_account is an example CSM table, not a hardcoded target. Check installed
applications, table access, and effective record/field ACLs. [4]

Every mapping must specify:
- Exact target table and eligible destination fields.
- Existing account sys_id, or a configured unique external-key lookup.
- For multiple customers, an explicit association such as UAC Business Service ID
  -> ServiceNow account sys_id. Never infer customer ownership from similar names.
- Related inventory match key and customer reference field, when applicable.
- Cardinality: aggregate per account, or one related record per source object.
- Data conversions and behavior for missing source values.

Handle many Agents/jobs per account deliberately: aggregate into appropriate
existing fields or use existing related inventory records. Never repeatedly
overwrite one scalar account field with different source records. If existing
fields cannot represent the data, report the schema gap; do not put inventory
into unrelated fields such as account name or contact details.

Zero or multiple account matches is a mapping error, never permission to create
an account or update all matches. Objects in multiple Business Services require
an explicit association policy; do not send data to every customer by default.

7. DECISION TABLE UPDATES

Decision Tables contain definitions and related inputs, conditions, answers, and
decisions. Updating only a sys_decision header does not synchronize its rules.
ServiceNow documents sn_dt.DecisionTableAPI as a server-side API. [5]

Verify the supported REST operations in the target release. Where a suitable REST
management API is absent, deliver a narrowly scoped Scripted REST API adapter
calling supported server-side DecisionTableAPI methods. [6] Do not present
JavaScript methods as public REST endpoints or invent a standard
/api/now/decisiontable CRUD API. Document adapter URLs as integration-specific
endpoints and include their installation prerequisites.

Support discovery/schema reads and updates to selected existing decision rows
and mapped condition/answer values. Creating missing managed rows is opt-in.
Verify the release's row/answer methods: an evaluation endpoint or a table
metadata update alone does not satisfy this requirement.

Require a decision mapping containing:
- Decision Table sys_id and existing input/result identifiers.
- Deterministic managed row key, including customer/source identity as applicable,
  with a documented way to store or resolve it using the existing schema.
- Input conditions/operators and source-to-result mappings with data types.
- Explicit row order/priority and preservation of existing default answers.
- Account association and behavior for multiple ABAP steps or Agent choices.

Do not invent business rules. Mapping a customer and environment to an Agent,
calendar, script, or ABAP program requires configured input conditions and result
fields. Examples must be marked as placeholders.

Preserve unrelated/manual rules and precedence. Follow the release's supported
draft/version/publication lifecycle where applicable and make publication an
explicit configured behavior. Verify changed rows and evaluate representative
matching/nonmatching inputs during authorized acceptance tests.
If an operation is unsupported, identify the limitation; do not fall back to
arbitrary writes across undocumented internal decision tables.

8. CONFIGURATION AND MAPPINGS

Provide native task fields for action, target mode, source dataset/scope, UAC
URL/credential, ServiceNow URL/authentication/credential, Controller identity,
dynamic selections, mappings, request timeouts, and page/result limits.
Show and require fields according to the selected action and mode.

Use documented versioned JSON mappings in a native multiline field or supported
attached configuration. Validate them before any target writes. Support field
copy, constants, explicit enum/status translation, typed conversion, reference
resolution, and deterministic aggregation. Never execute arbitrary Python or
JavaScript from a mapping.

Supply example mappings for all four required datasets and both target modes.
Mark unverified instance names, columns, and IDs as placeholders. Explain the
required existing columns and account associations in each example.

Defaults:
- Action: Preview.
- Missing customer account: error; never create.
- Missing managed related/decision row: error; creation opt-in only.
- Source object absent on later run: retain target record.
- Source field absent: leave destination unchanged; null clearing must be explicit.
- Script content: excluded.
- TLS verification: enabled; support a configured trusted CA bundle.

9. CORRECTNESS, SECURITY, AND ERROR HANDLING

- Identity: Controller identity + source type + stable source ID, qualified by
  customer and step identity where needed. Names alone are not stable keys.
- Read required source pages and validate the complete plan before writing.
  Incomplete retrieval must never be treated as an empty inventory.
- Compare normalized values and patch only changed mapped fields. Repeating an
  unchanged run must produce no duplicate records or content writes.
- Preserve fields maintained by ServiceNow/other integrations. Resolve references
  to real sys_id values and validate destination types, choices, and lengths.
- Protect against concurrent edits with supported conflict checks or documented
  serialization. A read followed by a write is not an atomic transaction.
- Use bounded ServiceNow pages, deterministic ordering, and documented continuation
  information. A short/empty page may reflect ACL filtering after page limits;
  do not silently treat it as proof of exhaustion. [3]
- Retry transient read failures, 429s, and temporary server errors with bounded
  backoff, timeouts, and Retry-After where provided. Fail clearly for bad
  credentials, missing permissions, or invalid schema.
- After an uncertain create response, reconcile by the stable key before retrying;
  reject duplicates. Apply equivalent safeguards to Decision Table adapter calls.
- Preview and Synchronize share collection/normalization/planning logic.
  Synchronize revalidates current state instead of blindly applying an old preview.
- Report partial writes and completed operations accurately. Do not claim rollback
  across independent ServiceNow requests or Both targets. Stop dependent work;
  reruns must converge without duplicate creation.
- Use UAC credential objects and separate configured service identities.
  Support authentication appropriate to the actual instances and document
  Basic/OAuth setup as applicable; do not invent an OAuth grant.
- Keep passwords, tokens, authorization headers, script bodies, and full customer
  payloads out of logs/output. Emit only sanitized response diagnostics.

10. OUTPUT AND ACCEPTANCE CRITERIA

Return a readable task summary and structured JSON containing run ID, action,
source dataset, target IDs, start/end times, status, read/matched counts,
planned/actual created and updated counts, unchanged/skipped/failed counts, and
sanitized per-record errors. Distinguish preview counts from completed writes.
Success requires all requested target operations to succeed; partial writes and
configuration/required-source failures must produce a nonzero task result.

Acceptance tests:
AC01 Native Dynamic Choice fields fetch real tables, decisions, and UAC objects,
     honor dependencies, and retain unambiguous selections after saving.
AC02 Discovery, validation, and Preview perform zero writes, including on failure.
AC03 All four source datasets work, including multiple ABAP steps and configured
     calendar custom-day details.
AC04 Only intended customer records and mapped fields change.
AC05 Multiple source objects per account follow aggregation/related-record mappings
     without last-record overwrites or cross-customer data leakage.
AC06 Decision conditions/results change as configured; evaluation returns expected
     answers while unrelated rules, precedence, and defaults remain correct.
AC07 A second unchanged run creates no duplicates and changes nothing. Renaming
     a source object updates its existing match using stable identity.
AC08 Unknown/ambiguous accounts, incompatible fields, stale selections, and missing
     required data are reported before writes for the validated plan.
AC09 Multi-page reads complete correctly; ACL-filtered pages, limits, and failed
     retrieval cannot silently drop records or clear target data.
AC10 Authentication failures, 429s, timeouts, malformed responses, partial writes,
     and uncertain creates produce bounded recovery and accurate results.
AC11 Concurrent edits are detected or serialized; unrelated fields survive.
AC12 Credentials and excluded source/customer content never appear in output.

Provide unit tests and mocked HTTP contract tests for these cases, plus a live
acceptance procedure for an authorized non-production environment. Label evidence
as local/mock/live. For executed live tests, record actual UAC instance IDs and
ServiceNow verification evidence. Missing access is not a passing live test.
Do not perform live writes until authorized for that environment.

11. DELIVERABLES AND INSTANCE-SPECIFIC INPUTS

Deliver:
- UE source, dependencies, native template.json, and import ZIP.
- ServiceNow REST adapter source/install artifact when required, including its
  contract, required roles/ACLs, and supported release information.
- Mapping schema/examples, setup guide, preview/sync examples, and troubleshooting.
- Tests, results, supported feature matrix, and remaining limitations.

Do not invent these deployment/configuration inputs:
- Target UAC/Agent/SDK versions and ServiceNow release/installed applications.
- URLs, credential objects, and authentication configuration.
- Eligible existing customer/account/related tables and destination columns.
- Account association keys or Business Service-to-account mapping.
- Decision Table IDs, conditions, results, row matching, and lifecycle needs.
- Whether creating managed rows or publishing decisions is required.

Continue independent implementation and mock validation while inputs are unknown;
request missing inputs when needed for real mappings or live validation.
Clearly report unsupported Decision Table capabilities. Do not declare the whole
integration complete if only customer/account updates work.

12. REFERENCE MATERIAL

[1] Stonebranch native Dynamic Choice tutorial (verify installed SDK/version):
https://stonebranchdocs.atlassian.net/wiki/spaces/UC75/pages/206404116/Dynamic%2BChoice%2BField

[2] Local UAC 8.0.0.0 snapshot: ../openapi.json
Revalidate against <controller-base-url>/resources/openapi.json.

[3] ServiceNow Table API (select the target release):
https://www.servicenow.com/docs/r/xanadu/api-reference/rest-apis/c_TableAPI.html

[4] ServiceNow CSM Case API, including customer_account references:
https://www.servicenow.com/docs/r/api-reference/rest-apis/case-api.html

[5] ServiceNow DecisionTableAPI - Scoped, Global:
https://www.servicenow.com/docs/r/api-reference/server-api-reference/DecisionTableAPI.html

[6] ServiceNow Scripted REST APIs:
https://www.servicenow.com/docs/r/api-reference/rest-api-explorer/c_CustomWebServices.html

Evidence boundary: this document uses vendor documentation and the local UAC
API snapshot. No live connectivity, permissions, customer mapping, or Decision
Table write capability was tested during requirements drafting.