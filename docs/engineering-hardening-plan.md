# PSF-Reasoner 工程质量改造实施计划(PR1:阶段1+2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变科学结论的前提下,修复生产依赖、关闭 Web API 任意本地路径读取、加固云服务、移除公开管理接口、将 V3 报告持久化到 SQLite、增加上传内容校验、消除静默降级,并完成全仓 Ruff 清理、CI 增强与五个大文件拆分。

**Architecture:** 所有修复都落在现有分层内(api / application / infrastructure / physical / reasoning / cloud)。V3 持久化复用现有 SQLite 存储体系(`.psf_reasoner/reports.db`,新增 `v3_reports` 表 + `schema_meta` 迁移);可选组件(LM/云/FoldX)通过新的 `ComponentRegistry` 报告状态并写入日志与报告 `runtime` 字段;后台任务系统(阶段3)不在本 PR。

**Tech Stack:** Python ≥3.12, FastAPI, Pydantic v2, gemmi, SQLite(WAL), httpx, Ruff, pytest, Docker(cloud 服务)。

**Spec:** 用户需求(对话中的 10 项要求 + 4 项已确认决策):
1. PR1=阶段1+2,PR2=阶段3(后台任务)。
2. 云服务未配置 `PSF_CLOUD_SECRET` 时计算接口 fail-closed(503);`/health` 公开。
3. 本地工作台 API 默认 SQLite 持久化(`PSF_PERSIST=0` 可关);CLI 默认不变。
4. 云服务实现简单内存限流(按客户端 IP 令牌桶)。

**基线(已实测):** 165 passed / 1 skipped;`ruff check .` 230 错误、50 文件需 format;CI 仅 3.12、仅检查变更文件;`httpx` 只在 dev 依赖但被 `infrastructure/cloud_compute.py` 与 `infrastructure/deepseek_provider.py` 运行时导入;`app.py` 的 `_resolve_structure_input` 接受任意存在的本地路径;`_V3_RESULTS` 为进程级字典;`POST /admin/maintain-uploads` 无保护;上传只查扩展名+大小;`cloud/` 无 `fpocket-src/`(被 .gitignore 排除),cloud-build CI 实际会失败;`cloud/server.py` 的 `CloudComputeRequest` 已无 `structure_path`(SECURITY.md 文档滞后)。

## Global Constraints

- 科学逻辑不得改变:所有置信度/机制/报告内容保持原语义;本计划只做安全、持久化、可观测性与代码组织。
- 现有外部 API 必须兼容:`psf_reasoner.api.app.create_app`/`app`、`psf_reasoner.bootstrap.create_default_runner`/`create_default_service`、`psf_reasoner.reasoning.baseline` 三个类、`reasoning.mechanism_generator.MechanismGenerator`、`physical.interactions` 的 `analyze_typed_interactions`/`count_typed_interactions`/`describe_ligand_atom_types`/`InteractionCounts` 及被测试 import 的 `_ligand_bond_graph`/`_type_ligand_atom`;前端 `window.PSF_I18N` 与全部 DOM id 不变。
- 不得在代码、测试、文档中写入真实密钥;日志不得记录 API 密钥、上传内容或完整结构文本。
- 不需要真实外部密钥/商业软件(FoldX、FPocket、DeepSeek、Anthropic)的测试必须在普通 CI 通过。
- 提交消息结尾带 `Co-Authored-By: Claude Code <noreply@anthropic.com>`;按任务分提交。
- 测试运行命令:`.venv/bin/python -m pytest`;Ruff:`.venv/bin/ruff`。
- 分支 `engineering-hardening` 基于 `origin/main`(5480f64),PR 目标 `main`。

---

### Task 1: 修复生产依赖 + CI 正式依赖导入冒烟

**Files:**
- Modify: `pyproject.toml`(dependencies 增 `httpx`,dev 删 `httpx`)
- Create: `scripts/smoke_prod_imports.py`
- Modify: `.github/workflows/ci.yml`(新增 `prod-imports` job)

**Interfaces:**
- Produces: CI job `prod-imports`;脚本 `scripts/smoke_prod_imports.py` 可 `python` 直接运行,退出码 0 为通过。

- [ ] **Step 1: 改 pyproject.toml**

```toml
dependencies = [
  "fastapi>=0.115,<1",
  "gemmi>=0.6,<1",
  "httpx>=0.28,<1",
  "pydantic>=2.9,<3",
  "python-multipart>=0.0.20,<1",
  "typer>=0.15,<1",
  "uvicorn>=0.34,<1",
]
[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9",
  "pytest-cov>=6,<7",
  "ruff>=0.9,<1",
]
```

- [ ] **Step 2: 写 scripts/smoke_prod_imports.py**

```python
"""Import smoke test for the production-only dependency set.

Run with ONLY the packages from `[project] dependencies` installed.
Fails (exit 1) if any runtime import is missing — this is the guard
against runtime dependencies accidentally living in the dev extra.
"""

import os
import sys
import tempfile


def main() -> int:
    os.chdir(tempfile.mkdtemp(prefix="psf-smoke-"))
    failures = []
    for check in (
        lambda: __import__("psf_reasoner.cli"),
        lambda: __import__("psf_reasoner.bootstrap"),
        lambda: __import__("psf_reasoner.api.app"),
    ):
        try:
            check()
        except Exception as exc:  # noqa: BLE001 — report then exit
            failures.append(f"{type(exc).__name__}: {exc}")

    if failures:
        for f in failures:
            print(f, file=sys.stderr)
        return 1

    from psf_reasoner.api.app import create_app
    from psf_reasoner.bootstrap import create_default_runner
    from psf_reasoner.cli import app as cli_app

    create_app(create_default_runner())
    assert cli_app is not None
    print("prod import smoke: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 3: ci.yml 增加 job**(放在 test job 后)

```yaml
  prod-imports:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install production dependencies only
        run: pip install .
      - name: Import smoke test (production deps only)
        run: python scripts/smoke_prod_imports.py
```

- [ ] **Step 4: 验证**:`.venv/bin/python -m pytest -q`(全绿);`python scripts/smoke_prod_imports.py` 在当前 venv 通过。注意:当前 venv 装了 dev extras,无法本地模拟"无 dev"环境——验证方式为临时 venv:`python3 -m venv /tmp/psf-prod-venv && /tmp/psf-prod-venv/bin/pip install . && /tmp/psf-prod-venv/bin/python scripts/smoke_prod_imports.py`(预期:修复前因缺 httpx 失败,修复后通过)。

- [ ] **Step 5: 提交**

```bash
git add pyproject.toml scripts/smoke_prod_imports.py .github/workflows/ci.yml
git commit -m "fix(deps): move httpx into production dependencies + CI prod-import smoke test

cloud_compute.HttpCloudAdapter and DeepSeekProvider import httpx at
runtime but httpx was only declared in the dev extra, so an install
from the production dependency set broke as soon as PSF_CLOUD_URL or
PSF_LLM_PROVIDER=deepseek was used.  A CI job now installs the package
without extras and imports the API/CLI composition roots.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 2: 收紧 Web API 输入边界(仅 upload_id / 内置示例)

**Files:**
- Modify: `src/psf_reasoner/api/app.py`(`_resolve_structure_input`)
- Test: `tests/test_api.py`(新增测试类 `TestStructureInputBoundary`)

**Interfaces:**
- Consumes: `resolve_upload(upload_id, upload_dir)`(infrastructure/uploads.py)。
- Produces: `_resolve_structure_input` 新语义:upload_id 走上传存储;`path` 仅允许位于 upload 目录或 `EXAMPLES_DIR`(`examples/data`)解析后仍被包含的真实文件;其余一律 400。CLI 不受影响。

- [ ] **Step 1: 先写失败测试**

```python
class TestStructureInputBoundary:
    """Raw filesystem paths must never let the API read arbitrary files."""

    def test_rejects_arbitrary_existing_file(self, structure_file: Path, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        payload = {
            "structure": {"path": str(structure_file)},  # exists, but outside allowed roots
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
            "phenotype": {"name": "drug_resistance"},
        }
        response = client.post("/analyze", json=payload)
        assert response.status_code == 400
        assert "structure" in response.json()["detail"].lower()

    def test_rejects_absolute_path(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        payload = {
            "structure": {"path": "/etc/hosts"},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
        }
        assert client.post("/analyze", json=payload).status_code == 400

    def test_rejects_parent_traversal(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        secret = tmp_path / "secret.pdb"
        secret.write_text("ATOM", encoding="ascii")
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        payload = {
            "structure": {"path": str(upload_dir / ".." / "secret.pdb")},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
        }
        assert client.post("/analyze", json=payload).status_code == 400

    def test_rejects_symlink_escaping_upload_dir(self, structure_file: Path, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "link.pdb").symlink_to(structure_file)
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        payload = {
            "structure": {"path": str(upload_dir / "link.pdb")},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
        }
        assert client.post("/analyze", json=payload).status_code == 400

    def test_accepts_bundled_example(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        example = Path(__file__).parent.parent / "examples" / "data" / "1sdt.cif"
        payload = {
            "structure": {"path": str(example), "format": "mmcif"},
            "mutant_structure": {"path": str(example.with_name("1sdv.cif")), "format": "mmcif"},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
        }
        response = client.post("/analyze", json=payload)
        assert response.status_code == 200, response.text

    def test_structure_endpoint_rejects_symlink_escape(self, structure_file: Path, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "link.pdb").symlink_to(structure_file)
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        resp = client.get("/structure", params={"path": str(upload_dir / "link.pdb")})
        assert resp.status_code == 403
```

