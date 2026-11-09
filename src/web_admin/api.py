"""API FastAPI para el panel de administración CCE-M5."""

from __future__ import annotations

import asyncio
import contextlib
import json as _json
import logging
import os
import subprocess
import tempfile
import urllib.request
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from src import db_manager
from src.config import settings
from src.web_admin import models as m
from src.web_admin.auth import (
    authenticate_user,
    change_user_password,
    create_access_token,
    create_new_user,
    get_current_user,
    require_admin,
    seed_default_admin,
)
from src.web_admin.config import (
    DB_PATH,
    GITHUB_COMENTARIOS_OWNER,
    GITHUB_COMENTARIOS_REPO,
    GITHUB_TOKEN_COMENTARIOS,
)
from src.web_admin.database import (
    WORKFLOW_STEPS,
    add_workflow_log,
    checkpoint_wal,
    count_admins,
    create_workflow_run,
    delete_user,
    get_backups_for_date,
    get_latest_workflow_run,
    get_user_by_id,
    get_workflow_logs,
    get_workflow_run,
    goto_workflow_step,
    init_admin_schema,
    list_users,
    list_workflow_runs,
    next_step,
    supersede_workflow_run,
    update_user,
)
from src.web_admin.health import full_health_report
from src.web_admin.models import ComentarioRequest
from src.web_admin.rate_limit import IPRateLimiter, LoginRateLimiter
from src.web_admin.workflow_engine import run_step

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_admin_schema()
    seed_default_admin()
    yield
    # Cierre endurecido: consolida el WAL en el main file aunque alguna
    # conexión se haya quedado abierta. Best-effort: un fallo aquí no debe
    # interrumpir el shutdown.
    try:
        checkpoint_wal()
    except Exception as exc:
        logger.warning("lifespan: no se pudo checkpointear el WAL al cerrar: %s", exc)


app = FastAPI(
    title="CCE-M5 Admin API",
    description="API de administración para el workflow manual de presentaciones litúrgicas.",
    version="1.0.0",
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).parent / "static"

# ------------------------------------------------------------------
# Editores legacy Flask montados bajo FastAPI
# ------------------------------------------------------------------
with contextlib.suppress(ImportError):
    from scripts.editor_acordes_server import app_editor_acordes
    from scripts.editor_diapositivas_server import app_editor_diapositivas
    from src.web_admin.wsgi_adapter import PrefixedWSGIMiddleware

    app.add_route(
        "/editor-acordes/{path:path}",
        PrefixedWSGIMiddleware(app_editor_acordes, prefix="/editor-acordes"),
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        include_in_schema=False,
    )
    app.add_route(
        "/editor-diapositivas/{path:path}",
        PrefixedWSGIMiddleware(app_editor_diapositivas, prefix="/editor-diapositivas"),
        methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"],
        include_in_schema=False,
    )

# ------------------------------------------------------------------
# Redirecciones de compatibilidad para URLs absolutas antiguas de editores
# montados bajo FastAPI. Útil mientras caches de navegador o bookmarks
# siguen apuntando a rutas de la raíz. NO deben capturar endpoints propios
# de la API FastAPI.
# ------------------------------------------------------------------


@app.get("/cancionero/{path:path}", include_in_schema=False)
async def redirect_cancionero(path: str):
    return RedirectResponse(url=f"/editor-acordes/cancionero/{path}", status_code=307)


@app.get("/slides/{path:path}", include_in_schema=False)
async def redirect_slides(path: str):
    return RedirectResponse(url=f"/editor-diapositivas/slides/{path}", status_code=307)


@app.get("/presentaciones/", include_in_schema=False)
async def redirect_presentaciones_root():
    return RedirectResponse(url="/editor-diapositivas/presentaciones/", status_code=307)


@app.get("/presentacion/{fecha}/armar", include_in_schema=False)
@app.get("/presentacion/{fecha}/asignar", include_in_schema=False)
@app.get("/presentacion/{fecha}/preview", include_in_schema=False)
@app.get("/presentacion/{fecha}/generar", include_in_schema=False)
@app.get("/presentacion/{fecha}/reconstruir", include_in_schema=False)
async def redirect_presentacion_operaciones(fecha: str, request: Request):
    return RedirectResponse(url=f"/editor-diapositivas{request.url.path}", status_code=307)


