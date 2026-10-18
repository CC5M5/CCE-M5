"""Modelos Pydantic para la API de administración."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str | None = None


class UserProfile(BaseModel):
    id: int
    username: str
    full_name: str | None
    role: str
    is_active: int = 1


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str | None = None
    role: str = "viewer"


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: str | None = None
    is_active: bool | None = None


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class WorkflowCreate(BaseModel):
    fecha_domingo: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    force: bool = False


class WorkflowAdvance(BaseModel):
    workflow_id: int
    action: str = Field(..., pattern=r"^(next|retry|rollback)$")
    data: dict[str, Any] | None = None


class WorkflowGotoStep(BaseModel):
    workflow_id: int
    step: str = Field(
        ...,
        pattern=r"^(init|fetch_lectures|verify_lectures|propose_songs|verify_songs|generate_assets|publish|done)$",
    )


class WorkflowRun(BaseModel):
    id: int
    fecha_domingo: str
    status: str
    current_step: str
    steps_data: dict[str, Any]
    created_by: str | None
    created_at: str | None
    updated_at: str | None
    completed_at: str | None
    superseded_by: int | None


class WorkflowLogEntry(BaseModel):
    id: int
    workflow_id: int
    step: str
    level: str
    message: str
    created_at: str | None


class LectureData(BaseModel):
    domingo: str | None = None
    temporada: str | None = None
    ciclo: str | None = None
    color_liturgico: str | None = None
    primera_lectura_cita: str | None = None
    primera_lectura_texto: str | None = None
    salmo_cita: str | None = None
    salmo_antifona: str | None = None
    salmo_texto: str | None = None
    segunda_lectura_cita: str | None = None
    segunda_lectura_texto: str | None = None
    evangelio_cita: str | None = None
    evangelio_texto: str | None = None
    fuente_scraping: str | None = None


class SongProposal(BaseModel):
    momento: str
    cancion_id: int


class WorkflowResponse(BaseModel):
    workflow: WorkflowRun
    logs: list[WorkflowLogEntry]
    can_advance: bool
    next_step_name: str | None
    warning: str | None = None


# ---------------------------------------------------------------------------
# Comentarios / sugerencias web
# ---------------------------------------------------------------------------


class ComentarioRequest(BaseModel):
    nombre: str = Field(..., max_length=100)
    email: EmailStr = Field(..., max_length=254)
    tipo: str = Field(default="otro", pattern=r"^(sugerencia|correccion|otro)$")
    presentacion: str = Field(default="", max_length=30)
    mensaje: str = Field(..., max_length=2000)


# ---------------------------------------------------------------------------
# Canciones
# ---------------------------------------------------------------------------


class CancionCreate(BaseModel):
    titulo: str
    letra_con_acordes: str
    momentos: list[str] = []
    tono: str | None = None
    fuente: str | None = "manual"


class CancionUpdate(BaseModel):
    titulo: str | None = None
    letra_con_acordes: str | None = None
    momentos: list[str] | None = None
    tono: str | None = None
    fuente: str | None = None


class CancionResponse(BaseModel):
    id: int
    titulo: str
    titulo_url: str
    slug: str
    letra_con_acordes: str | None = None
    letra_sin_acordes: str | None = None
    html_visual: str | None = None
    tono: str | None = None
    fuente: str | None = None
    momentos: list[str] = []
    fecha_creacion: str | None = None