- [ ] **Step 2: 运行确认失败**:`pytest tests/test_api.py::TestStructureInputBoundary -v` 预期 `test_rejects_arbitrary_existing_file`、`test_rejects_absolute_path`、`test_rejects_parent_traversal`、`test_rejects_symlink_escaping_upload_dir` FAIL(旧实现放行),其余 PASS。

- [ ] **Step 3: 实现**(替换 `_resolve_structure_input` 的 path 分支)

```python
    # No upload_id — path must reference a file that is either inside the
    # upload store or one of the bundled example fixtures.  The CLI is the
    # entry point for arbitrary user-provided local files; the web API
    # deliberately does not accept them.
    if si.path is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="structure must provide either upload_id or path",
        )
    resolved = Path(si.path).resolve()
    allowed_roots = (upload_dir.resolve(), EXAMPLES_DIR.resolve())
    if not any(root == resolved or root in resolved.parents for root in allowed_roots):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "path is not allowed: the web API only accepts uploaded files "
                "(by upload_id) or bundled example structures.  Use the CLI "
                "to analyze an arbitrary local file."
            ),
        )
    if not resolved.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "structure file not found.  Upload the file via multipart "
                "form first, then reference it by upload_id."
            ),
        )
    return si
```

`Path.resolve()` 在 py3.12+ 默认 strict=False,对不存在的路径也做符号链接解析——逃逸符号链接会被解析到 allowed_roots 之外从而被拒。

- [ ] **Step 4: 运行验证**:`pytest tests/test_api.py tests/test_v3_api.py -v` 全部通过(现有 V3 测试用 `examples/data` 路径,属于允许的白名单)。

- [ ] **Step 5: 提交**

```bash
git add src/psf_reasoner/api/app.py tests/test_api.py
git commit -m "fix(api): restrict web API structure paths to uploads and bundled examples

_resolve_structure_input previously accepted any existing local file,
so a caller could read arbitrary server files through the JSON
endpoints.  The web API now only accepts upload_ids or files under the
upload store / the bundled examples/data fixtures; the CLI keeps
reading user-provided local paths.  Parent traversal, absolute paths
and escaping symlinks are rejected (resolve-based containment check).

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 3: 云服务安全加固

**Files:**
- Modify: `cloud/server.py`
- Modify: `cloud/Dockerfile`
- Modify: `cloud/deploy.sh`
- Modify: `cloud/.gcloudignore`
- Modify: `cloud/SECURITY.md`(重写为真实状态)
- Modify: `src/psf_reasoner/infrastructure/cloud_compute.py`(核对:已自动发送 `X-API-Key`,保持)
- Test: `tests/test_cloud_server.py`(新建,通过 importlib 加载 `cloud/server.py`)

**Interfaces:**
- Produces: `cloud/server.py` 保持端点不变(`/health` 公开;`/compute/{tool}` 要求 `X-API-Key`);新模块级常量 `MAX_BODY_BYTES`、`MAX_PDB_DATA_CHARS`;`build_rate_limit_middleware()`。

- [ ] **Step 1: 写失败测试 tests/test_cloud_server.py**

```python
"""Security tests for the cloud compute service (cloud/server.py).

cloud/server.py is a standalone module (not part of the psf_reasoner
package); tests load it via importlib so its env-var configuration can
be controlled per test by reloading.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

CLOUD_DIR = Path(__file__).parent.parent / "cloud"
SERVER_PATH = CLOUD_DIR / "server.py"


def _load_server() -> Any:
    spec = importlib.util.spec_from_file_location("cloud_server_under_test", SERVER_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def server_module(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Any:
    monkeypatch.setenv("PSF_CLOUD_SECRET", "test-secret-token")
    monkeypatch.setenv("PSF_RATE_LIMIT_BURST", "10")
    monkeypatch.setenv("PSF_RATE_LIMIT_RPS", "0.1")
    return _load_server()


@pytest.fixture
def client(server_module: Any) -> TestClient:
    return TestClient(server_module.app)


_VALID_PDB = (
    "ATOM      1  N   VAL A  82       0.000   0.000   0.000  1.00 20.00           N\n"
    "ATOM      2  CA  VAL A  82       1.000   0.000   0.000  1.00 20.00           C\n"
    "HETATM    4  C1  MK1 B 902       4.000   0.000   0.000  1.00 20.00           C\n"
    "END\n"
)


def test_health_is_public_without_key(client: TestClient) -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_compute_requires_api_key(client: TestClient) -> None:
    resp = client.post("/compute/coulomb", json={"pdb_data": _VALID_PDB})
    assert resp.status_code == 401


def test_compute_rejects_wrong_api_key(client: TestClient) -> None:
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": _VALID_PDB},
        headers={"X-API-Key": "wrong"},
    )
    assert resp.status_code == 401


def test_compute_accepts_valid_key_and_structure(client: TestClient) -> None:
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": _VALID_PDB},
        headers={"X-API-Key": "test-secret-token"},
    )
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list)
    assert items and items[0]["evidence_type"] == "energy_component"


def test_compute_fail_closed_when_secret_unconfigured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PSF_CLOUD_SECRET", raising=False)
    module = _load_server()
    client = TestClient(module.app)
    resp = client.post("/compute/coulomb", json={"pdb_data": _VALID_PDB})
    assert resp.status_code == 503
    resp_health = client.get("/health")
    assert resp_health.status_code == 200


def test_compute_rejects_invalid_structure(server_module: Any, client: TestClient) -> None:
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": "this is not a structure"},
        headers={"X-API-Key": "test-secret-token"},
    )
    assert resp.status_code == 422


def test_oversized_body_is_rejected(client: TestClient) -> None:
    big = "A" * (50 * 1024 * 1024 + 1)
    resp = client.post(
        "/compute/coulomb",
        content=big,
        headers={
            "X-API-Key": "test-secret-token",
            "Content-Type": "application/json",
        },
    )
    assert resp.status_code == 413


def test_oversized_pdb_data_is_rejected(client: TestClient) -> None:
    big = "A" * (20 * 1024 * 1024)  # over MAX_PDB_DATA_CHARS
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": big},
        headers={"X-API-Key": "test-secret-token"},
    )
    assert resp.status_code == 422


def test_rate_limit_rejects_burst(server_module: Any, client: TestClient) -> None:
    for _ in range(11):
        client.post(
            "/compute/coulomb",
            json={"pdb_data": _VALID_PDB},
            headers={"X-API-Key": "test-secret-token"},
        )
    resp = client.post(
        "/compute/coulomb",
        json={"pdb_data": _VALID_PDB},
        headers={"X-API-Key": "test-secret-token"},
    )
    assert resp.status_code == 429


def test_fpocket_endpoint_reports_unavailable(client: TestClient) -> None:
    """CI image-less env: fpocket binary absent → 501, not a crash."""
    resp = client.post(
        "/compute/fpocket",
        json={"pdb_data": _VALID_PDB},
        headers={"X-API-Key": "test-secret-token"},
    )
    assert resp.status_code == 501
```

注意限流测试与其它测试共享进程内限流状态——限流器基于客户端 IP + 可注入时钟;为避免互扰,把限流参数做成 env 可配(`PSF_RATE_LIMIT_BURST`,默认 30),测试 fixture 里 monkeypatch 为 10。若 11 连发与其它测试冲突(TestClient 同一 host),将限流测试放入独立 fixture 并 reload 模块(限流器状态在模块级,reload 即重置)。

- [ ] **Step 2: 运行确认失败**:`pytest tests/test_cloud_server.py -v` 预期认证相关测试在当前代码下 FAIL(未配置密钥时旧行为放行)。

- [ ] **Step 3: 实现 cloud/server.py 加固**

```python
# 头部新增
import time
from collections import deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MAX_BODY_BYTES = 50 * 1024 * 1024
MAX_PDB_DATA_CHARS = 18_000_000

class CloudComputeRequest(BaseModel):
    pdb_data: str = Field(max_length=MAX_PDB_DATA_CHARS)
    params: dict = Field(default_factory=dict)

def _verify_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Enforce the configured API key; fail closed when unconfigured."""
    if not CLOUD_API_SECRET:
        raise HTTPException(503, "PSF_CLOUD_SECRET not configured — compute endpoints are disabled")
    if x_api_key != CLOUD_API_SECRET:
        raise HTTPException(401, "unauthorized")

class _BodyLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if request.method in {"POST", "PUT", "PATCH"} and (
            int(request.headers.get("content-length", 0) or 0) > MAX_BODY_BYTES
        ):
            return JSONResponse({"detail": "request body too large"}, status_code=413)
        return await call_next(request)
