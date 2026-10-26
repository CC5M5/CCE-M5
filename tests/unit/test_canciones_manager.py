"""Tests para src/canciones_manager.py."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from src import db_manager


@pytest.fixture
def canciones_manager(tmp_path: Path, monkeypatch):
    """Devuelve canciones_manager apuntando a una DB temporal."""
    monkeypatch.setenv("CCE_PROJECT_DIR", str(tmp_path))
    importlib.reload(db_manager)
    from src import canciones_manager as cm

    importlib.reload(cm)
    # Forzar DB_PATH y PROJECT_DIR temporales (se calculan en importación)
    monkeypatch.setattr(cm, "PROJECT_DIR", tmp_path)
    monkeypatch.setattr(cm, "DB_PATH", tmp_path / "data" / "db.sqlite3")
    # Copiar schema.sql del proyecto para que init_database lo use
    schema_src = Path(__file__).resolve().parents[2] / "data" / "schema.sql"
    schema_dst = tmp_path / "data" / "schema.sql"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_text(schema_src.read_text())
    db_manager.init_database(cm.DB_PATH)
    return cm


def test_slugify(canciones_manager) -> None:
    assert canciones_manager.slugify("Aleluya, Aleluya") == "aleluya-aleluya"
    assert canciones_manager.slugify("  MARÍA  ") == "maria"
    assert canciones_manager.slugify("") == ""


def test_regenerar_derivados_con_acordes(canciones_manager) -> None:
    texto = """
Am
Aleluya, aleluya
""".strip()
    derivados = canciones_manager._regenerar_derivados(texto)
    assert "html_visual" in derivados
    assert "estructura_json" in derivados
    assert derivados["letra_sin_acordes"].strip() == "Aleluya, aleluya"
    assert derivados["tono"] is not None


def test_crear_y_obtener_cancion(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="Canción de prueba",
        letra_con_acordes="\nAm\nLínea de prueba\n",
        momentos=["entrada", "comunion"],
        tono="Am",
    )
    cancion = canciones_manager.crear_cancion(data)
    assert cancion["id"] == 1
    assert cancion["titulo"] == "Canción de prueba"
    assert cancion["slug"] == "cancion-de-prueba"
    assert set(cancion["momentos"]) == {"entrada", "comunion"}
    assert cancion["tono"] == "Am"

    obtenida = canciones_manager.obtener_cancion(cancion["id"])
    assert obtenida["titulo"] == "Canción de prueba"


def test_crear_cancion_sin_titulo(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(titulo="   ", letra_con_acordes="Am\nTexto")
    with pytest.raises(ValueError, match="título"):
        canciones_manager.crear_cancion(data)


def test_actualizar_cancion(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="Original",
        letra_con_acordes="\nAm\nOriginal\n",
    )
    creada = canciones_manager.crear_cancion(data)

    actualizada = canciones_manager.actualizar_cancion(
        creada["id"],
        canciones_manager.CancionCreateUpdate(
            titulo="Actualizada",
            letra_con_acordes="\nC\nActualizada\n",
            momentos=["gloria"],
            tono="C",
        ),
    )
    assert actualizada["titulo"] == "Actualizada"
    assert actualizada["tono"] == "C"
    assert actualizada["momentos"] == ["gloria"]


def test_actualizar_cancion_inexistente(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="X", letra_con_acordes="Am\nX"
    )
    with pytest.raises(ValueError, match="No existe canción"):
        canciones_manager.actualizar_cancion(9999, data)


def test_eliminar_cancion(canciones_manager) -> None:
    data = canciones_manager.CancionCreateUpdate(
        titulo="Para borrar", letra_con_acordes="Am\nBorrar"
    )
    creada = canciones_manager.crear_cancion(data)
    canciones_manager.eliminar_cancion(creada["id"])

    with pytest.raises(ValueError, match="No existe canción"):
        canciones_manager.obtener_cancion(creada["id"])

    with pytest.raises(ValueError, match="No existe canción"):
        canciones_manager.eliminar_cancion(creada["id"])


def test_listar_canciones(canciones_manager) -> None:
    assert canciones_manager.listar_canciones() == []

    canciones_manager.crear_cancion(
        canciones_manager.CancionCreateUpdate(
            titulo="Bbb", letra_con_acordes="Am\nBbb"
        )
    )
    canciones_manager.crear_cancion(
        canciones_manager.CancionCreateUpdate(
            titulo="Aaa", letra_con_acordes="Am\nAaa"
        )
    )

    lista = canciones_manager.listar_canciones()
    assert len(lista) == 2
    assert lista[0]["titulo"] == "Aaa"
    assert lista[1]["titulo"] == "Bbb"
