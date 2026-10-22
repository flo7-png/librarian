# Local Archive AI — Podman Build Specification

## 1\. Objective

Build a fully local, free/open-source document intelligence system that can register one or more root folders, recursively process every supported file in those folders and their subfolders, incrementally synchronize changes, and answer questions from retrieved evidence with precise source citations.

The user should only need to provide file locations, choose a collection name, and start indexing. The system must keep original files untouched and should remain usable on ordinary desktop hardware by processing work in controlled background batches.

## 2\. Non-negotiable requirements

* Run locally with Podman and Podman Compose; no Docker daemon dependency.
* Use free/open-source components with permissive licenses where practical.
* Do not require cloud APIs, hosted databases, subscriptions, accounts, telemetry, or remote document upload.
* Treat user folders as read-only source archives.
* Recursively include nested folders by default.
* Never write extraction caches, databases, logs, or generated artifacts inside an indexed source root.
* Support incremental ingestion: scan quickly, hash candidate files, and process only new or changed files.
* Preserve citations down to PDF page, Word heading, spreadsheet sheet/table/row range, or image/OCR location whenever possible.
* Continue on errors; log skipped, unsupported, unreadable, encrypted, and failed files without stopping the job.
* Make all source-backed answers show the source path and location.
* Do not invent facts when evidence is absent. State that no supporting source was retrieved.

## 3\. Product behavior

### 3.1 Register a collection

A collection is a named source root, for example:

```text
Name: references
Host path: /mnt/archive/References
Container mount: /sources/references
Recursive: true
Read-only: true
```

A user should be able to register folders through the web UI and CLI. Registration must validate that:

* The mounted path exists and is readable.
* The path is not an internal application data path.
* The path is mounted read-only in the application containers.
* The selected collection name is unique and filesystem-safe.

### 3.2 Scan and synchronize

The scanner must recursively enumerate files below each registered root. It must:

* Use extension allowlists and content-type detection where available.
* Exclude configurable directory names such as `.git`, `node\_modules`, `\_\_pycache\_\_`, `.trash`, `tmp`, and `cache`.
* Ignore editor temporary files, hidden OS metadata files, and partial downloads by default.
* Not follow directory symlinks unless an administrator enables it.
* Compute a SHA-256 content hash for candidate files.
* Compare the current hash with the SQLite ledger.
* Skip unchanged files.
* Reprocess changed files by marking prior chunks inactive, writing new chunks, then deleting inactive chunks only after the new pipeline succeeds.
* Mark missing files inactive rather than immediately deleting them; purge after a configurable grace period.
* Keep a job/event log with timestamps, errors, retry count, parser selected, elapsed time, and output identifiers.

### 3.3 Ingestion priority

Use separate queues:

* Fast queue: plain text, Markdown, HTML, text-native PDF, DOC/DOCX, PPT/PPTX, XLS/XLSX.
* Slow queue: scanned PDFs, image OCR, PDFs requiring table/layout processing, large files.
* Retry queue: transient errors, unavailable files, and parser failures.

Default worker limits must be conservative:

```text
FAST\_WORKERS=2
SLOW\_WORKERS=1
MAX\_FILE\_SIZE\_MB=500
OCR\_ENABLED=true
```

The UI must allow pausing, resuming, and canceling jobs. Cancellation must leave the original archive untouched and maintain a consistent ledger.

## 4\. Supported document handling

### 4.1 PDF

* Extract text by page.
* Preserve page number and heading/section metadata.
* Detect likely image-only PDFs and place them in the OCR queue.
* Preserve tables and captions when possible.
* Store extraction output in Markdown and structured JSON outside the source archive.

### 4.2 Microsoft Office and OpenDocument files

* DOC/DOCX/ODT: extract headings, paragraphs, lists, tables, title, author/date metadata where available.
* XLS/XLSX/ODS: preserve workbook name, sheet name, table/header context, row ranges, and formula/value representation where practical.
* PPT/PPTX/ODP: preserve slide number, title, notes, and tables.

Do not turn an entire workbook into a single chunk. Spreadsheet chunks must include enough table context to interpret values.

### 4.3 Images and scans

* Support JPG/JPEG, PNG, TIFF/TIF, and optionally WebP.
* Run local OCR using Tesseract or a compatible local engine.
* Store OCR text and confidence, page/image location, filename, and available EXIF metadata.
* Do not make image captioning mandatory in version 1. Make it optional and separately configurable.