```

流式封顶:在 `dispatch` 中对无/不可信 content-length 的请求包裹 receive,累计字节超过 `MAX_BODY_BYTES` 即抛 413(实现 `_LimitedReceive` 包装器)。

```python
class _RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-client-IP token bucket.  Defense in depth; each Cloud Run
    instance keeps its own counters (documented in SECURITY.md)."""

    def __init__(self, app, *, capacity: int, refill_per_second: float) -> None:
        super().__init__(app)
        self._capacity = capacity
        self._refill = refill_per_second
        self._buckets: dict[str, tuple[float, float]] = {}

    async def dispatch(self, request: Request, call_next):
        if not request.url.path.startswith("/compute/"):
            return await call_next(request)
        client = _client_ip(request)
        now = time.monotonic()
        tokens, last = self._buckets.get(client, (float(self._capacity), now))
        tokens = min(self._capacity, tokens + (now - last) * self._refill)
        if tokens < 1.0:
            self._buckets[client] = (tokens, now)
            return JSONResponse({"detail": "rate limit exceeded"}, status_code=429)
        self._buckets[client] = (tokens - 1.0, now)
        return await call_next(request)
```

`_client_ip(request)`:取 `x-forwarded-for` 首个值(仅在本服务可信时才应使用,Cloud Run 由平台注入),否则 `request.client.host`。

`app.add_middleware(_BodyLimitMiddleware)`;`app.add_middleware(_RateLimitMiddleware, capacity=int(os.environ.get("PSF_RATE_LIMIT_BURST", "30")), refill_per_second=float(os.environ.get("PSF_RATE_LIMIT_RPS", "5")))`。

`_resolve_pdb` 增加 gemmi 预校验:

```python
def _resolve_pdb(req: CloudComputeRequest, work_dir: Path) -> Path:
    pdb_path = work_dir / "input.pdb"
    raw = req.pdb_data
    if raw.lstrip().startswith(("data_", "DATA_", "loop_", "LOOP_", "#")):
        try:
            struct = gemmi.read_structure_string(raw)
        except Exception as exc:
            raise HTTPException(422, f"structure data cannot be parsed: {type(exc).__name__}") from exc
        raw = struct.make_minimal_pdb()
        ...
    else:
        try:
            gemmi.read_structure_string(raw)
        except Exception as exc:
            raise HTTPException(422, f"structure data cannot be parsed: {type(exc).__name__}") from exc
    pdb_path.write_text(raw)
    return pdb_path
```

- [ ] **Step 4: Dockerfile 重写(非 root + 下载构建 FPocket 4.2.3)**

```dockerfile
FROM ubuntu:24.04

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    python3 \
    python3-pip \
    python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Build FPocket 4.2.3 from the official upstream tarball (Discngine/fpocket).
# The source is no longer vendored in this repository (was gitignored),
# which previously made the Docker build fail in CI.
ARG FPOCKET_VERSION=4.2.3
ARG FPOCKET_SHA256=62b3da6490eeab0db488f0182150d340de2be0be23f4fd1def9d5846ce724ede
RUN curl -fsSL "https://github.com/Discngine/fpocket/archive/refs/tags/${FPOCKET_VERSION}.tar.gz" \
        -o /tmp/fpocket.tar.gz \
    && echo "${FPOCKET_SHA256}  /tmp/fpocket.tar.gz" | sha256sum -c - \
    && tar xzf /tmp/fpocket.tar.gz -C /tmp \
    && cd "/tmp/fpocket-${FPOCKET_VERSION}" \
    && make \
    && cp bin/fpocket /usr/local/bin/ \
    && rm -rf "/tmp/fpocket-${FPOCKET_VERSION}" /tmp/fpocket.tar.gz

# Run as an unprivileged user.
RUN useradd --create-home --uid 10001 appuser
WORKDIR /app

RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

USER appuser
EXPOSE 8080
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8080"]
```

(`python3 -m venv /opt/venv` + venv 内 pip 安装规避 PEP 668,消除 `--break-system-packages` 风险项;非 root 用户对 /tmp 有写权限,FPocket 临时目录无需额外处理。)

- [ ] **Step 5: deploy.sh 强制密钥、去掉公开部署**

```bash
PSF_CLOUD_SECRET="${PSF_CLOUD_SECRET:?Set PSF_CLOUD_SECRET to a random token (e.g. openssl rand -hex 32). Compute endpoints refuse requests without it.}"

gcloud run deploy "${SERVICE_NAME}" \
  --image="${IMAGE}" \
  --platform=managed \
  --region="${REGION}" \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300 \
  --max-instances=5 \
  --allow-unauthenticated \
  --set-env-vars="PSF_CLOUD_SECRET=${PSF_CLOUD_SECRET},PSF_RATE_LIMIT_BURST=30,PSF_RATE_LIMIT_RPS=5" \
  --project="${PROJECT_ID}"
```

`--allow-unauthenticated` 保留是为了 `/health` 公开可达;计算接口由应用层密钥保护(在 SECURITY.md 与脚本注释中说明;生产更严格的选项是 `--no-allow-unauthenticated` + IAM,记为可选强化)。脚本末尾提示本地导出 `PSF_CLOUD_SECRET`。

- [ ] **Step 6: .gcloudignore 与 SECURITY.md**
  - `.gcloudignore`:增加 `*.pyc`、`__pycache__/`(fpocket-src 已不进入构建上下文,该项 LOW 风险随之消除)。
  - `SECURITY.md` 重写:对照新实现逐项更新表格——认证=已实现(API key fail-closed,deploy 强制注入;`--allow-unauthenticated` 仅保留 /health,记残余风险+可选 IAM 方案);structure_path=已不存在(历史修复,现加测试锁定);非 root=已实现;体积限制=已实现(50MB body / 18M 字符 pdb_data);限流=已实现(每实例内存令牌桶,多实例为纵深防御);FPocket 子进程=接受(风险缓解:gemmi 预校验);git 历史进上下文=已消除;--break-system-packages=已消除(venv)。所有状态与事实一致,不写密钥。

- [ ] **Step 7: 本地 HttpCloudAdapter 核对** — 已读源码确认:`PSF_CLOUD_SECRET` 存在时自动加 `X-API-Key` 头。补一条单元测试(httpx.MockTransport 捕获请求头),放 tests/test_infrastructure.py 或 tests/test_cloud_server.py:

```python
def test_http_cloud_adapter_sends_api_key(monkeypatch, tmp_path: Path) -> None:
    import httpx
    from psf_reasoner.infrastructure.cloud_compute import HttpCloudAdapter
    from psf_reasoner.schemas.inputs import StructureInput

    structure = tmp_path / "input.pdb"
    structure.write_text(_VALID_PDB, encoding="ascii")
    captured: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["headers"] = dict(request.headers)
        return httpx.Response(200, json=[_sample_evidence()])

    monkeypatch.setenv("PSF_CLOUD_SECRET", "adapter-secret")
    adapter = HttpCloudAdapter(base_url="http://cloud.test", timeout=5.0)
    adapter._client = httpx.Client(transport=httpx.MockTransport(handler))  # 或构造注入 client
    adapter.fpocket(StructureInput(path=str(structure)))
    assert captured["headers"].get("x-api-key") == "adapter-secret"
```

若 `HttpCloudAdapter` 没有注入 client 的口子,则给它增加可选构造参数 `client: httpx.Client | None = None`(向后兼容),关闭时注意所有权。

- [ ] **Step 8: 运行验证**:`pytest tests/test_cloud_server.py -v` 全绿;`pytest -q` 全绿。

- [ ] **Step 9: 提交**(拆两个提交:server.py+测试;Docker/deploy/SECURITY/docs)

```bash
git add cloud/server.py tests/test_cloud_server.py src/psf_reasoner/infrastructure/cloud_compute.py tests/test_infrastructure.py
git commit -m "fix(cloud): fail-closed API key auth, body limits, rate limiting, input validation

Compute endpoints now refuse requests when PSF_CLOUD_SECRET is not
configured (503) and require a matching X-API-Key otherwise (401);
/health stays public.  Request bodies are capped at 50 MB, pdb_data at
18M chars, PDB/CIF text is gemmi-validated before use, and a
per-client-IP token bucket limits compute request bursts.  The
HttpCloudAdapter already sent the key from PSF_CLOUD_SECRET; this is
now covered by a MockTransport test.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
git add cloud/Dockerfile cloud/deploy.sh cloud/.gcloudignore cloud/SECURITY.md
git commit -m "fix(cloud): non-root container, reproducible FPocket build, key-required deploy

The image previously ran as root and COPY'd a vendored fpocket-src
directory that is gitignored and absent from the repository — the CI
cloud build was guaranteed to fail.  The Dockerfile now downloads the
official FPocket 4.2.3 tarball (pinned SHA-256), builds it, installs
dependencies into a venv (no --break-system-packages), and runs as an
unprivileged user.  deploy.sh refuses to deploy without
PSF_CLOUD_SECRET and injects it into the service.  SECURITY.md updated
to reflect the verified state of every finding.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 4: 移除公开管理接口,上传维护移入 lifespan

**Files:**
- Modify: `src/psf_reasoner/api/app.py`
- Test: `tests/test_api.py`(新增 `TestUploadMaintenance`)

- [ ] **Step 1: 写失败测试**

```python
class TestUploadMaintenance:
    def test_admin_maintain_uploads_route_is_removed(self, tmp_path: Path) -> None:
        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
        resp = client.post("/admin/maintain-uploads")
        assert resp.status_code == 404

    def test_startup_cleanup_removes_expired_uploads(
        self, structure_file: Path, tmp_path: Path
    ) -> None:
        import os
        import time

        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        old = upload_dir / "old.pdb"
        old.write_text("OLD", encoding="ascii")
        old_time = time.time() - 48 * 3600
        os.utime(old, (old_time, old_time))

        app = create_app(create_default_runner(), upload_dir=upload_dir)
        with TestClient(app):
            pass  # lifespan runs maintain_uploads on startup
        assert not old.exists()

    def test_maintenance_is_idempotent(self, tmp_path: Path) -> None:
        from psf_reasoner.infrastructure.uploads import maintain_uploads

        upload_dir = tmp_path / ".psf_uploads"
        upload_dir.mkdir()
        (upload_dir / "a.pdb").write_text("A", encoding="ascii")
        first = maintain_uploads(upload_dir)
        second = maintain_uploads(upload_dir)
        assert second == {"age_removed": 0, "count_removed": 0}
        assert (upload_dir / "a.pdb").exists()
```

- [ ] **Step 2: 运行确认失败**:`pytest tests/test_api.py::TestUploadMaintenance -v` → admin 路由测试 FAIL(路由存在)。

- [ ] **Step 3: 实现**
  - 删除 `@api.post("/admin/maintain-uploads")` 路由与 `create_app` 中的启动调用;
  - `create_app` 加入 lifespan(同时把 `_upload_dir.mkdir` 从工厂顶部移入 lifespan;`/health` 等逻辑不变):

```python
from contextlib import asynccontextmanager

def create_app(...):
    active_runner = runner or _default_persistent_runner()
    _upload_dir = upload_dir or UPLOAD_DIR
    api = FastAPI(..., lifespan=lifespan)  # 见下

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        _upload_dir.mkdir(parents=True, exist_ok=True)
        maintain_uploads(_upload_dir)
        yield
```

注意 FastAPI 要求 lifespan 在 `FastAPI(...)` 构造时传入;把 lifespan 定义放在 create_app 内部、构造前。

  - 更新 `_store_upload` 内 `upload_dir.mkdir(parents=True, exist_ok=True)` 保留(防御性,幂等)。
  - 模块级 `app = create_app()` 不再在导入时建目录/清理(副作用移到 lifespan)。

- [ ] **Step 4: 运行验证**:`pytest tests/test_api.py tests/test_uploads.py tests/test_v3_api.py -v` 全绿;`pytest -q` 全绿;`python scripts/smoke_prod_imports.py` 通过且不产生 `.psf_uploads`(smoke 脚本已 chdir 到临时目录,断言目录不存在)。

- [ ] **Step 5: 提交**

```bash
git add src/psf_reasoner/api/app.py tests/test_api.py
git commit -m "fix(api): remove unauthenticated upload-maintenance endpoint, use lifespan

POST /admin/maintain-uploads was a public, unauthenticated maintenance
operation.  The route is removed; upload pruning now runs from the
FastAPI lifespan on startup, and maintain_uploads() remains a public,
idempotent function covered by tests.  App-creation side effects
(directory creation, cleanup) no longer run at import time.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 5: V3 报告 SQLite 持久化

**Files:**
- Create: `src/psf_reasoner/infrastructure/v3_repository.py`
- Modify: `src/psf_reasoner/api/app.py`(替换 `_V3_RESULTS`;`create_app(v3_store=None)`;导出走 store;新增 `DELETE /v3/reports/{report_id}`;lifespan 过期清理;API 默认 runner 持久化)
- Modify: `src/psf_reasoner/infrastructure/sqlite_repository.py`(加 `prune_old` 供启动清理;保持现有表结构不动)
- Test: `tests/test_v3_persistence.py`(新建)

**Interfaces:**
- Produces:
  - `V3ReportRepository(db_path: str | Path = ".psf_reasoner/reports.db")` — `save(payload: dict) -> None`、`get(report_id: str) -> dict`、`delete(report_id: str) -> bool`、`count() -> int`、`list_ids() -> tuple[str, ...]`、`prune_old(max_age_seconds: float) -> int`;`V3ReportNotFoundError(LookupError)`;`SCHEMA_VERSION = 1`。
  - `create_app(runner=None, upload_dir=None, v3_store=None)` 保持既有两个位置参数兼容;默认 v3_store 为惰性初始化的 `V3ReportRepository()`(首次操作才建库,保持导入无副作用)。
  - API 默认 runner:`create_default_runner(persist=os.environ.get("PSF_PERSIST", "1") != "0")`。

- [ ] **Step 1: 写失败测试 tests/test_v3_persistence.py**

```python
"""Persistence tests for V3 analysis payloads."""

from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.infrastructure.v3_repository import (
    V3ReportNotFoundError,
    V3ReportRepository,
)

REPO_ROOT = Path(__file__).parent.parent


def _payload(report_id: str = "report-aaaaaaaaaaaa") -> dict:
    return {
        "report_id": report_id,
        "v2_report": {"report_id": report_id, "schema_version": "1.0.0"},
        "protein_identity": {"family_hint": "TEST"},
        "v3_context": {"mutation_site": {}},
        "v3_causal_graph": None,
        "v3_literature": {"total_entries": 0},
        "evidence_localization": {},
    }


class TestV3Repository:
    def test_survives_repository_recreation(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        V3ReportRepository(db).save(_payload())
        # A brand-new instance over the same file must see the report —
        # this is the restart-recovery property.
        restored = V3ReportRepository(db).get("report-aaaaaaaaaaaa")
        assert restored["report_id"] == "report-aaaaaaaaaaaa"

    def test_missing_report_raises(self, tmp_path: Path) -> None:
        with pytest.raises(V3ReportNotFoundError):
            V3ReportRepository(tmp_path / "reports.db").get("nope")

    def test_delete(self, tmp_path: Path) -> None:
        repo = V3ReportRepository(tmp_path / "reports.db")
        repo.save(_payload())
        assert repo.delete("report-aaaaaaaaaaaa") is True
        assert repo.delete("report-aaaaaaaaaaaa") is False
        assert repo.count() == 0

    def test_prune_old_removes_expired(self, tmp_path: Path) -> None:
        repo = V3ReportRepository(tmp_path / "reports.db")
        repo.save(_payload("report-old"))
        repo.save(_payload("report-fresh"))
        # Age the old row directly.
        import sqlite3

        cutoff = (time.time() - 60 * 60 * 48)
        with sqlite3.connect(str(tmp_path / "reports.db")) as conn:
            conn.execute(
                "UPDATE v3_reports SET generated_at = ? WHERE report_id = ?",
                (time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime(cutoff)), "report-old"),
            )
        assert repo.prune_old(max_age_seconds=3600) == 1
        with pytest.raises(V3ReportNotFoundError):
            repo.get("report-old")
        assert repo.get("report-fresh")["report_id"] == "report-fresh"

    def test_schema_version_recorded(self, tmp_path: Path) -> None:
        db = tmp_path / "reports.db"
        V3ReportRepository(db).save(_payload())
        V3ReportRepository(db)  # re-open: migrations must be idempotent
        import sqlite3

        with sqlite3.connect(str(db)) as conn:
            row = conn.execute("SELECT value FROM schema_meta WHERE key = 'schema_version'").fetchone()
        assert row and int(row[0]) >= 1

    def test_concurrent_save_and_get(self, tmp_path: Path) -> None:
        repo = V3ReportRepository(tmp_path / "reports.db")

        def write(i: int) -> str:
            rid = f"report-{i:012d}"
            repo.save(_payload(rid))
            return rid

        with ThreadPoolExecutor(max_workers=8) as pool:
            ids = list(pool.map(write, range(16)))
        for rid in ids:
            assert repo.get(rid)["report_id"] == rid
        assert repo.count() == 16


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            create_default_runner(),
            upload_dir=tmp_path / ".psf_uploads",
            v3_store=V3ReportRepository(tmp_path / "reports.db"),
        )
    )


class TestV3ApiPersistence:
    def test_export_survives_app_recreation(self, tmp_path: Path) -> None:
        payload = {
            "structure": {"path": str(REPO_ROOT / "examples/data/1sdt.cif"), "format": "mmcif"},
            "mutant_structure": {"path": str(REPO_ROOT / "examples/data/1sdv.cif"), "format": "mmcif"},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
        }
        first = _client(tmp_path)
        resp = first.post("/v3/analyze", json=payload)
        assert resp.status_code == 200, resp.text
        report_id = resp.json()["report_id"]

        # A completely new app instance (new runner, new store object,
        # same db file) must still export the report.
        second = _client(tmp_path)
        r = second.get(f"/export/{report_id}", params={"format": "json"})
        assert r.status_code == 200
        assert json.loads(r.text)["report_id"] == report_id

    def test_delete_report(self, tmp_path: Path) -> None:
        client = _client(tmp_path)
        payload = {
            "structure": {"path": str(REPO_ROOT / "examples/data/1sdt.cif"), "format": "mmcif"},
            "mutant_structure": {"path": str(REPO_ROOT / "examples/data/1sdv.cif"), "format": "mmcif"},
            "ligand": {"identifier": "MK1"},
            "mutation": {"notation": "V82A", "chain": "A"},
        }
        report_id = client.post("/v3/analyze", json=payload).json()["report_id"]
        resp = client.delete(f"/v3/reports/{report_id}")
        assert resp.status_code == 200
        assert client.get(f"/export/{report_id}").status_code == 404

    def test_no_process_level_cache(self) -> None:
        import psf_reasoner.api.app as app_module

        assert not hasattr(app_module, "_V3_RESULTS")
```

注意 `_payload` 的 report_id 格式必须匹配 `PSFReport` 的 `^report-[a-f0-9]{12}$`(仅当 store 里做校验时;store 存的是原始 dict,不校验,但用合法格式避免歧义)。`report-aaaaaaaaaaaa` = `report-` + 12 个 a,合法。

- [ ] **Step 2: 运行确认失败**:`pytest tests/test_v3_persistence.py -v` → import/属性错误 FAIL。

- [ ] **Step 3: 实现 v3_repository.py**

```python
"""SQLite-backed V3 analysis payload repository.

