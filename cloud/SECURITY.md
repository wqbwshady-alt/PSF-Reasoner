# Cloud Run Security Posture

> Last updated: 2026-09-17 (verified against `cloud/server.py`, `cloud/Dockerfile`, `cloud/deploy.sh`)

## Current Deployment

| Setting | Value |
|---------|-------|
| Service | `psf-cloud-compute` |
| GCP Project | `800903726899` |
| Region | `us-central1` |
| Platform | Cloud Run (managed) |
| Memory / CPU | 2 GiB / 2 vCPU |
| Timeout | 300 s |
| Max instances | 5 |
| Authentication | Public ingress (`--allow-unauthenticated`) so `/health` stays probeable; **every `/compute/*` request requires `X-API-Key` == `PSF_CLOUD_SECRET`** |
| Container user | Unprivileged `appuser` (uid 10001, `USER` directive) |
| Base image | `ubuntu:24.04` |
| FPocket | 4.2.3, built at image build time from the official upstream tarball (SHA-256 pinned) |
| Python deps | Installed into a venv (no `--break-system-packages`) |

## Exposed Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | None | Health check; returns available tools |
| `POST` | `/compute/fpocket` | `X-API-Key` | Pocket detection via FPocket 4.2.3 |
| `POST` | `/compute/coulomb` | `X-API-Key` | Coulombic electrostatics (AMBER ff99) |

## Enforced Controls

### API key authentication (fail-closed)
`PSF_CLOUD_SECRET` must be configured. When it is not, every compute
request is refused with **503** (`PSF_CLOUD_SECRET not configured —
compute endpoints are disabled`). When it is configured, requests
without a matching `X-API-Key` header are refused with **401**.
`deploy.sh` refuses to deploy without a secret and injects it into the
service; the local `HttpCloudAdapter` sends the key automatically from
the `PSF_CLOUD_SECRET` environment variable. The secret value itself is
never stored in this repository.

### Input containment
- `CloudComputeRequest` has **no `structure_path` field** — all compute
  requests must carry inline `pdb_data` text. The historical arbitrary
  filesystem-read vector is gone and locked in by a test.
- `pdb_data` is capped at 18M characters (422 above that) and is
  gemmi-validated before use, including a zero-atom check (422). Garbage
  never reaches the compute engines.
- Request bodies are capped at 50 MB by middleware (413).

### Rate limiting
A per-client-IP token bucket (`PSF_RATE_LIMIT_BURST`, default 30;
`PSF_RATE_LIMIT_RPS`, default 5) throttles `/compute/*` requests (429).
**Limitation:** each Cloud Run instance keeps its own counters, so this
is defense in depth, not a hard global limit. Behind a load balancer,
capacity scales with instance count. For a hard limit, configure Cloud
Run request rate limiting or a dedicated gateway.

### Non-root container
The image runs as an unprivileged `appuser` (uid 10001). RCE via a
parser bug no longer grants root.

### Residual risks (accepted)

| Risk | Severity | Status | Notes |
|------|----------|--------|-------|
| Public ingress for `/health` | LOW | Accepted | Needed for uptime probes. Compute endpoints are key-protected; for a stricter posture, remove `--allow-unauthenticated` in `deploy.sh` and grant `roles/run.invoker` to the caller identity. |
| FPocket subprocess with user-supplied PDB | MEDIUM | Accepted | Input is gemmi-validated first; the remaining risk is inside FPocket's own parser. Dependency trade-off. |
| Per-instance rate limiting | LOW | Accepted | Documented above; each instance limits independently. |

## Local ↔ Cloud Connection

- Local adapter (`HttpCloudAdapter`) connects via HTTPS to
  `$PSF_CLOUD_URL` and authenticates with `X-API-Key` from
  `$PSF_CLOUD_SECRET` (same value deployed to the service).
- PDB data is sent inline as `pdb_data` in the JSON body.
- Transport is encrypted (HTTPS); the server enforces the key on all
  compute endpoints.

## Mitigation Status

| Finding | Severity | Status |
|---------|----------|--------|
| No authentication (`--allow-unauthenticated`) | CRITICAL | **Fixed** — API key on all compute endpoints, fail-closed, deploy-time enforced |
| `structure_path` arbitrary file read | HIGH | **Fixed** — field removed, test-enforced |
| Container runs as root | HIGH | **Fixed** — `USER appuser` |
| No rate limiting | MEDIUM | **Fixed (per instance)** — token bucket; limitation documented |
| No body size limit | MEDIUM | **Fixed** — 50 MB body cap + 18M char pdb_data cap |
| FPocket subprocess risk | MEDIUM | Accepted — gemmi pre-validation added |
| Git history in build context | LOW | **Fixed** — FPocket source no longer vendored; downloaded with pinned SHA-256 at build time |
| `--break-system-packages` | LOW | **Fixed** — dependencies installed into a venv |
