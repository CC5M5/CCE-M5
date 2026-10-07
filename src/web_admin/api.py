"""API FastAPI para el panel de administración CCE-M5."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import asyncio
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

from src.web_admin.auth import (
    authenticate_user,
    change_user_password,
    create_access_token,
    create_new_user,
    get_current_user,
    hash_password,
    require_admin,
    security,
    seed_default_admin,
)
from src.web_admin import models as m
from src.web_admin.database import (
    WORKFLOW_STEPS,
    add_workflow_log,
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
    set_user_password,
    supersede_workflow_run,
    update_user,
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
    allow_origins=["http://localhost:4321", "http://192.168.68.244:4321", "http://192.168.68.244:4324", "http://localhost:4324"],
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


@app.post("/users", response_model=m.UserProfile)
async def create_user_endpoint(
    payload: m.UserCreate,
    current_user: Dict[str, Any] = Depends(require_admin),
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
    return m.UserProfile(**{
        "id": user.id,
        "username": user.username,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": 1 if user.is_active else 0,
    })


@app.patch("/users/{user_id}", response_model=m.UserProfile)
async def update_user_endpoint(
    user_id: int,
    payload: m.UserUpdate,
    current_user: Dict[str, Any] = Depends(require_admin),
):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if payload.role is not None and payload.role not in ("admin", "viewer"):
        raise HTTPException(status_code=400, detail="Rol debe ser admin o viewer")
    if target.role == "admin" and (payload.role == "viewer" or payload.is_active is False):
        if count_admins() <= 1:
            raise HTTPException(status_code=409, detail="No se puede eliminar el último administrador activo")
    update_user(
        user_id,
        full_name=payload.full_name,
        role=payload.role,
        is_active=payload.is_active,
    )
    updated = get_user_by_id(user_id)
    assert updated is not None
    return m.UserProfile(**{
        "id": updated.id,
        "username": updated.username,
        "full_name": updated.full_name,
        "role": updated.role,
        "is_active": 1 if updated.is_active else 0,
    })


@app.delete("/users/{user_id}")
async def delete_user_endpoint(
    user_id: int,
    current_user: Dict[str, Any] = Depends(require_admin),
):
    target = get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if target.id == current_user["id"]:
        raise HTTPException(status_code=409, detail="No puedes eliminar tu propio usuario")
    if target.role == "admin" and count_admins() <= 1:
        raise HTTPException(status_code=409, detail="No se puede eliminar el último administrador activo")
    delete_user(user_id)
    return {"detail": "Usuario eliminado"}


# ---------------------------------------------------------------------------
# Cambio de contraseña propio
# ---------------------------------------------------------------------------


@app.post("/auth/change-password")
async def change_password(
    payload: m.PasswordChange,
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    user = get_user_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if not authenticate_user(user.username, payload.current_password):
        raise HTTPException(status_code=401, detail="Contraseña actual incorrecta")
    if len(payload.new_password) < 4:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener al menos 4 caracteres")
    change_user_password(user.id, payload.new_password)
    return {"detail": "Contraseña actualizada"}


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


@app.post("/workflows/{workflow_id}/goto-step", response_model=m.WorkflowResponse)
async def workflow_goto_step(
    workflow_id: int,
    payload: m.WorkflowGotoStep,
    current_user: Dict[str, Any] = Depends(require_admin),
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
    add_workflow_log(workflow_id, payload.step, f"Movido manualmente al paso {payload.step} por {current_user['username']}")
    updated = get_workflow_run(workflow_id)
    logs = get_workflow_logs(workflow_id)
    can_advance = updated["current_step"] != "done" and next_step(updated["current_step"]) is not None
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
    current_user: Dict[str, Any] = Depends(require_admin),
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




@app.get("/canciones", response_model=List[m.CancionResponse])
async def list_canciones_endpoint(
    current_user: Dict[str, Any] = Depends(get_current_user),
):
    """Lista todas las canciones del cancionero."""
    from src.canciones_manager import listar_canciones
    return listar_canciones()


@app.post("/canciones", response_model=m.CancionResponse, status_code=201)
async def create_cancion_endpoint(
    payload: m.CancionCreate,
    current_user: Dict[str, Any] = Depends(require_admin),
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
    current_user: Dict[str, Any] = Depends(get_current_user),
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
    current_user: Dict[str, Any] = Depends(require_admin),
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
                letra_con_acordes=payload.letra_con_acordes if payload.letra_con_acordes is not None else existing["letra_con_acordes"] or "",
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
    current_user: Dict[str, Any] = Depends(require_admin),
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