Stores the combined V3 payload (V2 report + structural context + causal
graph + literature) in the SAME SQLite database file used by
SqliteReportRepository (.psf_reasoner/reports.db) so both kinds of
report share one storage system.  Schema changes go through a versioned
migration table (schema_meta) rather than ad-hoc ALTERs.
"""

from __future__ import annotations

import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock

_DEFAULT_DB_PATH = ".psf_reasoner/reports.db"
SCHEMA_VERSION = 1

_MIGRATIONS: tuple[tuple[str, ...], ...] = (
    # version 1
    (
        "CREATE TABLE IF NOT EXISTS v3_reports ("
        "  report_id    TEXT PRIMARY KEY,"
        "  generated_at TEXT NOT NULL,"
        "  payload      TEXT NOT NULL"
        ")",
        "CREATE INDEX IF NOT EXISTS idx_v3_reports_generated_at ON v3_reports(generated_at DESC)",
    ),
)


class V3ReportNotFoundError(LookupError):
    """Raised when a V3 report does not exist in the repository."""


class V3ReportRepository:
    """Thread-safe SQLite store for V3 payloads; lazy schema init."""

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self._db_path = Path(db_path)
        self._lock = RLock()
        self._initialised = False

    def save(self, payload: dict) -> None:
        report_id = payload["report_id"]
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO v3_reports(report_id, generated_at, payload) "
                    "VALUES (?, ?, ?)",
                    (
                        report_id,
                        datetime.now(UTC).isoformat(),
                        json.dumps(payload, ensure_ascii=False, default=str),
                    ),
                )

    def get(self, report_id: str) -> dict:
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                row = conn.execute(
                    "SELECT payload FROM v3_reports WHERE report_id = ?", (report_id,)
                ).fetchone()
        if row is None:
            raise V3ReportNotFoundError(report_id)
        return json.loads(row[0])

    def delete(self, report_id: str) -> bool:
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                cursor = conn.execute("DELETE FROM v3_reports WHERE report_id = ?", (report_id,))
            return cursor.rowcount > 0

    def count(self) -> int:
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                row = conn.execute("SELECT COUNT(*) FROM v3_reports").fetchone()
            return int(row[0]) if row else 0

    def list_ids(self) -> tuple[str, ...]:
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                rows = conn.execute(
                    "SELECT report_id FROM v3_reports ORDER BY generated_at DESC"
                ).fetchall()
            return tuple(row[0] for row in rows)

    def prune_old(self, max_age_seconds: float) -> int:
        cutoff = (time.time() - max_age_seconds)
        with self._lock:
            self._init_db()
            with self._connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM v3_reports WHERE generated_at < ?",
                    (datetime.fromtimestamp(cutoff, tz=UTC).isoformat(),),
                )
            return cursor.rowcount

    def _init_db(self) -> None:
        if self._initialised:
            return
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connection() as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            row = conn.execute(
                "SELECT value FROM schema_meta WHERE key = 'schema_version'"
            ).fetchone()
            version = int(row[0]) if row else 0
            for target in range(version + 1, SCHEMA_VERSION + 1):
                for statement in _MIGRATIONS[target - 1]:
                    conn.execute(statement)
                conn.execute(
                    "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
                    (str(target),),
                )
        self._initialised = True

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self._db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
```

`prune_old` 的 `generated_at` 比较依赖 ISO-8601 字符串字典序;测试里用 `time.strftime("%Y-%m-%dT%H:%M:%S+00:00", ...)` 生成的值与本实现 `datetime.isoformat()`(+00:00 后缀)字典序一致。若测试与实现格式有偏差,以实现的 isoformat 为准修正测试中的 UPDATE 值。

- [ ] **Step 4: 改造 app.py**
  - 删除 `_V3_RESULTS`;`create_app(..., v3_store: V3ReportRepository | None = None)`,默认 `v3_store or V3ReportRepository()`(惰性建库,导入无副作用)。
  - 默认 runner 改为持久化:`active_runner = runner or create_default_runner(persist=os.environ.get("PSF_PERSIST", "1") != "0")`。**同时把 `SqliteReportRepository` 改为惰性初始化**(`__init__` 不再建目录/建表,`_init_db` 挪到首次 save/get/list/delete/prune 前,`_initialised` 标志 + RLock 保护)——否则模块级 `app = create_app()` 在 import 时又会在 CWD 创建 `.psf_reasoner/`,与 Task 4 的"导入无副作用"目标矛盾。`InMemoryReportRepository` 不变。
  - `_build_v3_payload(..., v3_store)`:末尾 `v3_store.save(payload)` 替换 `_V3_RESULTS[...] = payload`。
  - `/export/{report_id}`:`payload = v3_store.get(report_id)`,404 detail 改为 `"no V3 analysis found for this report_id. Run a V3 analysis first; reports are stored on disk and survive restarts."`;捕获 `V3ReportNotFoundError`。
  - 新增 `@api.delete("/v3/reports/{report_id}")` → `{"status": "ok", "deleted": v3_store.delete(report_id)}`。
  - lifespan 增加 `v3_store.prune_old(max_age_seconds=_v3_max_age())`,`_v3_max_age()` 读 `PSF_V3_MAX_AGE_DAYS`(默认 30)→ 秒。
  - `sqlite_repository.py` 加 `prune_old(max_age_seconds) -> int`(同模式,`DELETE FROM reports WHERE generated_at < ?`),并在 lifespan 中同样调用(仅当 runner 用 SQLite repo 时——通过 runner 暴露?简单起见:lifespan 只清理 v3_store;V2 仓库清理由 `SqliteReportRepository.prune_old` 提供、在 create_default_runner(persist=True) 构造时不做自动清理,由调用方(API lifespan)可选调用。为控制范围:V2 prune_old 提供方法+单元测试,API 不自动调用,PR 中说明)。

- [ ] **Step 5: 运行验证**:`pytest tests/test_v3_persistence.py tests/test_v3_api.py -v` 全绿;`pytest -q` 全绿。

- [ ] **Step 6: 提交**

```bash
git add src/psf_reasoner/infrastructure/v3_repository.py src/psf_reasoner/api/app.py src/psf_reasoner/infrastructure/sqlite_repository.py tests/test_v3_persistence.py
git commit -m "feat(api): persist V3 reports in SQLite, remove process-level cache

V3 payloads were kept in a process-local dict, so exports vanished on
restart, multi-process deployments could not share them, and memory
grew without bound.  V3 payloads now live in the same SQLite database
as V2 reports (.psf_reasoner/reports.db) behind a versioned
schema_meta migration table, with delete/prune support and restart
recovery tests.  The workbench API now persists reports by default
(PSF_PERSIST=0 disables); the CLI default is unchanged.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 6: 上传结构文件内容校验

**Files:**
- Modify: `src/psf_reasoner/infrastructure/uploads.py`(加 `InvalidStructureError`、`MAX_STRUCTURE_MODELS=100`、`MAX_STRUCTURE_ATOMS=2_000_000`、`validate_structure_file(path)`)
- Modify: `src/psf_reasoner/api/app.py`(`_store_upload` 写入后校验,失败删除+422)
- Test: `tests/test_upload_validation.py`(新建)

**Interfaces:**
- Produces: `validate_structure_file(path: Path | str) -> None`,失败抛 `InvalidStructureError(ValueError)`,消息不含路径。

- [ ] **Step 1: 写失败测试 tests/test_upload_validation.py**

```python
"""Content validation for structure uploads (beyond extension + size)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.infrastructure.uploads import (
    InvalidStructureError,
    validate_structure_file,
)

