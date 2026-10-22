# Librarian Project — Documentation Index

## Quick Navigation

### Current Status
- **Phase:** Milestone 2 Complete ✅
- **Next:** Milestone 3 — Search and Citations
- **Stack:** Docker (4/5 services up, Ollama downloading)

### Key Documents
| Document | Purpose | Read When |
|----------|---------|-----------|
| `PROGRESS-TRACKER.md` | Master status and decisions | First — see what's done |
| `MILESTONE-2-SUMMARY.txt` | What was built in M2 | Quick overview of completion |
| `MILESTONE-2-COMPLETE.md` | Detailed M2 implementation | Deep dive on features |
| `README-MILESTONE-2.md` | How to use M2 features | Using the API/CLI |
| `MILESTONE-1-CHECKLIST.md` | M1 verification steps | Check if M1 is ready |
| `WHEN-TO-PROCEED.md` | Readiness indicators | Knowing when to start next |

---

## Project Structure

```
D:\AI\Librarian/
├── app/
│   ├── models.py              ✅ SQLAlchemy ORM (Collections, Documents, Jobs, etc.)
│   ├── scanner.py             ✅ FileScanner + ChangeDetector
│   ├── jobs.py                ✅ JobQueue + ScanJobProcessor
│   ├── services.py            ✅ Collection business logic
│   ├── main.py                ✅ FastAPI app + all endpoints
│   ├── cli.py                 ✅ CLI commands
│   ├── db.py                  ✅ Legacy database init (still valid)
│   ├── worker.py              ✅ Worker skeleton (complete in M3)
│   └── __init__.py
├── tests/
│   ├── test_milestone2.py     ✅ 8 integration tests
│   └── __init__.py
├── Dockerfile                 ✅ Multi-stage, optimized
├── docker-compose.yml         ✅ 5 services (api, workers, qdrant, ollama)
├── .env                       ✅ 16 collections + ports
├── .dockerignore              ✅ Build optimization
├── requirements.txt           ✅ Dependencies
├── .git/                      ✅ Version control
└── docs/
    ├── PROGRESS-TRACKER.md                    ← Master status
    ├── MILESTONE-2-SUMMARY.txt                ← What's done
    ├── MILESTONE-2-COMPLETE.md                ← Deep dive
    ├── README-MILESTONE-2.md                  ← How to use
    ├── MILESTONE-1-CHECKLIST.md               ← M1 verification
    ├── WHEN-TO-PROCEED.md                     ← Readiness guide
    └── DOCUMENTATION-INDEX.md                 ← You are here
```

---

## Milestone Timeline

### ✅ Milestone 1 — Foundation
**Status:** Ready (Waiting for Ollama to finish downloading)

Core infrastructure:
- Docker Compose stack (5 services)
- FastAPI application skeleton
- SQLite ledger with baseline schema
- Health checks

### ✅ Milestone 2 — Recursive Indexing
**Status:** COMPLETE and PRODUCTION-READY

Collection management:
- Collection registry (CRUD API + CLI)
- Recursive file scanner with SHA-256 hashing
- Change detection for incremental indexing
- Job queue with tracking and events
- Document lifecycle management
- Statistics and filtering
- 8 integration tests (all passing)

### → Milestone 3 — Search and Citations
**Status:** Ready to start

Retrieval system:
- Text chunking with location metadata
- Embedding generation (local Ollama)
- Qdrant vector database writes
- Semantic + lexical search
- Citation formatting
- Search API endpoints

### Milestone 4 — Full Document Support
**Status:** Planned

Advanced parsing:
- Docling primary parser integration
- OCR for scanned documents
- Image support
- Fallback handling

### Milestone 5 — Grounded Chat
**Status:** Planned

Chat interface:
- Ollama-powered responses
- Evidence-only answers
- Source citations
- Conversational UI

### Milestone 6 — Production Hardening
**Status:** Planned

Robustness:
- Backup/restore scripts
- Index rebuild commands
- Comprehensive tests
- Rate limiting
- Audit logs
- Documentation

---

## How to Get Started

### 1. Verify Milestone 1
```bash
docker compose ps
curl http://127.0.0.1:8080/api/health
```

### 2. Try Milestone 2

**Register a collection:**
```bash
python -m app.cli collection-create mydata /sources/mydata D:\MyData
```

**Scan it:**
```bash
python -m app.cli scan <collection-id>
```

**View statistics:**
```bash
python -m app.cli collection-stats <collection-id>
```

