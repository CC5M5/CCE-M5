"""Modelos Pydantic para la API de administración."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: Optional[str] = None


class UserProfile(BaseModel):
    id: int
    username: str
    full_name: Optional[str]
    role: str
    is_active: int = 1


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: Optional[str] = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class WorkflowCreate(BaseModel):
    fecha_domingo: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    force: bool = False


class WorkflowAdvance(BaseModel):
    workflow_id: int
    action: str = Field(..., pattern=r"^(next|retry|rollback)$")
    data: Optional[Dict[str, Any]] = None


class WorkflowGotoStep(BaseModel):
    workflow_id: int
    step: str = Field(..., pattern=r"^(init|fetch_lectures|verify_lectures|propose_songs|verify_songs|generate_assets|publish|done)$")


class WorkflowRun(BaseModel):
    id: int
    fecha_domingo: str
    status: str
    current_step: str
    steps_data: Dict[str, Any]
    created_by: Optional[str]
    created_at: Optional[str]
    updated_at: Optional[str]
    completed_at: Optional[str]
    superseded_by: Optional[int]


class WorkflowLogEntry(BaseModel):
    id: int
    workflow_id: int
    step: str
    level: str
    message: str
    created_at: Optional[str]


class LectureData(BaseModel):
    domingo: Optional[str] = None
    temporada: Optional[str] = None
    ciclo: Optional[str] = None
    color_liturgico: Optional[str] = None
    primera_lectura_cita: Optional[str] = None
    primera_lectura_texto: Optional[str] = None
    salmo_cita: Optional[str] = None
    salmo_antifona: Optional[str] = None
    salmo_texto: Optional[str] = None
    segunda_lectura_cita: Optional[str] = None
    segunda_lectura_texto: Optional[str] = None
    evangelio_cita: Optional[str] = None
    evangelio_texto: Optional[str] = None
    fuente_scraping: Optional[str] = None


class SongProposal(BaseModel):
    momento: str
    cancion_id: int


class WorkflowResponse(BaseModel):
    workflow: WorkflowRun
    logs: List[WorkflowLogEntry]
    can_advance: bool
    next_step_name: Optional[str]
    warning: Optional[str] = None


# ---------------------------------------------------------------------------
# Canciones
# ---------------------------------------------------------------------------


class CancionCreate(BaseModel):
    titulo: str
    letra_con_acordes: str
    momentos: List[str] = []
    tono: Optional[str] = None
    fuente: Optional[str] = "manual"


class CancionUpdate(BaseModel):
    titulo: Optional[str] = None
    letra_con_acordes: Optional[str] = None
    momentos: Optional[List[str]] = None
    tono: Optional[str] = None
    fuente: Optional[str] = None


class CancionResponse(BaseModel):
    id: int
    titulo: str
    titulo_url: str
    slug: str
    letra_con_acordes: Optional[str] = None
    letra_sin_acordes: Optional[str] = None
    html_visual: Optional[str] = None
    tono: Optional[str] = None
    fuente: Optional[str] = None
    momentos: List[str] = []
    fecha_creacion: Optional[str] = None
