# Milestone 1 Completion Checklist

Run these commands to verify each criterion. **All 8 must pass before moving to Milestone 2.**

## Criterion 1: Four containers running
```powershell
docker compose ps
```
**Expected output:**
- `archive_qdrant` — status: Up
- `archive_ollama` — status: Up
- `archive_api` — status: Up (healthy)
- `archive_worker_fast` — status: Up
- `archive_worker_slow` — status: Up

**Status:** ⬜ PENDING

---

## Criterion 2: API /health endpoint returns 200 with both services OK
```powershell
curl http://127.0.0.1:8080/api/health
```
**Expected output:**
```json
{
  "status": "ok",
  "qdrant": "ok",
  "ollama": "ok"
}
```

**Status:** ⬜ PENDING

---

## Criterion 3: Qdrant is reachable at port 6333
```powershell
curl http://127.0.0.1:6333/health
```
**Expected output:** HTTP 200 (Qdrant health response)

**Status:** ⬜ PENDING

---

## Criterion 4: Ollama is reachable at port 11434
```powershell
curl http://127.0.0.1:11434/api/tags
```
**Expected output:** HTTP 200 with JSON list of models (or empty if no models pulled yet)

**Status:** ⬜ PENDING

---

## Criterion 5: API container has health check passing
```powershell
docker inspect archive_api | Select-String -Pattern "Health"
```
**Expected output:** Should show `"Status": "healthy"` (after 10s start-period)

**Status:** ⬜ PENDING

---

## Criterion 6: SQLite ledger exists and has baseline tables
```powershell
docker exec archive_api python -m app.db
```
**Expected output:** No errors; database initialized at `/app-data/librarian.db`

**Status:** ⬜ PENDING

---

## Criterion 7: Browser loads the root endpoint without errors
Open: `http://127.0.0.1:8080`

**Expected output:**
```json
{"message": "Librarian API is running. Visit /docs for API documentation."}
```
Or visit `http://127.0.0.1:8080/docs` for interactive Swagger UI.

**Status:** ⬜ PENDING

---

## Criterion 8: Docker Compose network is up
```powershell
docker network inspect archive_net
```
**Expected output:** Network exists with all 4+ containers attached

**Status:** ⬜ PENDING

---

## When ALL 8 are ✅ COMPLETE:

**Milestone 1 is done.** Proceed to **Milestone 2 — Recursive Indexing.**

Run this command to see what's next:
```powershell
cd D:\AI\Librarian
# Message me: "Ready for Milestone 2"
```

---

## Troubleshooting

### Containers not starting?
```powershell
docker compose logs --tail 100
```

### API won't reach Qdrant/Ollama?
```powershell
docker inspect archive_api | Select-String "IPAddress"
docker network inspect archive_net
```

### Port conflicts?
```powershell
netstat -ano | findstr ":8080\|:6333\|:11434"
```

### Rebuild from scratch?
```powershell
cd D:\AI\Librarian
docker compose down -v
docker compose up -d --build
```