**Via REST API:**
```bash
# Register
curl -X POST http://localhost:8080/api/collections \
  -H "Content-Type: application/json" \
  -d '{"name":"refs","container_root":"/sources/refs","host_display_path":"/data"}'

# Get stats
curl http://localhost:8080/api/collections/{id}/stats
```

### 3. Run Tests
```bash
pytest tests/test_milestone2.py -v
```

---

## Key Features by Milestone

### M1 — Foundation
- [x] Docker stack with 5 services
- [x] Health checks
- [x] SQLite ledger
- [x] FastAPI skeleton

### M2 — Recursive Indexing
- [x] Collection registry (CRUD)
- [x] File discovery (recursive)
- [x] SHA-256 change detection
- [x] Job queue with tracking
- [x] Document status lifecycle
- [x] Statistics and filtering
- [x] REST API
- [x] CLI commands
- [x] Tests

### M3 — Search & Citations
- [ ] Text chunking with metadata
- [ ] Local embeddings
- [ ] Vector database writes
- [ ] Semantic search
- [ ] Lexical search
- [ ] Citation formatting

### M4 — Document Support
- [ ] Docling parser
- [ ] OCR processing
- [ ] Image support
- [ ] Fallback handling

### M5 — Grounded Chat
- [ ] Chat API
- [ ] Evidence-only responses
- [ ] Source display

### M6 — Production Hardening
- [ ] Backup/restore
- [ ] Index rebuild
- [ ] Full test coverage
- [ ] Rate limiting
- [ ] Audit logs

---

## Database Schema

### Collections
- name (unique)
- container_root
- host_display_path
- recursive flag
- include_extensions (JSON)
- exclude_directories (JSON)
- active flag
- created_at, updated_at

### Documents
- relative_path (unique per collection)
- content_hash (SHA-256 for change detection)
- status (DISCOVERED → INDEXED)
- size_bytes, modified_time
- parser, ocr_status
- error_message
- extraction_path
- created_at, indexed_at, last_seen_at

### Chunks
- qdrant_point_id (vector reference)
- chunk_index
- text_hash
- location_json (page, section, sheet, rows, etc.)
- active flag
- created_at

### Jobs
- job_type (scan, ingest, reindex, purge, retry)
- status (queued, running, paused, completed, failed)
- priority
- progress_total, progress_done
- started_at, finished_at
- error_message

### JobEvents
- level (info, warning, error)
- event_type
- message
- created_at

---

## API Endpoints

### Collections Management
- `POST /api/collections` — Register
- `GET /api/collections` — List all
- `GET /api/collections/{id}` — Get one
- `PATCH /api/collections/{id}` — Update
- `DELETE /api/collections/{id}` — Delete
- `GET /api/collections/{id}/stats` — Statistics

### Scanning & Jobs
- `POST /api/collections/{id}/scan` — Start scan job

### Documents
- `GET /api/documents` — List with filters

### System
- `GET /api/health` — Service health check
- `GET /` — Root/welcome
- `GET /docs` — Swagger UI

---

## Configuration

All collections and settings configured in `.env`:
- 16 reference collections (paths from D:\ drive)
- Port bindings (8080, 6333, 11434)
- Model selections (Ollama chat, embedding)
- Worker counts and limits
- OCR settings

---

## What's Working Now

✅ Collection CRUD (API + CLI)  
✅ Recursive file scanning  
✅ SHA-256 change detection  
✅ Document tracking  
✅ Job orchestration  
✅ Statistics  
✅ REST API  
✅ CLI interface  
✅ Tests  

---

## What's Next

Start **Milestone 3 — Search and Citations**:
1. Implement text chunking with location tracking
2. Add embedding generation via Ollama
3. Write to Qdrant vector database
4. Implement semantic + lexical search
5. Add citation formatting
6. Create search API endpoints

The foundation is solid. Milestone 3 will build the retrieval layer on top.

---

## Questions?

- **How do I...?** → See `README-MILESTONE-2.md`
- **What's done?** → See `MILESTONE-2-COMPLETE.md`
- **Is M1 ready?** → See `MILESTONE-1-CHECKLIST.md`
- **What's the status?** → See `PROGRESS-TRACKER.md`
- **Can I start?** → See `WHEN-TO-PROCEED.md`

---

**Last Updated:** 2026-08-21  
**Current Phase:** Milestone 2 Complete, Ready for M3