REPO_ROOT = Path(__file__).parent.parent


def _client(tmp_path: Path) -> TestClient:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    return TestClient(create_app(create_default_runner(), upload_dir=upload_dir))


def _post_file(client: TestClient, name: str, content: bytes, fields: dict | None = None):
    return client.post(
        "/v3/analyze-upload",
        files={"reference_file": (name, content, "chemical/x-pdb")},
        data={**(fields or {}), "ligand": "MK1", "mutation": "V82A", "chain": "A"},
    )


def test_valid_pdb_upload_accepted(tmp_path: Path) -> None:
    client = _client(tmp_path)
    with open(REPO_ROOT / "examples/data/1sdt.cif", "rb") as f1, open(
        REPO_ROOT / "examples/data/1sdv.cif", "rb"
    ) as f2:
        resp = client.post(
            "/v3/analyze-upload",
            files={
                "reference_file": ("1sdt.cif", f1, "chemical/x-cif"),
                "mutant_file": ("1sdv.cif", f2, "chemical/x-cif"),
            },
            data={"ligand": "MK1", "mutation": "V82A", "chain": "A"},
        )
    assert resp.status_code == 200, resp.text


def test_fake_extension_text_rejected(tmp_path: Path) -> None:
    resp = _post_file(_client(tmp_path), "not_a_structure.pdb", b"hello world, definitely not a PDB")
    assert resp.status_code == 422
    assert "parse" in resp.json()["detail"].lower() or "structure" in resp.json()["detail"].lower()


