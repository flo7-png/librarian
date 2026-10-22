# Librarian — Build Plan

**What this is:** A local-first document intelligence system. It scans your
reference folders on D:\, extracts and indexes their contents, and lets you
search and ask grounded questions against them — citations included, nothing
sent to the cloud.

**Home location:** `D:\AI\Librarian`
**Runtime:** Docker Desktop, WSL2 backend
**Built from:** `local-archive-ai-podman-build-spec.md` (adapted from Podman to Docker)

---

## Decisions already locked in

| Decision | Choice | Why |
|---|---|---|
| Container engine | Docker Desktop, WSL2 backend | Switched from Podman — simpler GPU passthrough, native Windows path support in bind mounts |
| LLM engine | Ollama, containerized | Model reuse via bind mount, single-stack lifecycle — GPU passthrough works fine containerized |
| GPU access | Docker Desktop's built-in NVIDIA GPU-PV | No manual toolkit install needed inside a VM — just `--gpus all` |
| Existing Ollama models | Bind-mounted in from your Windows model store | No re-downloading models you already have |
| Docling (document parser) | Editable install, bind-mounted from `D:\AI\GitHub\Starred Repositories\docling` | `git pull` on the host updates it — no container rebuild needed |
| Source folders | 16 reference collections (see below) | Registered once the scanner exists (Milestone 2) |

**Reference collections to register:**
`D:\References`, `D:\US Army\Lean Six Sigma`, `D:\US Army\1 TSC`, `D:\US Army\Admin`,
`D:\US Army\Army`, `D:\US Army\Engineer Smartbook`, `D:\US Army\Fort Hood`,
`D:\US Army\From USACE 23Sep24`, `D:\TRC Companies`, `D:\USACE TAFB`,
`D:\Old Hard Drive 1\COTR`, `D:\Google Drive`, `D:\Fernley NV`, `D:\Books`,
`D:\OneDrive`, `D:\OneDrive - East Carolina University`

**⚠️ Before Milestone 2:** `D:\OneDrive`, `D:\OneDrive - East Carolina University`,
and `D:\Google Drive` (if using Stream mode) must have every file fully
downloaded/hydrated locally — "Files On-Demand" placeholder files are not
reliably readable from inside a container. In Windows Explorer, right-click
each folder → **Always keep on this device**, and let it finish.

**Note on Docker Desktop licensing:** free for personal use and small
business. A paid subscription is required only for companies over 250
employees or $10M annual revenue — doesn't affect this build, just flagging
it against the "stay free/open-source" priority, since Docker Desktop itself
isn't fully open-source the way Podman is.

---

## Still needed from you before Milestone 1 can be finalized

Run these once and hand back the output — everything else in Milestone 1 can
start without them, but GPU wiring and resource limits get set from this data:

**PowerShell:**
```
docker --version
docker info
Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM
systeminfo | findstr /C:"Total Physical Memory"
Get-PSDrive D
ollama list
```

**Also confirm in Docker Desktop:**
- Settings → Resources → WSL Integration — confirm the backend is enabled
- Settings → Resources → File sharing — confirm your D: drive is shared/enabled
- Verify GPU access:
```
docker run --rm -it --gpus=all nvcr.io/nvidia/k8s/cuda-sample:nbody nbody -gpu -benchmark
```

---

## Milestone 1 — Foundation (start here)

**Goal:** Prove the stack runs. One folder mounted, health checks passing,
nothing indexed yet.

### Step 1 — Create the project folder structure
Open PowerShell and run:
```
mkdir D:\AI\Librarian
cd D:\AI\Librarian
mkdir app, app\api, app\frontend, app\worker, data, data\cache, sources, docs
```
This creates the skeleton. `app\` holds the code for each service, `data\`
holds the SQLite ledger and extraction cache, `sources\` is where your
reference folders get mounted read-only.

### Step 2 — Initialize version control
```
git init
```
This turns the folder into a Git repository so changes are tracked and
nothing is lost. If you don't have Git installed, this is the point to grab
it (free, from git-scm.com) — everything else in this plan works without it,
but you'll want history once real code exists.

### Step 3 — Add the environment file
I'll hand you a `.env.example` with one variable to start:
```
REFERENCES_PATH=D:\References
```
Copy it to `.env` and this becomes your first manually-mounted source folder,
per the spec's Milestone 1 scope (one folder, proving the pipeline — the
other 15 register in Milestone 2).

### Step 4 — Write the Compose stack
I'll build `compose.yaml` defining four services:
- **api** — the backend, built from a Dockerfile I write
- **frontend** — the web UI, built from a Dockerfile I write
- **qdrant** — the vector database (official image, no changes needed)
- **ollama** — the local LLM engine (official image, GPU reservation wired in
  once your diagnostics come back — Docker Compose uses
  `deploy.resources.reservations.devices` with `capabilities: [gpu]`)

### Step 5 — Write the API skeleton
A minimal backend with one endpoint: `/health`, returning "ok" once Qdrant
and Ollama are both reachable. This is the thing Milestone 1 is actually
proving — that all four containers can start and talk to each other.

### Step 6 — Write the SQLite ledger skeleton
An empty database file with the baseline tables (files, jobs, collections)
created but unused — the scanner that populates them arrives in Milestone 2.

### Step 7 — Build and start the stack
```
docker compose up -d --build
```
This builds your two custom containers and starts all four. First run takes
a while — it's downloading the Qdrant and Ollama base images.

### Step 8 — Verify it worked
- Open `http://127.0.0.1:8080` in a browser — you should see a bare page,
  not an error.
- Check `docker ps` — four containers should show as running.
- Check the `/health` endpoint reports Qdrant and Ollama both reachable.

**Milestone 1 is done when all of the above is green.** That's the whole
goal — nothing gets indexed yet, no chat works yet. Just a working, healthy
stack.

---

## Milestones 2 through 6 — what's coming

Detailed step-by-step for each of these gets written once the milestone
before it is verified working, since each one's exact steps depend on real
output from the last (error messages, actual file counts, actual timings).
Here's what each delivers:

**Milestone 2 — Recursive indexing.** The collection registry goes in, so
all 16 reference folders get registered as named collections. A recursive
scanner walks each one, a SHA-256 ledger tracks what's already indexed vs.
new/changed, and a job queue processes TXT, Markdown, PDF text, DOCX, and
XLSX files. You'll see per-collection progress in the UI for the first time.

**Milestone 3 — Search and citations.** Documents get chunked, embedded, and
written into Qdrant. You can search — by keyword, by meaning, or both — and
filter results down to a specific collection or folder.

**Milestone 4 — Full document support.** Docling comes online as the primary
parser (using your local clone), plus OCR for scanned documents, image
support, and fallback handling for anything Docling can't parse.

**Milestone 5 — Grounded chat.** Ollama-powered chat that answers only from
what's actually indexed, with clickable citations back to the source file
and location (page, sheet, row).

**Milestone 6 — Production hardening.** Backup/restore scripts, an
index-rebuild command, automated tests, resource limits, and documentation —
the difference between "works on my machine right now" and "still works
after a reboot, a crash, or six months of neglect."