### 4.4 Text and structured files

* Support TXT, MD, CSV, JSON, YAML/YML, HTML/HTM, XML, RTF, and EML where parsers support them.
* Keep document structure and headers where meaningful.

### 4.5 Unsupported files

* Record the file and reason in the ledger.
* Display them in the UI with options to retry or exclude.
* Never fail an entire collection scan because of an unsupported file.

## 5\. Architecture

```text
Read-only host folders
        |
        v
Scanner / collection registry
        |
        v
SQLite ledger + job queue
        |
        +---------------------+
        |                     |
        v                     v
Fast extraction workers   OCR/slow workers
(Docling and fallbacks)   (Docling/Tesseract)
        |                     |
        +----------+----------+
                   |
                   v
Structured extraction cache
(Markdown + JSON outside source roots)
                   |
                   v
Structure-aware chunker
                   |
                   v
Local embedding model service
                   |
                   v
Qdrant vector database + metadata payload
                   |
                   v
Hybrid retrieval + reranker + citation builder
                   |
                   v
Local LLM service
                   |
                   v
Web UI and local API
```

## 6\. Required components

### 6.1 Application services

Create these containers:

|Service|Responsibility|Required persistent storage|
|-|-|-|
|`frontend`|Local browser UI for collections, status, search, chat, sources, and settings|None required beyond build assets|
|`api`|REST API, authentication, collection registry, retrieval, citations, chat orchestration|Application data volume|
|`worker-fast`|File scanning, extraction, chunking, and embedding for normal documents|Application data volume|
|`worker-slow`|OCR and resource-intensive extraction tasks|Application data volume|
|`qdrant`|Vector database and payload filtering|Qdrant data volume|
|`ollama`|Local LLM and embedding-model runtime|Ollama models volume|

Use a shared application-data volume for SQLite, job data, extracted artifacts, logs, and temporary processing output. Do not store these files in a source mount.

### 6.2 Suggested implementation

* Backend: Python 3.12, FastAPI, Pydantic, SQLAlchemy/SQLModel, Alembic.
* Background jobs: a SQLite-backed job table and worker processes are acceptable for a single-machine product. Avoid adding Redis unless a real operational need appears.
* Parsing: Docling as primary parser. Use `pypdf`, `python-docx`, `openpyxl`, and/or `LibreOffice` headless as controlled fallbacks where necessary.
* OCR: Tesseract, local only.
* Vector database: Qdrant.
* Embeddings: call Ollama’s local embedding API. Make model name configurable.
* LLM: call Ollama’s local chat API. Make model name configurable.
* Reranking: optional local cross-encoder service/library; use only after baseline retrieval is functional.
* Frontend: React/Vite or a server-rendered FastAPI UI. Prioritize reliability and source inspection over visual complexity.

## 7\. Data model

Use SQLite for the control plane. Qdrant is for retrieval only, not for authoritative job state.

### 7.1 Tables

#### `collections`

```text
id                  UUID / string primary key
name                unique human-readable name
host\_display\_path   text; show to user only
container\_root      text; e.g. /sources/references
recursive           boolean default true
active              boolean default true
include\_extensions  JSON
exclude\_directories JSON
created\_at          timestamp
updated\_at          timestamp
```

#### `documents`

```text
id                  UUID / string primary key
collection\_id       foreign key
relative\_path       text
source\_path         text; container path only
file\_name           text
extension           text
size\_bytes          integer
modified\_time       timestamp/null
content\_hash        text
status              enum: discovered, queued, processing, indexed, failed, skipped, inactive
parser              text/null
ocr\_status          enum: not\_needed, pending, running, complete, failed
error\_message       text/null
extraction\_path     text/null
created\_at          timestamp
indexed\_at          timestamp/null
last\_seen\_at        timestamp
```

Enforce a unique constraint on `(collection\_id, relative\_path)` and track content hash changes.

#### `chunks`

```text
id                  UUID / string primary key
document\_id         foreign key
qdrant\_point\_id     text unique
chunk\_index         integer
text\_hash           text
text\_preview        text
location\_json       JSON; page, section, sheet, rows, slide, image info
active              boolean
created\_at          timestamp
```

#### `jobs`

