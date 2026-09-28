"""API FastAPI para el panel de administración CCE-M5."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from src.web_admin.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    require_admin,
    security,
    seed_default_admin,
)
from src.web_admin import models as m
from src.web_admin.database import (
    add_workflow_log,
    create_workflow_run,
    get_backups_for_date,
    get_latest_workflow_run,
    get_workflow_logs,
    get_workflow_run,
    init_admin_schema,
    list_users,
    list_workflow_runs,
    supersede_workflow_run,
)
from src.web_admin.workflow_engine import run_step

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_admin_schema()
    seed_default_admin()
    yield


app = FastAPI(
    title="CCE-M5 Admin API",
    description="API de administración para el workflow manual de presentaciones litúrgicas.",
    version="1.0.0",
    lifespan=lifespan,
)

STATIC_DIR = Path(__file__).parent / "static"

# CORS permitido para el origen local del panel admin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4321", "http://192.168.68.244:4321"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.exception("Error no controlado en API")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


@app.post("/auth/login", response_model=m.TokenResponse)
async def login(payload: m.LoginRequest):
    user = authenticate_user(payload.username, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos")
    token = create_access_token(user["username"], user["role"])
    return m.TokenResponse(
        access_token=token,
        role=user["role"],
        full_name=user.get("full_name"),
    )


@app.get("/auth/me", response_model=m.UserProfile)
async def me(current_user: Dict[str, Any] = Depends(get_current_user)):
    return m.UserProfile(**current_user)


# ---------------------------------------------------------------------------
# Usuarios (solo admin)
# ---------------------------------------------------------------------------


@app.get("/users", response_model=List[m.UserProfile])
async def get_users(current_user: Dict[str, Any] = Depends(require_admin)):
    rows = list_users()
    return [m.UserProfile(**r) for r in rows]


# ---------------------------------------------------------------------------
# Workflows
# ---------------------------------------------------------------------------


@app.get("/workflows")
async def workflows_index(
    fecha: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user: Dict[str, Any] = Depends(require_admin),
):
    rows = list_workflow_runs(fecha_domingo=fecha, limit=limit)
    return {"workflows": [m.WorkflowRun(**r) for r in rows]}


@app.get("/workflows/{workflow_id}")
async def workflow_detail(
    workflow_id: int,
    current_user: Dict[str, Any] = Depends(require_admin),
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
    current_user: Dict[str, Any] = Depends(require_admin),
):
    fecha = payload.fecha_domingo
    existing = get_latest_workflow_run(fecha)
    warning: Optional[str] = None

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
    logs = get_workflow_logs(workflow_id)
    return m.WorkflowResponse(
        workflow=m.WorkflowRun(**wf),
        logs=[m.WorkflowLogEntry(**r) for r in logs],
        can_advance=True,
        next_step_name="fetch_lectures",
        warning=warning,
    )


@app.post("/workflows/{workflow_id}/advance")
async def workflow_advance(
    workflow_id: int,
    payload: m.WorkflowAdvance,
    current_user: Dict[str, Any] = Depends(require_admin),
):
    wf = get_workflow_run(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow no encontrado")
    if payload.workflow_id != workflow_id:
        raise HTTPException(status_code=400, detail="workflow_id inconsistente")

    result = run_step(workflow_id, payload.action, payload.data or {})
    if not result.get("success"):
        raise HTTPException(status_code=422, detail=result.get("error", "Error desconocido"))

    return m.WorkflowResponse(
        workflow=m.WorkflowRun(**result["workflow"]),
        logs=[m.WorkflowLogEntry(**r) for r in result["logs"]],
        can_advance=result["can_advance"],
        next_step_name=result.get("next_step_name"),
        warning=result.get("warning"),
    )


@app.get("/workflows/{workflow_id}/backups")
async def workflow_backups(
    workflow_id: int,
    current_user: Dict[str, Any] = Depends(require_admin),
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
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Devuelve las fechas de presentaciones ya publicadas (visible para viewer)."""
    from src.db_manager import get_connection
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT fecha_domingo FROM presentaciones ORDER BY fecha_domingo DESC"
        ).fetchall()
    return {"fechas": [r["fecha_domingo"] for r in rows]}