def test_empty_file_rejected(tmp_path: Path) -> None:
    resp = _post_file(_client(tmp_path), "empty.pdb", b"")
    assert resp.status_code == 422


def test_zero_atom_structure_rejected(tmp_path: Path) -> None:
    content = b"HEADER    EMPTY STRUCTURE\nEND\n"
    resp = _post_file(_client(tmp_path), "zero.pdb", content)
    assert resp.status_code == 422
    assert "atom" in resp.json()["detail"].lower()


def test_malformed_structure_rejected(tmp_path: Path) -> None:
    resp = _post_file(_client(tmp_path), "malformed.cif", b"\x00\x01\x02garbage\xff\xfe")
    assert resp.status_code == 422


def test_rejected_upload_is_deleted(tmp_path: Path) -> None:
    client = _client(tmp_path)
    upload_dir = tmp_path / ".psf_uploads"
    before = set(upload_dir.iterdir())
    resp = _post_file(client, "bad.pdb", b"not a structure")
    assert resp.status_code == 422
    assert set(upload_dir.iterdir()) == before, "failed upload must not leave files behind"


def test_oversized_upload_rejected(tmp_path: Path) -> None:
    content = b"ATOM" + b" " * (25 * 1024 * 1024)
    resp = _post_file(_client(tmp_path), "big.pdb", content)
    assert resp.status_code == 413


def test_error_detail_hides_server_paths(tmp_path: Path) -> None:
    client = _client(tmp_path)
    resp = _post_file(client, "bad.pdb", b"not a structure")
    detail = resp.json()["detail"]
    assert str(tmp_path) not in detail
    assert "/Users" not in detail and "/home" not in detail and "/tmp" not in detail