```text
id                  UUID / string primary key
collection\_id       foreign key/null
job\_type            enum: scan, ingest, reindex, purge, retry
status              enum: queued, running, paused, cancelled, completed, failed
priority            integer
progress\_total      integer
progress\_done       integer
started\_at          timestamp/null
finished\_at         timestamp/null
created\_at          timestamp
error\_message       text/null
```

#### `job\_events`

```text
id                  UUID / string primary key
job\_id              foreign key
document\_id         foreign key/null
level               enum: info, warning, error
event\_type          text
message             text
created\_at          timestamp
```

## 8\. Extraction cache format

For every successful source version, store both Markdown and JSON under application data:

```text
/app-data/extracted/<content-hash>/document.md
/app-data/extracted/<content-hash>/document.json
/app-data/extracted/<content-hash>/manifest.json
```

`manifest.json` must include:

```json
{
  "document\_id": "...",
  "content\_hash": "sha256:...",
  "collection": "references",
  "relative\_path": "Projects/House/2021-budget.xlsx",
  "parser": "docling",
  "parser\_version": "...",
  "ocr\_used": false,
  "created\_at": "..."
}
```

## 9\. Chunking and retrieval

### 9.1 Chunking

* Chunk by document structure first: title, heading, page, table, slide, spreadsheet table/row group.
* Target approximately 300–700 tokens per chunk, with small overlap only where structure does not give a natural boundary.
* Preserve parent context in every chunk: document title, filename, heading, page, sheet, table headers, or slide title.
* Keep tables as coherent units when feasible.
* Store raw chunk text and exact location metadata.
* Never embed only a filename or a fragment without context.

### 9.2 Qdrant payload

Every point payload must include at least:

```json
{
  "collection\_id": "references",
  "document\_id": "...",
  "relative\_path": "Projects/House/2021-budget.xlsx",
  "folder\_path": "Projects/House",
  "source\_path": "/sources/references/Projects/House/2021-budget.xlsx",
  "file\_type": "xlsx",
  "document\_title": "2021 Budget",
  "location": {
    "sheet": "Repairs",
    "row\_start": 18,
    "row\_end": 31
  },
  "content\_hash": "sha256:...",
  "active": true
}
```

### 9.3 Retrieval behavior

* Implement semantic vector search.
* Implement keyword retrieval using a local lexical index, SQLite FTS5, Qdrant sparse vectors, or another fully local mechanism.
* Combine/rerank semantic and lexical results.
* Filter by collection, folder prefix, file type, date, and tags.
* Retrieve a moderate candidate set, rerank, then send only the best evidence to the LLM.
* Default response mode: answer with citations and quote snippets available in the UI.
* Add a “sources only” search mode that does not call an LLM.

### 9.4 Citation format

Responses must cite original source location, for example:

```text
\[References › Projects/House/2021-budget.xlsx — Repairs, rows 18–31]
\[References › Manuals/vehicle.pdf — p. 7, “Maintenance Schedule”]
\[References › Photos/receipt-014.jpg — OCR text]
```

The UI must make citations clickable. A citation should open the source file when the browser/host integration allows it, or at minimum display the source path and relevant extracted text.

## 10\. API requirements

Expose a local API bound to localhost by default.

### Collections

```text
POST   /api/collections
GET    /api/collections
GET    /api/collections/{id}
PATCH  /api/collections/{id}
DELETE /api/collections/{id}
POST   /api/collections/{id}/scan
POST   /api/collections/{id}/sync
POST   /api/collections/{id}/pause
POST   /api/collections/{id}/resume
```

### Documents and jobs

```text
GET    /api/documents?collection\_id=\&status=\&path\_prefix=
GET    /api/documents/{id}
POST   /api/documents/{id}/retry
POST   /api/documents/{id}/exclude
GET    /api/jobs
GET    /api/jobs/{id}
POST   /api/jobs/{id}/cancel
GET    /api/jobs/{id}/events
```

### Search and chat

```text
POST   /api/search
POST   /api/chat
GET    /api/sources/{document\_id}
GET    /api/health
```

`POST /api/search` must return source chunks, scores, metadata, and citations without generation.

`POST /api/chat` must return:

```json
{
  "answer": "...",
  "citations": \[],
  "retrieved\_sources": \[],
  "model": "...",
  "retrieval\_query": "..."
}
```

## 11\. Web UI requirements

Build a local UI with these pages:

