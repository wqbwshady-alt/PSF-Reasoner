# Cloud Run Security Posture

> Last updated: 2026-07-14

## Current Deployment

| Setting | Value |
|---------|-------|
| Service | `psf-cloud-compute` |
| URL | `https://psf-cloud-compute-800903726899.us-central1.run.app` |
| GCP Project | `800903726899` |
| Region | `us-central1` |
| Platform | Cloud Run (managed) |
| Memory / CPU | 2 GiB / 2 vCPU |
| Timeout | 300 s |
| Max instances | 5 |
| Authentication | **`--allow-unauthenticated`** — fully public |
| Ingress | `all` (default) |
| VPC connector | None |
| Container user | **root** (no `USER` directive) |
| Base image | `ubuntu:24.04` |

## Exposed Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Health check; returns available tools |
| `POST` | `/compute/fpocket` | None | Pocket detection via FPocket 4.2.3 |
| `POST` | `/compute/coulomb` | None | Coulombic electrostatics (AMBER ff99) |

## Identified Risks

### CRITICAL — No authentication
The service is deployed with `--allow-unauthenticated`. Any internet user who
discovers the URL can invoke all endpoints. IAM grants `roles/run.invoker` to
`allUsers`. There is no API key, bearer token, or identity-aware proxy.

**Recommendation:** Remove `--allow-unauthenticated` from `deploy.sh`. Use a
service account with `roles/run.invoker` and generate an identity token in
the local adapter.

### HIGH — `structure_path` field in CloudComputeRequest
`CloudComputeRequest.structure_path` accepts an arbitrary filesystem path
string. `_resolve_pdb()` calls `Path(req.structure_path).read_text()` with
no sanitization, no `resolve()`, and no containment check.

**Recommendation:** Remove `structure_path` entirely. Require `pdb_data`
(inline PDB text) for all compute requests. The local adapter already sends
`pdb_data` exclusively.

### HIGH — Container runs as root
No `USER` directive in `Dockerfile`. If an attacker achieves RCE (e.g., via
a vulnerability in FPocket or gemmi), they have full root access to the
container.

**Recommendation:** Add `RUN useradd --create-home appuser && USER appuser`
to `Dockerfile`.

### MEDIUM — No rate limiting
Only `--max-instances=5` limits concurrency. No request-level rate limiting,
no IP-based throttling. An attacker can submit many concurrent compute
requests, consuming project resources.

**Recommendation:** Add FastAPI rate-limiting middleware or configure
Cloud Run rate limits.

### MEDIUM — No request body size limit
No `max_body_size` on endpoints. An attacker can send arbitrarily large
PDB data payloads, consuming memory and CPU.

**Recommendation:** Add body size middleware (e.g., 50 MB cap).

### MEDIUM — FPocket subprocess with attacker-controlled input
`/compute/fpocket` writes user-supplied PDB data to disk and executes the
FPocket C binary on it via `subprocess.run()`. Any vulnerability in
FPocket's PDB parser is exploitable.

**Mitigation:** The `pdb_data` path (inline PDB text) is already the
primary input path from the local adapter. The `structure_path` removal
eliminates the filesystem-read vector. The remaining risk is in FPocket
itself, which is a dependency trade-off.

### LOW — Full git history in Docker build context
`.gcloudignore` does not exclude `fpocket-src/.git/`. The full FPocket
source repository (including `.git/`) is included in the Docker build
context and potentially in the final image.

**Recommendation:** Add `fpocket-src/.git/` to `.gcloudignore`.

### LOW — `--break-system-packages`
`pip3 install --break-system-packages` bypasses PEP 668. If
`requirements.txt` were compromised, system Python packages could be
overwritten.

**Mitigation:** `requirements.txt` is checked into the repository. Use
a virtual environment or a slimmer base image (e.g., `python:3.12-slim`)
instead of `ubuntu:24.04`.

## Local ↔ Cloud Connection

- Local adapter (`HttpCloudAdapter`) connects via HTTPS to
  `$PSF_CLOUD_URL`.
- No client authentication — no API key, no identity token, no mTLS.
- PDB data is sent inline as `pdb_data` in the JSON body.
- Transport is encrypted (HTTPS), but the server accepts all connections.

## Mitigation Status

| Finding | Severity | Status | Notes |
|---------|----------|--------|-------|
| No authentication (`--allow-unauthenticated`) | CRITICAL | Open | Requires GCP IAM changes + adapter update |
| `structure_path` arbitrary file read | HIGH | Open | Remove field from CloudComputeRequest |
| Container runs as root | HIGH | Open | Add `USER` to Dockerfile |
| No rate limiting | MEDIUM | Open | |
| No body size limit | MEDIUM | Open | |
| FPocket subprocess risk | MEDIUM | Accepted | Dependency trade-off |
| Git history in build context | LOW | Open | Add to `.gcloudignore` |
| `--break-system-packages` | LOW | Accepted | Ubuntu 24.04 compatibility |