class TestValidateStructureFile:
    def test_accepts_valid_pdb(self, tmp_path: Path) -> None:
        path = tmp_path / "ok.pdb"
        path.write_text(
            "ATOM      1  N   VAL A  82       0.000   0.000   0.000  1.00 20.00           N\nEND\n",
            encoding="ascii",
        )
        validate_structure_file(path)  # must not raise

    def test_rejects_unparseable(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.pdb"
        path.write_text("certainly not a structure", encoding="ascii")
        with pytest.raises(InvalidStructureError):
            validate_structure_file(path)
```

`test_error_detail_hides_server_paths` 的 `/tmp` 检查与 macOS `/tmp` 私有路径无关(错误消息不应含路径即可,断言取保守三项)。

- [ ] **Step 2: 运行确认失败**:`pytest tests/test_upload_validation.py -v` → 校验相关测试 FAIL(旧实现只查扩展名)。

- [ ] **Step 3: 实现 uploads.py 校验函数**

```python
MAX_STRUCTURE_MODELS = 100
MAX_STRUCTURE_ATOMS = 2_000_000


class InvalidStructureError(ValueError):
    """The uploaded file is not a usable protein structure."""


def validate_structure_file(path: Path | str) -> None:
    """Parse *path* with gemmi and reject unusable structures.

    Raises InvalidStructureError for files gemmi cannot parse, files
    with no models, zero atoms, or implausible model/atom counts.
    Error messages never contain filesystem paths.
    """
    import gemmi

    try:
        structure = gemmi.read_structure(str(path))
    except Exception as exc:
        raise InvalidStructureError(
            f"structure file cannot be parsed: {type(exc).__name__}"
        ) from exc

    model_count = len(structure)
    if model_count < 1:
        raise InvalidStructureError("structure contains no models")
    if model_count > MAX_STRUCTURE_MODELS:
        raise InvalidStructureError(
            f"structure has {model_count} models (limit {MAX_STRUCTURE_MODELS})"
        )
    atom_count = sum(
        1
        for model in structure
        for chain in model
        for residue in chain
        for _ in residue
    )
    if atom_count == 0:
        raise InvalidStructureError("structure contains no atoms")
    if atom_count > MAX_STRUCTURE_ATOMS:
        raise InvalidStructureError(
            f"structure has {atom_count} atoms (limit {MAX_STRUCTURE_ATOMS})"
        )
```

注意 gemmi 解析失败时其异常消息可能含路径——只用 `type(exc).__name__`,不转发消息。gemmi 对部分畸形文件可能宽容(把文本当 PDB 读入但 0 原子)——0 原子检查兜底。空文件:`read_structure` 会抛(文件格式无法识别)或 0 模型,两路都被拒。

- [ ] **Step 4: 实现 app.py `_store_upload` 校验**(写入完成、size 检查后)

```python
    from psf_reasoner.infrastructure.uploads import InvalidStructureError, validate_structure_file

    try:
        validate_structure_file(destination)
    except InvalidStructureError as exc:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
```

(模块顶部改为直接 import;按 Task 10 拆分时迁到 upload_service。)

- [ ] **Step 5: 运行验证**:`pytest tests/test_upload_validation.py tests/test_api.py tests/test_v3_api.py -v` 全绿;`pytest -q` 全绿。

- [ ] **Step 6: 提交**

```bash
git add src/psf_reasoner/infrastructure/uploads.py src/psf_reasoner/api/app.py tests/test_upload_validation.py
git commit -m "fix(api): gemmi content validation for structure uploads

Uploads were accepted on extension + size alone, so garbage could
reach the analysis pipeline and validation failures leaked nothing
useful.  Uploaded files are now parsed with gemmi before use: empty
files, zero-atom structures, implausible model/atom counts and
unparseable content return 422 with path-free messages, and the
written temp file is removed on rejection.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 7: 消除静默降级(组件状态/日志/健康接口/报告 runtime 字段)

**Files:**
- Create: `src/psf_reasoner/infrastructure/component_status.py`
- Modify: `src/psf_reasoner/bootstrap.py`(LLM provider 失败日志+注册;注册 reasoning/modeler/cloud 状态;runner 注入 runtime factory)
- Modify: `src/psf_reasoner/application/runner.py`(可选 `runtime_factory`;run() 时附到报告)
- Modify: `src/psf_reasoner/schemas/report.py`(新增可选 `runtime: ReportRuntime | None = None` 与 `ReportRuntime` 模型)
- Modify: `src/psf_reasoner/physical/cloud_provider.py`(suppress → 记录日志+更新状态)
- Modify: `src/psf_reasoner/physical/modeling.py`(FoldX 回退日志+版本捕获+状态)
- Modify: `src/psf_reasoner/physical/openbabel_typing.py`、`src/psf_reasoner/physical/identity.py`、`src/psf_reasoner/physical/structure_qc.py`(降级点补日志)
- Modify: `src/psf_reasoner/api/app.py`(`/health` 返回组件状态)
- Test: `tests/test_component_status.py`(新建)

**Interfaces:**
- Produces:
  - `ComponentStatus`(frozen dataclass:`name: str, enabled: bool, available: bool, implementation: str, detail: str = ""`)`to_dict() -> dict[str, object]`
  - `ComponentRegistry`:`set(status) / get(name) -> ComponentStatus | None / snapshot() -> dict[str, dict]`;模块级单例 `component_registry`
  - `ReportRuntime(reasoning_engine: str, mutation_modeler: str, llm_provider: str | None = None, cloud_adapter: str | None = None, external_tools: dict[str, str] = {}, component_status: dict[str, dict] = {})`
  - `AnalysisRunner(..., runtime_factory: Callable[[], ReportRuntime] | None = None)`

- [ ] **Step 1: 写失败测试 tests/test_component_status.py**

```python
"""Optional-component status, degradation logging, and report runtime info."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from psf_reasoner.api.app import create_app
from psf_reasoner.bootstrap import create_default_runner
from psf_reasoner.infrastructure.component_status import (
    ComponentStatus,
    component_registry,
)


def test_registry_set_get_snapshot() -> None:
    component_registry.set(ComponentStatus("x", True, False, "impl-a", "detail"))
    assert component_registry.get("x").implementation == "impl-a"  # type: ignore[union-attr]
    snap = component_registry.snapshot()
    assert snap["x"]["implementation"] == "impl-a"


def test_invalid_llm_provider_logs_and_falls_back(monkeypatch, caplog) -> None:
    from psf_reasoner import bootstrap

    monkeypatch.setenv("PSF_LLM", "1")
    monkeypatch.setenv("PSF_LLM_PROVIDER", "no-such-provider")
    with caplog.at_level(logging.WARNING, logger="psf_reasoner.bootstrap"):
        provider = bootstrap._auto_llm_provider()
    assert provider is None
    assert "no-such-provider" in caplog.text
    assert "DEEPSEEK_API_KEY" not in caplog.text


def test_default_runner_is_baseline_and_status_reflected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("PSF_LLM", raising=False)
    monkeypatch.delenv("PSF_CLOUD_URL", raising=False)
    runner = create_default_runner()
    from psf_reasoner.application.runner import AnalysisRunner

    assert isinstance(runner, AnalysisRunner)
    status = component_registry.get("reasoning_engine")
    assert status is not None and status.implementation == "baseline"
    modeler = component_registry.get("mutation_modeler")
    assert modeler is not None and modeler.implementation == "local_side_chain"


def test_report_records_runtime_components(
    structure_file: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("PSF_LLM", raising=False)
    monkeypatch.delenv("PSF_CLOUD_URL", raising=False)
    runner = create_default_runner()
    request = _simple_request(structure_file)
    report = runner.run(request)
    runtime = report.runtime
    assert runtime is not None
    assert runtime.reasoning_engine == "baseline"
    assert runtime.mutation_modeler == "local_side_chain"
    assert runtime.llm_provider is None
    assert "gemmi" in runtime.external_tools


def test_health_reports_component_status(tmp_path: Path) -> None:
    upload_dir = tmp_path / ".psf_uploads"
    upload_dir.mkdir()
    client = TestClient(create_app(create_default_runner(), upload_dir=upload_dir))
    data = client.get("/health").json()
    assert data["status"] == "ok"
    assert "components" in data
    assert "reasoning_engine" in data["components"]


def test_cloud_provider_failure_is_logged_not_suppressed(
    monkeypatch, caplog
) -> None:
    from psf_reasoner.physical.cloud_provider import CloudEvidenceProvider

    class BrokenAdapter:
        def fpocket(self, structure):
            raise RuntimeError("boom: http://cloud.internal")

        def coulomb(self, structure):
            raise RuntimeError("also broken")

    from psf_reasoner.schemas.inputs import StructureInput

    provider = CloudEvidenceProvider(adapter=BrokenAdapter())
    with caplog.at_level(logging.WARNING, logger="psf_reasoner.physical.cloud_provider"):
        items = provider.collect(_simple_request(Path("/nonexistent.pdb")))
    assert items == ()
    assert "fpocket" in caplog.text or "cloud" in caplog.text.lower()
    # The failure reason must be logged, but never structure contents.
    assert "ATOM" not in caplog.text
```

`_simple_request(path)` helper 构造 `AnalysisRequest`(structure=StructureInput(path=...)、ligand MK1、mutation V82A)。

- [ ] **Step 2: 运行确认失败**:`pytest tests/test_component_status.py -v` → 属性/行为 FAIL。

- [ ] **Step 3: 实现 component_status.py、ReportRuntime、runner 注入、bootstrap 接线**
  - `component_status.py` 如接口所述(RLock + dict;`snapshot()` 返回 `{name: status.to_dict()}`)。
  - `schemas/report.py` 加:

```python
class ReportRuntime(ScientificModel):
    reasoning_engine: str
    mutation_modeler: str
    llm_provider: str | None = None
    cloud_adapter: str | None = None
    external_tools: dict[str, str] = Field(default_factory=dict)
    component_status: dict[str, dict[str, object]] = Field(default_factory=dict)


class PSFReport(ScientificModel):
    ...
    runtime: ReportRuntime | None = None
```

  - `AnalysisRunner.__init__(..., runtime_factory=None)`;`run()` 里 `report = self._execution.execute(...)`,若 factory 非空:`report = report.model_copy(update={"runtime": self._runtime_factory()})`,再 save。
  - bootstrap:
    - `create_default_service`:构造后注册 `reasoning_engine`(implementation="llm:deepseek"/"llm:anthropic"/"baseline",enabled 按是否启用 LLM)、`mutation_modeler`(foldx/local)、`cloud_adapter`(enabled=URL 是否配置,implementation=base_url 或 "disabled",available 未知时先记 "unknown",由 CloudEvidenceProvider 首次调用后更新)。
    - `_auto_llm_provider` 的 `except Exception` → `logger.warning("LLM provider %r unavailable, falling back to baseline: %s", provider_name, exc)` + 注册 llm 状态 available=False。
    - `create_default_runner`:`runtime_factory=partial(_build_runtime)`;`_build_runtime()` 从 `component_registry.snapshot()` + `gemmi.version_info()` + foldx 版本(registry 里 foldx detail)组装 `ReportRuntime(reasoning_engine=..., mutation_modeler=..., llm_provider=..., cloud_adapter=..., external_tools={"gemmi": version, "foldx": ..., "fpocket": shutil.which("fpocket") and "available" or "not-installed"}, component_status=snapshot)`。
  - CloudEvidenceProvider.collect:每个调用 `try/except Exception as exc: logger.warning("cloud %s unavailable: %s", tool, exc); registry.set(ComponentStatus("cloud_adapter", enabled=True, available=False, implementation=..., detail=str(exc)[:200]))`(不记录结构内容;exc 消息可能含 URL,不含密钥——密钥在 header)。成功后 `available=True`。
  - FoldXMutationModeler:`build()` 的 `except MutationModelingUnavailableError:` 分支改为记录 `logger.info("FoldX unavailable for %s, using local modeler: %s", mutation.notation, exc)`;`__init__` 时注册 foldx 状态(available=which 结果;detail=二进制路径)。`_build_with_foldx` 成功后从 `result.stderr` 首行提取版本字符串存 `self._foldx_version`(默认 "unknown"),并更新注册。
  - openbabel_typing:`_available=False` 与各 `except Exception` 分支 → `logger.debug("OpenBabel typing unavailable: %s", exc)`(一次;模块加载时注册 `openbabel` 状态,避免每原子刷屏——用模块级 `_logged` 标志)。
  - identity.py / structure_qc.py 的 `except Exception: return ...` → 保留返回值语义,补 `logger.debug`(模块级 logger,一次/次均可,含异常类型)。
  - app.py `/health`:

```python
    @api.get("/health")
    def health() -> dict:
        return {"status": "ok", "components": component_registry.snapshot()}
```

- [ ] **Step 4: 兼容性检查**:`PSFReport` 增加可选字段后,现有测试如断言 `model_dump` 精确结构会失败——运行 `pytest -q` 找出并最小化修正断言(加 runtime 字段预期)。`test_schemas.py` 等。

- [ ] **Step 5: 运行验证**:`pytest -q` 全绿;手动:`PSF_LLM=1 PSF_LLM_PROVIDER=bogus .venv/bin/python -c "from psf_reasoner.bootstrap import create_default_runner; create_default_runner()"` 输出 warning 日志。

- [ ] **Step 6: 提交**

```bash
git add src/psf_reasoner/infrastructure/component_status.py src/psf_reasoner/bootstrap.py src/psf_reasoner/application/runner.py src/psf_reasoner/schemas/report.py src/psf_reasoner/physical/cloud_provider.py src/psf_reasoner/physical/modeling.py src/psf_reasoner/physical/openbabel_typing.py src/psf_reasoner/physical/identity.py src/psf_reasoner/physical/structure_qc.py src/psf_reasoner/api/app.py tests/test_component_status.py
git commit -m "fix(observability): log degradations, expose component status, record runtime info

Optional components (LLM, cloud compute, FoldX, OpenBabel) used to
degrade silently via bare 'except Exception' handlers, making
misconfiguration undetectable.  Failures are now logged with reasons
(never API keys or structure contents), a component registry powers
the /health payload, and every report records the reasoning engine,
mutation modeler, cloud adapter and external tool versions used.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 8: 全仓 Ruff 清理 + CI 全仓检查

**Files:**
- Modify: 全部 Ruff 报错文件(230 errors / 50 未格式化文件)
- Modify: `.github/workflows/ci.yml`(全仓 `ruff format --check .` + `ruff check .`,删除 changed-files 逻辑)

- [ ] **Step 1: 自动修复**:`.venv/bin/ruff format .` → `.venv/bin/ruff check --fix .`(仅安全修复)。预期剩余约 100 个需人工处理。

- [ ] **Step 2: 人工清理剩余问题**,原则:
  - 未使用 import → 删除;
  - `B904`(raise 缺少 from)→ 补 `from exc`;
  - `SIM`/`RUF` 建议 → 按建议简化,若与冻结模型/科学逻辑冲突则用精确 `# noqa: <rule>` 并附原因注释(全仓 noqa 新增 < 15 处);
  - 过宽 `except Exception` 保留处(Task 7 已处理核心链路;calibration/evaluation 离线脚本中的)加注释说明为何宽捕获(离线批处理容错),或收窄到具体异常类型;
  - 模糊变量名(如 `l`、`f`)→ 重命名(注意不触碰科学逻辑,仅命名)。
  - `cloud/server.py` 与 `scripts/` 一并纳入全仓检查。

- [ ] **Step 3: CI 改为全仓检查**

```yaml
      - name: Check formatting (ruff)
        run: ruff format --check .
      - name: Lint (ruff)
        run: ruff check .
```

- [ ] **Step 4: 验证**:`.venv/bin/ruff format --check .` 与 `.venv/bin/ruff check .` 退出码 0;`pytest -q` 全绿(尤其 calibration/context/physical 相关测试)。

- [ ] **Step 5: 提交**(按目录分 2-3 个提交:src 核心、calibration/evaluation/benchmarks、cloud/scripts+CI)

```bash
git commit -m "style: repo-wide ruff format + lint cleanup (no behavior changes)

Mechanical formatting and safe autofixes across the repository, plus
manual removal of unused imports, broad-exception annotations, and
ambiguous names.  No scientific logic was changed; CI now checks the
whole repository instead of only the files touched by a PR.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 9: CI 增强(矩阵/覆盖率/缓存/Docker 健康检查)

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `.github/workflows/cloud-build.yml`(构建后运行容器并 curl /health)

- [ ] **Step 1: 测当前覆盖率**:`.venv/bin/python -m pytest --cov=src/psf_reasoner --cov-report=term -q`,记录总分与 api/cloud_compute/uploads/cloud_provider 等关键模块分数。

- [ ] **Step 2: ci.yml 增强**

```yaml
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.12", "3.13"]
    steps:
      - uses: actions/checkout@v4
      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: pip
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]" plip==3.0.1
      - name: Check formatting (ruff)
        run: ruff format --check .
      - name: Lint (ruff)
        run: ruff check .
      - name: Run tests with coverage
        run: pytest --cov=src/psf_reasoner --cov-report=term-missing --cov-fail-under=70