* **Dashboard:** collection counts, indexed/failed/queued files, storage use, current worker activity.
* **Collections:** add/edit/disable source roots, exclusions, extension settings, sync controls.
* **Jobs:** live progress, pause/resume/cancel, per-file errors, retry selection.
* **Documents:** browse by collection/folder/status/type and inspect extraction output/chunks.
* **Search:** sources-only search with filters and result previews.
* **Chat:** grounded Q\&A, visible retrieved sources, citations, response settings.
* **Settings:** model selection, embedding model, worker limits, OCR, data locations, retention/purge policy.

The “add collection” flow must state clearly that host folders must first be mounted through `compose.yaml` or the Podman run configuration. The UI cannot safely grant itself host filesystem access.

## 12\. Podman deployment

### 12.1 Repository layout

```text
local-archive-ai/
  README.md
  LICENSE
  compose.yaml
  .env.example
  Makefile
  config/
    collections.example.yaml
  backend/
    Containerfile
    app/
    requirements.txt
    alembic/
  frontend/
    Containerfile
    src/
  worker/
    Containerfile
    app/
  scripts/
    bootstrap.sh
    healthcheck.sh
  docs/
    architecture.md
    operations.md
    backup-restore.md
  tests/
```

### 12.2 Compose requirements

Provide a Podman-compatible `compose.yaml` using named volumes:

```text
archive\_app\_data
archive\_qdrant\_data
archive\_ollama\_models
```

Bind application services to `127.0.0.1` by default. Do not expose Qdrant publicly. Use an internal network for service-to-service traffic.

Source directories must be host bind mounts that are read-only. Example only:

```yaml
services:
  api:
    volumes:
      - type: bind
        source: ${REFERENCES\_PATH}
        target: /sources/references
        read\_only: true
        bind:
          selinux: Z
      - archive\_app\_data:/app-data:Z
```

Use correct Podman SELinux labels (`:Z` or `:z`) when applicable. Document how to remove labels or adapt mount syntax on non-SELinux systems.

The worker containers need the same source mounts and shared application-data volume. The frontend must not need source-folder mounts.

### 12.3 Rootless operation

* Support rootless Podman as the default.
* Avoid privileged containers.
* Avoid host networking unless explicitly selected.
* Run application processes as non-root users inside containers.
* Document required permissions for source folder reads.
* Keep all service ports configurable in `.env`.

### 12.4 Container health checks

Implement health checks for:

* `qdrant`: endpoint/service readiness.
* `ollama`: API readiness.
* `api`: `/api/health` including database and dependency status.
* workers: heartbeat timestamp in SQLite or a health endpoint.

## 13\. Configuration

Provide `.env.example`:

```dotenv
APP\_PORT=8080
QDRANT\_PORT=6333
OLLAMA\_PORT=11434

APP\_DATA\_PATH=./data
REFERENCES\_PATH=/replace/with/your/reference/folder

DEFAULT\_CHAT\_MODEL=replace-with-installed-local-model
DEFAULT\_EMBEDDING\_MODEL=replace-with-installed-local-embedding-model

FAST\_WORKERS=2
SLOW\_WORKERS=1
MAX\_FILE\_SIZE\_MB=500
OCR\_ENABLED=true
SCAN\_INTERVAL\_MINUTES=0
DELETE\_GRACE\_DAYS=30
```

Never hard-code user source paths or model names. Provide scripts or UI instructions to pull/select a local model after deployment.

## 14\. CLI requirements

Provide a CLI executable named `archive-ai` that can be run through Podman Compose or inside the API container:

```bash
archive-ai collections list
archive-ai collections add --name references --root /sources/references --recursive
archive-ai collections scan references
archive-ai collections sync references
archive-ai collections watch references
archive-ai jobs list
archive-ai documents failed --collection references
archive-ai documents retry --collection references
archive-ai search "roof repair costs" --collection references
archive-ai chat "What maintenance does the vehicle manual recommend?" --collection references
```

The CLI must show progress and return meaningful nonzero exit codes on failures.

## 15\. Security and privacy

* Bind all user-facing services to localhost by default.
* Make remote access an explicit, documented opt-in with authentication and TLS via a reverse proxy.
* Keep source mounts read-only.
* Do not execute macros, embedded scripts, or arbitrary document content.
* Disable network access for parsing/extraction workers after images/models/dependencies are installed if practical.
* Log no raw document text by default; logs should contain document IDs/paths and error details only.
* Store secrets only in environment variables or a local secrets mechanism; do not commit them.
* Provide a local admin password option if the UI is accessible beyond localhost.

