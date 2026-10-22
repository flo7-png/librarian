# When to Move to Milestone 2

## Quick Status Check

**Run this periodically:**

```powershell
docker compose ps
```

**You're ready for Milestone 2 when ALL these are true:**

### ✅ All 4 containers are running

```powershell
docker compose ps
```

Must show:
- `archive_qdrant` — `Up`
- `archive_ollama` — `Up`
- `archive_api` — `Up (healthy)`
- `archive_worker_fast` — `Up`
- `archive_worker_slow` — `Up`

### ✅ API /health returns OK

```powershell
curl http://127.0.0.1:8080/api/health
```

Should return:
```json
{"status": "ok", "qdrant": "ok", "ollama": "ok"}
```

Or `"status": "degraded"` is acceptable if Ollama is still warming up.

### ✅ Browser loads Swagger UI

Open: `http://127.0.0.1:8080/docs`

Should see the FastAPI interactive API documentation.

---

## Current Status

**Ollama is still downloading** (~1.9GB image). 

Check progress:
```powershell
docker compose logs --tail 20 archive_ollama
```

Once you see:
```
Message: Successfully pulled model
```

Then run:
```powershell
curl http://127.0.0.1:8080/api/health
```

If it returns `"status": "ok"` for all three services → **Milestone 1 is done.**

---

## How Long Will This Take?

- **Download**: 5-30 minutes (depends on bandwidth)
- **Extract & start**: 2-5 minutes
- **Containers stabilize**: 1-2 minutes

Total: **10-40 minutes** from initial startup.

---

## When All Checks Pass

Message me:
> Ready for Milestone 2

And we'll proceed with:
- Collection registry implementation
- Recursive file scanner
- SHA-256 change detection
- Job queue for indexing