```

阈值取实测值:若当前 < 70,先设 `--cov-fail-under=<实测值-2>`,并在 PR 说明中注明;新增测试应把总分推到 70+ 再定 70(目标:API/存储/云适配器/上传 ≥ 85)。

- [ ] **Step 3: cloud-build.yml 增加运行与健康检查**

```yaml
      - name: Build cloud Docker image
        uses: docker/build-push-action@v6
        with:
          context: ./cloud
          push: false
          tags: psf-cloud-compute:ci
          load: true

      - name: Run container and check /health
        run: |
          docker run -d --name psf-cloud-test -p 8080:8080 psf-cloud-compute:ci
          for i in $(seq 1 30); do
            if curl -fsS http://localhost:8080/health > /tmp/health.json; then break; fi
            sleep 2
          done
          cat /tmp/health.json
          python3 -c "import json; d=json.load(open('/tmp/health.json')); assert d['status']=='ok', d"
          docker logs psf-cloud-test | tail -20
          docker rm -f psf-cloud-test
```

注意 `build-push-action` 需 `load: true` 才能本地 run。

- [ ] **Step 4: 本地验证 Docker**(若本机有 docker):`docker build -t psf-cloud-compute:ci ./cloud` 与 `docker run --rm -p 8080:8080 psf-cloud-compute:ci` + `curl localhost:8080/health`;无 docker 则在 PR 中明确说明依赖 CI 验证。

- [ ] **Step 5: 提交**

```bash
git commit -m "ci: test 3.12/3.13 with coverage gate, pip cache, container health check

The matrix now covers Python 3.12 and 3.13 with cached pip
dependencies and a repository-wide coverage gate.  The cloud-build
workflow builds the image and probes /health inside a running
container.  No test requires real external keys or commercial
software.

Co-Authored-By: Claude Code <noreply@anthropic.com>"
```

---

### Task 10: 拆分五个大文件(纯结构迁移,外部 API 不变)

**Files:** 见各子任务。每个子任务完成后必须:`pytest -q` 全绿 + `ruff format --check .` + `ruff check .` 全绿再提交。

- [ ] **10a. api/app.py → 子模块**
  - Create: `api/upload_service.py`(`SUPPORTED_STRUCTURE_SUFFIXES`、`MAX_UPLOAD_BYTES`、`_store_upload` 改名 `store_upload`;app.py 内保留 `_store_upload = upload_service.store_upload` 兼容别名)
  - Create: `api/input_service.py`(`_resolve_structure_input`、`_resolve_request` → `resolve_structure_input`/`resolve_request`;app.py 保留旧名别名)
  - Create: `api/v3_service.py`(`_build_v3_payload` → `build_v3_payload(runner, request, upload_dir, v3_store)`)
  - Modify: `api/app.py` 仅剩 `create_app`/路由/`app` 与 lifespan;`EXAMPLES_DIR`、`STATIC_DIR`、`UPLOAD_DIR` 常量迁到 `api/paths.py`(或留在 app.py,按引用最少原则:迁到 upload_service/input_service 各自需要的模块,EXAMPLES_DIR 放 input_service)。
  - 测试:`tests/test_api.py`/`test_v3_api.py` 不动(行为不变)。

- [ ] **10b. reasoning/baseline.py → 子包 `reasoning/baseline/`**
  - `__init__.py` 重导出 `BaselineForwardReasoner`/`BaselineReverseReasoner`/`BaselineConsistencyChecker`(bootstrap 与 `reasoning/__init__.py` 的 import 路径不变);
  - `forward.py`(ForwardReasoner 及其机制/功能构造块)、`reverse.py`、`consistency.py`;
  - `scoring.py`(`_bounded`/`_qualitative`/`_make_score_breakdown`/`_rule_provenance`)、`support.py`(证据支撑 helpers:`_supporting_evidence_for_mechanism`/`_count_supporting_evidence`/`_build_evidence_graph`/`_build_missing_nodes`/`_matching_evidence_ids`/`_measurement_direction`/`_evidence_support_score`/`_function_support_score`/`_function_support_count`/`_reverse_evidence_support`/`_consistency_bonus`)。
  - 分层注释:forward.py 内按「机制层构造 / 功能层构造 / 验证计划」加节注释;物理层支撑逻辑集中在 support.py。**禁止**改变任何打分常数与判定顺序;两处不一致的 `type_map` 保持原样(在 PR 中作为已知问题记录,不擅自合并)。
  - 删除旧 `baseline.py`(改名由 git 追踪)。

- [ ] **10c. reasoning/mechanism_generator.py → 子包 `reasoning/mechanism_generator/`**
  - `__init__.py` 重导出 `MechanismGenerator`;`generator.py`(generate 主流程)、`nodes.py`(`_build_*_nodes` 五个方法 + `_volume`)、`paths.py`(`_extract_paths`/`_dfs_paths`/`_extract_uncertainties`)。方法改为接收/返回与原来相同的数据;类内部实现经子模块函数组织(方法体搬入 `nodes.py` 的模块级函数,generator 方法委托)。app.py 与 test_literature_integrity.py 的 import 路径不变。

- [ ] **10d. physical/interactions.py → 子包 `physical/interactions/`**
  - `__init__.py` 重导出公共面:`analyze_typed_interactions`、`count_typed_interactions`、`describe_ligand_atom_types`、`InteractionCounts`、`cutoff_sensitivity_analysis` 及被测试 import 的 `_ligand_bond_graph`、`_type_ligand_atom`(保持名字,即使以别名形式);
  - `typing.py`(原子分类常量+`_type_protein_atom`/`_type_ligand_atom`/`describe_ligand_atom_types`)、`contacts.py`(`_forms_hydrogen_bond`/`_forms_salt_bridge`/`_pi_interaction`/`_water_bridge_events`)、`geometry.py`(氢键几何/质心/重原子)、`graph.py`(配体键图)、`sensitivity.py`(`_classify_stability`/`cutoff_sensitivity_analysis`)、`analysis.py`(`InteractionCounts`/`analyze_typed_interactions`/`count_typed_interactions` 组装)。提取 5 种 interaction_type 字符串为模块级常量(值不变,消除散落字面量)。
  - 外部 import(`physical/energy.py`、`physical/comparison.py`、`physical/preparation.py`、`evaluation/external_validation.py`、`tests/*`)路径不变。

- [ ] **10e. api/static/app.js → ES 模块**
  - Create: `api/static/modules/api.js`(fetch 封装 `api()`)、`viewer.js`(initViewer/loadPDB/applyHighlights/showStructurePanel)、`render.js`(renderQC/renderIdentity/renderLiterature/renderContext/renderCausalGraph/renderLocalization/renderGapAnalysis/renderSummary/renderReport 及渲染原语 metricEl/section/evidenceCard/qualLabel/esc/num)、`form.js`(表单/示例/模式切换事件与 runJsonRequest)、`main.js`(入口:els 缓存、加载动画、事件绑定、/health 探活,export 挂载);
  - Modify: `index.html`:`<script src="/client/i18n.js?v=v1"></script>` 保留 + `<script type="module" src="/client/modules/main.js?v=v6"></script>`(i18n 仍为全局 `window.PSF_I18N`,modules 内包装回退逻辑);
  - 删除旧 `app.js`;`app.js` 内部依赖的 DOM id 与 API 端点逐一核对(agent 报告清单),全部保持。
  - 验证:每个模块 `node --check` 语法通过;`pytest tests/test_api.py -q`(workbench/静态文件服务测试)通过;TestClient 请求 `/client/modules/main.js` 返回 200 且 content-type 正确(js→text/javascript,StaticFiles 默认)。

- [ ] **收尾:最终验证 + 提交**(10a-10e 各自独立提交,消息如 `refactor(api): split app.py into upload/input/v3 service modules` 等,均带 Co-Authored-By 行)。

---

## 最终验收清单(全部实测后写入 PR 说明)

1. `pytest -q` 的 passed/skipped/failed 计数;
2. 总覆盖率与 api、infrastructure(cloud_compute/uploads/v3_repository)、physical/cloud_provider 关键模块覆盖率;
3. `ruff format --check .` 退出码;
4. `ruff check .` 退出码;
5. 仅正式依赖 venv 中 `python scripts/smoke_prod_imports.py` 结果;
6. Docker 镜像构建 + `/health`(本地 docker 可用则实测,否则 CI 验证并在 PR 注明);
7. 端到端:内置示例(1sdt.cif/1sdv.cif)一次真实 V3 分析与 JSON/CSV/PyMOL 导出;
8. 服务重启(新 app 实例)后按 report_id 重新导出;
9. 路径穿越/未授权云请求/超大上传被正确拒绝(对应测试通过);
10. PR 说明包含:修改前问题、修改后行为、安全影响、数据库迁移/兼容性说明、测试证据、未完成事项及原因(例如:限流为每实例内存实现;`--allow-unauthenticated` 保留原因;type_map 两处不一致为遗留问题不在本 PR 合并;后台任务系统留待 PR2)。