## 16\. Backup and recovery

Document a backup process for:

* SQLite ledger and application configuration.
* Qdrant storage volume.
* Extraction cache.
* Ollama model volume only if desired; it can be recreated by re-pulling models.

The original archive is not copied, modified, or treated as application-owned data.

Provide a restore procedure and a `rebuild-index` command that can recreate Qdrant from cached extraction data or, if necessary, reprocess source folders.

## 17\. Observability and quality controls

Provide:

* Collection-level counts: discovered, indexed, unchanged, failed, skipped, inactive.
* Per-job progress and estimated remaining work where possible.
* Error taxonomy: permission denied, unsupported type, file too large, corrupted file, encrypted file, parser error, OCR error, embedding error, Qdrant error.
* Retrieval inspection: show query, filters, candidate sources, reranking score, selected context, and final citations.
* A small seeded test corpus and automated tests for recursive discovery, duplicate detection, changed-file reindexing, deleted-file grace handling, and citation preservation.

## 18\. Acceptance criteria

The product is production-ready for a single local user when all of the following work:

1. A user edits `.env`, replacing `REFERENCES\_PATH` with an existing host folder path.
2. `podman compose up -d --build` starts the stack rootlessly.
3. The UI opens locally and reports healthy API, Qdrant, and Ollama services.
4. The user can register `/sources/references` as a recursive collection.
5. The system discovers supported files in nested folders without changing the originals.
6. A first index job can be paused, resumed, and canceled safely.
7. A subsequent sync skips unchanged files and processes only new/changed files.
8. A changed file replaces its prior active chunks only after successful processing.
9. A deleted file is marked inactive and is not immediately purged.
10. Search results can be filtered to a collection and folder prefix.
11. A chat answer based on archive material includes clickable citations with file path and page/sheet/row or equivalent location.
12. The UI exposes failed files and supports retries.
13. The entire stack runs without external cloud services after local models have been installed.
14. Backup, restore, and full index rebuild are documented and tested.

## 19\. Build milestones

### Milestone 1: Foundation

* Create repository, licensing, Compose stack, rootless Podman documentation, health checks, API skeleton, SQLite migrations, and Qdrant/Ollama integration.
* Implement one manually configured read-only source mount.

### Milestone 2: Recursive indexing

* Add collection registry, recursive scanner, allow/deny rules, SHA-256 ledger, basic job queue, fast worker, and UI job status.
* Support TXT, Markdown, PDF text extraction, DOCX, and XLSX.

### Milestone 3: Search and citations

* Add structured chunking, embeddings, Qdrant writes, lexical retrieval, semantic retrieval, metadata filters, sources-only search, and citation formatting.

### Milestone 4: Full document support

* Integrate Docling as primary parser, OCR queue, image support, Office/PDF fallback logic, extraction-cache inspection, failure recovery, and resource controls.

### Milestone 5: Grounded chat

* Add Ollama chat orchestration, evidence-only prompt policy, citations, retrieved-source display, and conversational UI.

### Milestone 6: Production hardening

* Add backup/restore scripts, index rebuild, comprehensive tests, rate/resource limits, audit logs, documentation, sample configuration, and release packaging.

## 20\. Definition of done

Deliver a repository that includes:

* A complete Podman-compatible Compose deployment.
* Containerfiles for custom services.
* Clear README with a five-minute local start path.
* `.env.example` with source-folder configuration.
* Read-only recursive source mounts demonstrated for at least one folder.
* Web UI, API, CLI, workers, SQLite ledger, extraction cache, Qdrant integration, and Ollama integration.
* Test coverage for the acceptance criteria.
* Operational documentation for maintenance, backups, restoration, index rebuilds, and adding additional mounted source folders.
* No paid service or cloud account required for normal operation.

## 21\. User quick start target

The final documentation should allow this flow:

```bash
cp .env.example .env
# Edit .env and set REFERENCES\_PATH to the folder to index.
podman compose up -d --build
# Open http://127.0.0.1:8080
# Register collection: references -> /sources/references
# Click “Scan and index.”
```

After setup, the user should not have to manually upload documents. Adding or editing files under the selected root or any nested subfolder should be handled by the next sync or optional folder watcher.