@app.get("/canciones/nueva", include_in_schema=False)
async def redirect_canciones_nueva():
    return RedirectResponse(url="/editor-diapositivas/canciones/nueva", status_code=307)


# CORS permitido para el origen local del panel admin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Rate limiting global por IP (excluye health y archivos estáticos/admin).
_ip_rate_limiter = IPRateLimiter(max_requests=120, window_seconds=60)


@app.middleware("http")
async def ip_rate_limit_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith(("/health", "/admin", "/static")):
        return await call_next(request)
    try:
        _ip_rate_limiter.check_or_raise(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/admin/")


@app.get("/admin", include_in_schema=False)
async def admin_root():
    return RedirectResponse(url="/admin/")


@app.get("/admin/", include_in_schema=False)
async def admin_index():
    return FileResponse(STATIC_DIR / "admin" / "index.html")


@app.get("/admin/login", include_in_schema=False)
async def admin_login_root():
    return RedirectResponse(url="/admin/login.html")


@app.get("/admin/login.html", include_in_schema=False)
async def admin_login_html():
    return FileResponse(STATIC_DIR / "admin" / "login.html")


@app.get("/health", response_model=dict)
async def health():
    """Healthcheck que incluye accesibilidad de BD y web estática."""
    return full_health_report()


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception("Error no controlado en API")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


_rate_limiter = LoginRateLimiter()
_comentarios_limiter = IPRateLimiter(
    max_requests=settings.comentarios_rate_limit_max, window_seconds=3600.0
)


@app.post("/auth/login", response_model=m.TokenResponse)
async def login(request: Request, payload: m.LoginRequest):
    _rate_limiter.check_or_raise(request, payload.username)
    user = authenticate_user(payload.username, payload.password)
    if not user:
        _rate_limiter.record_failure(request, payload.username)
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    _rate_limiter.record_success(request, payload.username)
    token = create_access_token(user["username"], user["role"])
    return m.TokenResponse(
        access_token=token,
        role=user["role"],
        full_name=user.get("full_name"),
    )


@app.get("/auth/me", response_model=m.UserProfile)
async def me(current_user: dict[str, Any] = Depends(get_current_user)):
    return m.UserProfile(**current_user)


@app.post("/comentarios", response_model=dict)
async def crear_comentario(
    request: Request,
    payload: ComentarioRequest,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Recibe un comentario de la web y crea un issue en GitHub vía proxy.

    Requiere autenticación (401 sin token). El token de GitHub nunca se expone
    al navegador; se lee del servidor. Limitado por IP (por defecto 5/hora,
    CCE_ADMIN_COMENTARIOS_RATE_LIMIT_MAX) y el issue público no incluye el
    email del visitante.
    """
    _comentarios_limiter.check_or_raise(request)
    if not GITHUB_TOKEN_COMENTARIOS:
        logger.warning("Intento de comentario sin GITHUB_TOKEN_COMENTARIOS configurado")
        raise HTTPException(status_code=503, detail="Servicio de comentarios no configurado")

    tipo_label = {
        "sugerencia": "🎵 Sug. musical",
        "correccion": "✏️ Corrección",
        "otro": "💬 Otro",
    }.get(payload.tipo, "💬 Otro")
    title = f"[Comentario] {tipo_label}{f' - Domingo {payload.presentacion}' if payload.presentacion else ''}".strip()
    body = (
        f"**Autor**: {payload.nombre or 'Anónimo'}\n"
        f"**Tipo**: {tipo_label}\n"
        f"**Presentación**: {payload.presentacion or 'No especificada'}\n"
        f"**Mensaje**:\n{payload.mensaje}"
    )

    data = _json.dumps(
        {"title": title, "body": body, "labels": ["web-comment", "pendiente"]}
    ).encode("utf-8")
    url = (
        f"https://api.github.com/repos/{GITHUB_COMENTARIOS_OWNER}/{GITHUB_COMENTARIOS_REPO}/issues"
    )
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {GITHUB_TOKEN_COMENTARIOS}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            resp.read()
    except urllib.error.HTTPError as exc:
        logger.error("GitHub rechazó el comentario: %s %s", exc.code, exc.reason)
        raise HTTPException(
            status_code=502, detail="No se pudo enviar el comentario a GitHub"
        ) from exc
    except Exception as exc:
        logger.exception("Error enviando comentario a GitHub")
        raise HTTPException(status_code=502, detail="Error de conexión con GitHub") from exc

    return {"success": True, "message": "Comentario recibido"}


# ---------------------------------------------------------------------------
# Deploy a GitHub Pages (solo admin)
# ---------------------------------------------------------------------------

DEPLOY_REPO = "CC5M5/CCE-M5"
DEPLOY_WORKFLOW = "deploy.yml"
DEPLOY_DISPATCH_URL = (
    f"https://api.github.com/repos/{DEPLOY_REPO}/actions/workflows/{DEPLOY_WORKFLOW}/dispatches"
)
PUBLISH_SEED_FILE = "data/seeds/db.empty.sqlite3"
PUBLISH_COMMIT_MESSAGE = "chore(seed): actualizar seed canónica desde el panel admin"


class GithubApiError(Exception):
    """Error de la API de GitHub con código HTTP y detalle legible."""

    def __init__(self, status_code: int, detail: Any):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _github_api_request(
    url: str, *, method: str = "GET", payload: dict[str, Any] | None = None
) -> httpx.Response:
    """Ejecuta una petición a la API de GitHub con el token configurado.

    El token se usa el mismo de comentarios (GITHUB_TOKEN_CC5M5). Lanza
    GithubApiError si el token falta (503) o si GitHub responde con 4xx/5xx;
    los fallos de red se propagan como httpx.HTTPError.
    """
    if not GITHUB_TOKEN_COMENTARIOS:
        raise GithubApiError(
            503,
            "GITHUB_TOKEN_CC5M5 no está configurado en el servidor.",
        )
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {GITHUB_TOKEN_COMENTARIOS}",
    }
    response = httpx.request(url, method=method, headers=headers, json=payload, timeout=20.0)
    if response.status_code >= 400:
        raise GithubApiError(response.status_code, _github_error_detail(response))
    return response


def _github_error_detail(response: httpx.Response) -> str:
    """Extrae el mensaje de error de una respuesta de la API de GitHub."""
    try:
        data = response.json()
        message = str(data.get("message", ""))[:300]
        return message or response.text[:300]
    except Exception:
        return response.text[:300]


def _seed_sync_module():
    """Carga scripts/seed_sync.py.

    En pruebas el paquete es importable directamente (pythonpath incluye
    scripts/); en producción se carga por archivo desde el directorio del
    proyecto para no depender del sys.path.
    """
    try:
        import seed_sync

        return seed_sync
    except ModuleNotFoundError:
        import importlib.util

        script_path = settings.project_dir / "scripts" / "seed_sync.py"
        spec = importlib.util.spec_from_file_location("cce_seed_sync", script_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module


def _checkpoint_source_db() -> None:
    """Checkpoint WAL para que el main file de la BD refleje todo el contenido."""
    conn = db_manager.create_connection(DB_PATH)
    try:
        conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    finally:
        conn.close()


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Ejecuta un comando git en la raíz del proyecto (sin check)."""
    return subprocess.run(
        ["git", *args],
        cwd=settings.project_dir,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def _seed_status() -> dict[str, Any]:
    """Estado de la seed canónica (frescura y validez de la BD de origen).

    La seed se considera "al día" cuando la forma canónica de la BD de origen
    (sin tablas de runtime, compactada) coincide con la seed actual. No
    comparamos el archivo crudo con la seed: la seed nunca es idéntica al
    working DB porque se limpia y se compacta al generarse.
    """
    seed_sync = _seed_sync_module()
    seed_path = Path(seed_sync.SEED_PATH)
    source_path = Path(seed_sync.SOURCE_PATH)
    try:
        _checkpoint_source_db()
    except Exception:
        logger.exception("No se pudo hacer checkpoint WAL de la BD de origen")
    try:
        errors = seed_sync._validate_source(source_path)
    except Exception as exc:
        errors = [f"No se pudo validar la BD de origen: {exc}"]

    exists = seed_path.exists()
    up_to_date = False
    if exists and not errors and source_path.exists():
        tmp: Path | None = None
        try:
            fd, tmp_name = tempfile.mkstemp(suffix=".sqlite3", prefix="seed_canon_")
            os.close(fd)
            tmp = Path(tmp_name)
            seed_sync._build_canonical_seed(source_path, tmp)
            up_to_date = tmp.read_bytes() == seed_path.read_bytes()
        except Exception:
            logger.exception("No se pudo construir la seed canónica provisional")
        finally:
            if tmp is not None:
                with contextlib.suppress(OSError):
                    tmp.unlink()

    return {
        "exists": exists,
        "up_to_date": up_to_date,
        "valid": not errors,
        "errors": errors,
    }


def _git_status() -> dict[str, Any]:
    """Estado git local: si es repo y rama actual."""
    try:
        repo_check = _git("rev-parse", "--is-inside-work-tree")
    except (subprocess.SubprocessError, OSError):
        return {"is_repo": False, "branch": None}
    if repo_check.returncode != 0:
        return {"is_repo": False, "branch": None}
    branch = None
    try:
        branch_check = _git("rev-parse", "--abbrev-ref", "HEAD")
        if branch_check.returncode == 0:
            branch = branch_check.stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        pass
    return {"is_repo": True, "branch": branch}


@app.post("/admin/deploy")
async def admin_deploy(current_user: dict[str, Any] = Depends(require_admin)):
    """Dispara workflow_dispatch del workflow deploy.yml sobre main.

    GitHub ejecuta lint-and-test → build → deploy-pages y publica el sitio.
    """
    try:
        _github_api_request(DEPLOY_DISPATCH_URL, method="POST", payload={"ref": "main"})
    except GithubApiError as exc:
        mapped = exc.status_code if exc.status_code in (403, 404, 503) else 502
        raise HTTPException(
            status_code=mapped,
            detail=f"Error en la petición a GitHub: {exc.detail}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Error de conexión con GitHub: {exc}") from exc
    return {
        "triggered": True,
        "ref": "main",
        "workflow": DEPLOY_WORKFLOW,
        "repo": DEPLOY_REPO,
        "run": {"html_url": f"https://github.com/{DEPLOY_REPO}/actions/workflows/{DEPLOY_WORKFLOW}"},
    }


@app.get("/admin/deploy/status")
async def admin_deploy_status(current_user: dict[str, Any] = Depends(require_admin)):
    """Estado del despliegue: última ejecución, seed canónica y git local."""
    latest_run = None
    runs_url = (
        f"https://api.github.com/repos/{DEPLOY_REPO}/actions/workflows/{DEPLOY_WORKFLOW}"
        f"/runs?per_page=1&branch=main"
    )
    try:
        data = _github_api_request(runs_url)
        data = data.json() if isinstance(data, httpx.Response) else data
        runs = data.get("workflow_runs", [])
        if runs:
            run = runs[0]
            latest_run = {
                "status": run.get("status"),
                "conclusion": run.get("conclusion"),
                "head_branch": run.get("head_branch"),
                "created_at": run.get("created_at"),
                "html_url": run.get("html_url"),
            }
    except (GithubApiError, httpx.HTTPError):
        latest_run = None
    return {
        "deploy": {
            "repo": DEPLOY_REPO,
            "workflow": DEPLOY_WORKFLOW,
            "latest_run": latest_run,
        },
        "seed": _seed_status(),
        "git": _git_status(),
    }


@app.post("/admin/publish")
async def admin_publish(current_user: dict[str, Any] = Depends(require_admin)):
    """Publica el estado local: seed canónica + commit + push a main.

    Sincroniza data/db.sqlite3 → data/seeds/db.empty.sqlite3 vía
    scripts/seed_sync.py, comite la seed (respetando .gitignore) y hace
    push a origin main; el workflow de GitHub Pages se ejecuta con el push.
    """
    # Verificar que el token puede acceder al repo antes de publicar.
    try:
        _github_api_request(f"https://api.github.com/repos/{DEPLOY_REPO}")
    except GithubApiError as exc:
        mapped = exc.status_code if exc.status_code in (403, 404, 503) else 502
        raise HTTPException(
            status_code=mapped,
            detail=f"GitHub no permite publicar: {exc.detail}",
        ) from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Error de conexión con GitHub: {exc}") from exc

    branch_check = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch_check.returncode != 0:
        raise HTTPException(status_code=409, detail="El directorio no es un repositorio git.")
    branch = branch_check.stdout.strip()
    if branch != "main":
        raise HTTPException(
            status_code=409,
            detail=f"Estás en la rama '{branch}'; la publicación requiere estar en 'main'.",
        )

    seed_sync = _seed_sync_module()
    _checkpoint_source_db()
    source_errors = seed_sync._validate_source(seed_sync.SOURCE_PATH)
    if source_errors:
        raise HTTPException(
            status_code=409,
            detail="La base de datos de origen no es válida para la seed: " + "; ".join(source_errors),
        )

    seed_sync._apply_sync()

    status_check = _git("status", "--porcelain")
    changed = sorted(
        {
            line[3:].strip()
            for line in status_check.stdout.splitlines()
            if line and line[3:].strip() == PUBLISH_SEED_FILE
        }
    )
    if not changed:
        return {"committed": False, "pushed": False, "files": []}

    _git("add", "--", *changed)
    _git("commit", "-m", PUBLISH_COMMIT_MESSAGE)
    push = _git("push", "origin", "main")
    if push.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"git push falló: {push.stderr.strip()[:300] or push.stdout.strip()[:300]}",
        )
    return {
        "committed": True,
        "pushed": True,
        "files": changed,
        "commit_message": PUBLISH_COMMIT_MESSAGE,
    }


# ---------------------------------------------------------------------------
# Usuarios (solo admin)
# ---------------------------------------------------------------------------


@app.get("/users", response_model=list[m.UserProfile])
async def get_users(current_user: dict[str, Any] = Depends(require_admin)):
    rows = list_users()
    return [m.UserProfile(**r) for r in rows]


@app.post("/users", response_model=m.UserProfile)
async def create_user_endpoint(
    payload: m.UserCreate,
    current_user: dict[str, Any] = Depends(require_admin),
):
    if payload.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Rol debe ser admin o viewer")
    try:
        user_id = create_new_user(
            username=payload.username,
            password=payload.password,
            full_name=payload.full_name,
            role=payload.role,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    user = get_user_by_id(user_id)
    assert user is not None
    return m.UserProfile(
        id=user.id,
        username=user.username,
        full_name=user.full_name,
        role=user.role,
        is_active=1 if user.is_active else 0,
    )


@app.patch("/users/{user_id}", response_model=m.UserProfile)
async def update_user_endpoint(
    user_id: int,
    payload: m.UserUpdate,
    current_user: dict[str, Any] = Depends(require_admin),
):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if payload.role is not None and payload.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Rol debe ser admin o viewer")
    if (
        target.role == "admin"
        and (payload.role == "viewer" or payload.is_active is False)
        and count_admins() <= 1
    ):
        raise HTTPException(
            status_code=409, detail="No se puede eliminar el último administrador activo"
        )
    update_user(
        user_id,
        full_name=payload.full_name,
        role=payload.role,
        is_active=payload.is_active,
    )
    updated = get_user_by_id(user_id)
    assert updated is not None
    return m.UserProfile(
        id=updated.id,
        username=updated.username,
        full_name=updated.full_name,
        role=updated.role,
        is_active=1 if updated.is_active else 0,
    )


@app.delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: dict[str, Any] = Depends(require_admin),
):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.id == current_user["id"]:
        raise HTTPException(status_code=409, detail="No puedes eliminar tu propio usuario")
    if target.role == "admin" and count_admins() <= 1:
        raise HTTPException(
            status_code=409, detail="No se puede eliminar el último administrador activo"
        )
    delete_user(user_id)
    return {"detail": "Usuario eliminado"}


# ---------------------------------------------------------------------------
# Cambio de contraseña propio
# ---------------------------------------------------------------------------


@app.post("/auth/change-password")
async def change_password(
    payload: m.PasswordChange,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    user = get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not authenticate_user(user.username, payload.current_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    if len(payload.new_password) < 4:
        raise HTTPException(
            status_code=400, detail="La nueva contraseña debe tener al menos 4 caracteres"
        )
    change_user_password(user.id, payload.new_password)
    return {"detail": "Contraseña actualizada"}


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


@app.get("/workflows")
async def workflows_index(
    fecha: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict[str, Any] = Depends(require_admin),
):
    rows = list_workflow_runs(fecha_domingo=fecha, limit=limit)
    return {"workflows": [m.WorkflowRun(**r) for r in rows]}


@app.get("/workflows/{workflow_id}")
async def workflow_detail(
    workflow_id: int,
    current_user: dict[str, Any] = Depends(require_admin),
):
    wf = get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    logs = get_workflow_logs(workflow_id)
    from src.web_admin.database import next_step

    can_advance = wf["current_step"] != "done" and next_step(wf["current_step"]) is not None
    return m.WorkflowResponse(
        workflow=m.WorkflowRun(**wf),
        logs=[m.WorkflowLogEntry(**r) for r in logs],
        can_advance=can_advance,
        next_step_name=next_step(wf["current_step"]),
    )


@app.post("/workflows", response_model=m.WorkflowResponse)
async def workflow_create(
    payload: m.WorkflowCreate,
    current_user: dict[str, Any] = Depends(require_admin),
):
    fecha = payload.fecha_domingo
    existing = get_latest_workflow_run(fecha)
    warning: str | None = None

    if existing and existing["status"] != "superseded":
        if not payload.force:
            raise HTTPException(
                status_code=409,
                detail=(
                    f"Ya existe un workflow activo para {fecha}. "
                    "Usa force=true para regenerar y crear backup."
                ),
            )
        warning = f"Workflow anterior {existing['id']} marcado como superseded"

    workflow_id = create_workflow_run(
        fecha_domingo=fecha,
        created_by=current_user["username"],
        steps_data={"fecha": fecha},
    )

    if existing and existing["status"] != "superseded":
        supersede_workflow_run(existing["id"], workflow_id)

    add_workflow_log(workflow_id, "init", f"Workflow creado por {current_user['username']}")
    wf = get_workflow_run(workflow_id)
    if wf is None:
        raise HTTPException(status_code=500, detail="No se pudo recargar el workflow")
    logs = get_workflow_logs(workflow_id)
    return m.WorkflowResponse(
        workflow=m.WorkflowRun(**wf),
        logs=[m.WorkflowLogEntry(**r) for r in logs],
        can_advance=True,
        next_step_name="fetch_lectures",
        warning=warning,
    )


@app.post("/workflows/{workflow_id}/goto-step", response_model=m.WorkflowResponse)
async def workflow_goto_step(
    workflow_id: int,
    payload: m.WorkflowGotoStep,
    current_user: dict[str, Any] = Depends(require_admin),
):
    """Mueve el workflow a un paso arbitrario para permitir re-edición o re-publicación."""
    wf = get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    if payload.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="workflow_id inconsistente")

    if payload.step not in WORKFLOW_STEPS:
        raise HTTPException(status_code=400, detail=f"Paso no válido: {payload.step}")

    goto_workflow_step(workflow_id, payload.step)
    add_workflow_log(
        workflow_id,
        payload.step,
        f"Movido manualmente al paso {payload.step} por {current_user['username']}",
    )
    updated = get_workflow_run(workflow_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="No se pudo recargar el workflow")
    logs = get_workflow_logs(workflow_id)
    can_advance = (
        updated["current_step"] != "done" and next_step(updated["current_step"]) is not None
    )
    return m.WorkflowResponse(
        workflow=m.WorkflowRun(**updated),
        logs=[m.WorkflowLogEntry(**r) for r in logs],
        can_advance=can_advance,
        next_step_name=next_step(updated["current_step"]),
    )


@app.post("/workflows/{workflow_id}/advance")
async def workflow_advance(
    workflow_id: int,
    payload: m.WorkflowAdvance,
    current_user: dict[str, Any] = Depends(require_admin),
):
    wf = get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    if payload.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="workflow_id inconsistente")

    result = await asyncio.to_thread(run_step, workflow_id, payload.action, payload.data or {})
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Error desconocido"))

    return m.WorkflowResponse(
        workflow=m.WorkflowRun(**result["workflow"]),
        logs=[m.WorkflowLogEntry(**r) for r in result["logs"]],
        can_advance=result["can_advance"],
        next_step_name=result.get("next_step_name"),
        warning=result.get("warning"),
    )


@app.get("/canciones", response_model=list[m.CancionResponse])
async def list_canciones_endpoint(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Lista todas las canciones del cancionero."""
    from src.canciones_manager import listar_canciones

    return listar_canciones()


@app.post("/canciones", response_model=m.CancionResponse, status_code=201)
async def create_cancion_endpoint(
    payload: m.CancionCreate,
    current_user: dict[str, Any] = Depends(require_admin),
):
    """Crea una nueva canción en el cancionero."""
    from src.canciones_manager import CancionCreateUpdate, crear_cancion
    from src.rebuild_web import rebuild_web

    try:
        cancion = crear_cancion(
            CancionCreateUpdate(
                titulo=payload.titulo,
                letra_con_acordes=payload.letra_con_acordes,
                momentos=payload.momentos,
                tono=payload.tono,
                fuente=payload.fuente,
            )
        )
        await asyncio.to_thread(rebuild_web)
        return cancion
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/canciones/{cancion_id}", response_model=m.CancionResponse)
async def get_cancion_endpoint(
    cancion_id: int,
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Devuelve una canción por ID."""
    from src.canciones_manager import obtener_cancion

    try:
        return obtener_cancion(cancion_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.patch("/canciones/{cancion_id}", response_model=m.CancionResponse)
async def update_cancion_endpoint(
    cancion_id: int,
    payload: m.CancionUpdate,
    current_user: dict[str, Any] = Depends(require_admin),
):
    """Actualiza una canción existente."""
    from src.canciones_manager import CancionCreateUpdate, actualizar_cancion, obtener_cancion
    from src.rebuild_web import rebuild_web

    try:
        existing = obtener_cancion(cancion_id)
        cancion = actualizar_cancion(
            cancion_id,
            CancionCreateUpdate(
                titulo=payload.titulo if payload.titulo is not None else existing["titulo"],
                letra_con_acordes=payload.letra_con_acordes
                if payload.letra_con_acordes is not None
                else existing["letra_con_acordes"] or "",
                momentos=payload.momentos if payload.momentos is not None else existing["momentos"],
                tono=payload.tono if payload.tono is not None else existing["tono"],
                fuente=payload.fuente if payload.fuente is not None else existing["fuente"],
            ),
        )
        await asyncio.to_thread(rebuild_web)
        return cancion
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/canciones/{cancion_id}")
async def delete_cancion_endpoint(
    cancion_id: int,
    current_user: dict[str, Any] = Depends(require_admin),
):
    """Elimina una canción del cancionero."""
    from src.canciones_manager import eliminar_cancion

    try:
        eliminar_cancion(cancion_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"detail": "Canción eliminada"}


@app.get("/workflows/{workflow_id}/backups")
async def workflow_backups(
    workflow_id: int,
    current_user: dict[str, Any] = Depends(require_admin),
):
    wf = get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    rows = get_backups_for_date(wf["fecha_domingo"])
    return {"backups": rows}


# ---------------------------------------------------------------------------
# Datos auxiliares
# ---------------------------------------------------------------------------


@app.get("/presentacion/fechas")
async def fechas_presentaciones(
    current_user: dict[str, Any] = Depends(get_current_user),
):
    """Devuelve las fechas de presentaciones ya publicadas (visible para viewer)."""
    from src.db_manager import get_connection

    with contextlib.closing(get_connection()) as conn:
        rows = conn.execute(
            "SELECT fecha_domingo FROM presentaciones ORDER BY fecha_domingo DESC"
        ).fetchall()
    return {"fechas": [r["fecha_domingo"] for r in rows]}
