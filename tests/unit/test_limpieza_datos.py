"""Tests para scripts/limpieza_datos.py (S3 limpieza de datos de prueba, S4 prefijo «l »).

Cada test construye una BD sintética en tmp_path; no toca la BD viva.
El test de invariantes del archivo real (data/schema.sql) sí lo lee, pero en
modo solo lectura.
"""

import importlib
import json
import sqlite3
from pathlib import Path

import pytest


RAIZ_PROYECTO = Path(__file__).resolve().parents[2]
SCHEMA_SQL_REAL = RAIZ_PROYECTO / "data" / "schema.sql"


@pytest.fixture
def limpieza():
    return importlib.import_module("limpieza_datos")


DDL_BASE = """
CREATE TABLE "canciones" (
"id" INTEGER NOT NULL,
"titulo" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "cancion_momentos" (
"cancion_id" INTEGER NOT NULL,
"momento_liturgico" TEXT NOT NULL,
PRIMARY KEY ("cancion_id", "momento_liturgico")
);
CREATE TABLE "slides" (
"id" INTEGER NOT NULL,
"tipo" TEXT,
"subtipo" TEXT,
"titulo" TEXT,
"notas" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "presentacion_slides" (
"id" INTEGER NOT NULL,
"presentacion_id" INTEGER NOT NULL,
"slide_id" INTEGER NOT NULL,
"numero" INTEGER,
PRIMARY KEY ("id")
);
CREATE TABLE "presentaciones" (
"id" INTEGER NOT NULL,
"fecha_domingo" TEXT,
"lectura_id" INTEGER,
"canciones_json" TEXT,
"estado" TEXT,
"lectura_json" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "lecturas" (
"id" INTEGER NOT NULL,
"fecha" TEXT,
"domingo" TEXT,
"celebracion" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "workflow_runs" (
"id" INTEGER NOT NULL,
"steps_data" TEXT,
PRIMARY KEY ("id")
);
"""


def _build_dirty_db(path: Path) -> None:
    """BD sintética con los datos de prueba de S3/S4 presentes."""
    conn = sqlite3.connect(path)
    conn.executescript(DDL_BASE)
    conn.executemany("INSERT INTO canciones VALUES (?, ?)", [
        (1, "Canción A"),
        (2, "Canción B"),
        (3, "Aleluya"),
        (4, "PREPARAD EL CAMINO"),
    ])
    conn.executemany("INSERT INTO cancion_momentos VALUES (?, ?)", [
        (1, "entrada"),
        (2, "salmo"),
        (3, "entrada"),
        (4, "entrada"),
    ])
    conn.executemany("INSERT INTO slides VALUES (?, ?, ?, ?, ?)", [
        (101, "entrada", "cancion_1", "Canción A", "Auto-creada desde canción"),
        (102, "salmo", "cancion_2", "SALMO: Canción B", "Auto-creada desde canción"),
        (103, "entrada", "cancion_3", "Aleluya", None),
        (104, "entrada", "cancion_4", "PREPARAD EL CAMINO", None),
        (105, "portada", "general", "L DOMINGO XXVI DEL TIEMPO ORDINARIO", None),
    ])
    conn.executemany("INSERT INTO presentacion_slides VALUES (?, ?, ?, ?)", [
        (1, 1, 101, 1),
        (2, 1, 102, 2),
        (3, 1, 103, 3),
    ])
    cj = json.dumps(
        {
            "cancion_1": {"id": 1},
            "cancion_2": {"id": 2},
            "cancion_4": {"id": 4},
            "cancion_999": {"id": 999},
        },
        ensure_ascii=False,
    )
    lj = json.dumps(
        {"celebracion": "l XXXII Domingo del Tiempo Ordinario", "ciclo": "C"},
        ensure_ascii=False,
    )
    conn.execute(
        "INSERT INTO presentaciones VALUES (1, '2026-10-25', 1, ?, 'publicado', ?)",
        (cj, lj),
    )
    conn.executemany("INSERT INTO lecturas VALUES (?, ?, ?, ?)", [
        (1, "2026-10-25", "l XXVIII Domingo del Tiempo Ordinario", "l XXVIII Domingo del Tiempo Ordinario"),
        (2, "2026-10-18", "XXVII Domingo del Tiempo Ordinario", "XXVII Domingo del Tiempo Ordinario"),
    ])
    conn.execute("INSERT INTO workflow_runs VALUES (1, '{\"steps\": [\"l XXX Domingo\"]}')")
    conn.commit()
    conn.close()


def _ids(conn: sqlite3.Connection, query: str, params: tuple = ()) -> set:
    return {row[0] for row in conn.execute(query, params)}


def test_elimina_canciones_prueba_y_relacionados(limpieza, tmp_path):
    db = tmp_path / "db.sqlite3"
    _build_dirty_db(db)
    conn = sqlite3.connect(db)
    try:
        res = limpieza.clean_db(conn)
        assert sorted(res["canciones"]) == [1, 2]
        assert res["cancion_momentos"] == 2
        assert sorted(res["slides"]) == [101, 102]
        assert res["presentacion_slides"] == 2

        assert _ids(conn, "SELECT id FROM canciones") == {3, 4}
        assert _ids(conn, "SELECT cancion_id FROM cancion_momentos") == {3, 4}
        assert _ids(conn, "SELECT id FROM slides") == {103, 104, 105}
        assert _ids(conn, "SELECT slide_id FROM presentacion_slides") == {103}

        cj = json.loads(conn.execute("SELECT canciones_json FROM presentaciones WHERE id=1").fetchone()[0])
        assert set(cj) == {"cancion_4"}
        assert cj["cancion_4"] == {"id": 4}
    finally:
        conn.close()


def test_preserva_canciones_sospechosas(limpieza, tmp_path):
    """«Aleluya» y demás canciones no se tocan; se reportan como anomalía."""
    db = tmp_path / "db.sqlite3"
    _build_dirty_db(db)
    conn = sqlite3.connect(db)
    try:
        res = limpieza.clean_db(conn)
        assert res["anomalias"]["aleluya"]["canciones"] == [3]
        assert res["anomalias"]["aleluya"]["slides"] == 1
        assert conn.execute("SELECT titulo FROM canciones WHERE id=3").fetchone()[0] == "Aleluya"
        assert conn.execute("SELECT titulo FROM slides WHERE id=103").fetchone()[0] == "Aleluya"
    finally:
        conn.close()


def test_normaliza_prefijo_l(limpieza, tmp_path):
    db = tmp_path / "db.sqlite3"
    _build_dirty_db(db)
    conn = sqlite3.connect(db)
    try:
        res = limpieza.clean_db(conn)
        assert res["lecturas"] == [1]

        domingo, celebracion = conn.execute(
            "SELECT domingo, celebracion FROM lecturas WHERE id=1"
        ).fetchone()
        assert domingo == "XXVIII Domingo del Tiempo Ordinario"
        assert celebracion == "XXVIII Domingo del Tiempo Ordinario"

        domingo2, celebracion2 = conn.execute(
            "SELECT domingo, celebracion FROM lecturas WHERE id=2"
        ).fetchone()
        assert domingo2 == "XXVII Domingo del Tiempo Ordinario"
        assert celebracion2 == "XXVII Domingo del Tiempo Ordinario"

        lj = json.loads(conn.execute("SELECT lectura_json FROM presentaciones WHERE id=1").fetchone()[0])
        assert lj["celebracion"] == "XXXII Domingo del Tiempo Ordinario"
        assert lj["ciclo"] == "C"

        # Anomalías NO normalizadas (mayúscula / histórico): se reportan, no se mutan.
        assert res["anomalias"]["slides_titulo_L_mayuscula"] == [105]
        assert res["anomalias"]["workflow_l"] == 1
        titulo_105 = conn.execute("SELECT titulo FROM slides WHERE id=105").fetchone()[0]
        assert titulo_105 == "L DOMINGO XXVI DEL TIEMPO ORDINARIO"
    finally:
        conn.close()


def test_purga_referencias_hueras(limpieza):
    """Refs a canciones inexistentes (p. ej. 999) se eliminan; las válidas se conservan."""
    ids_vivos = {4}
    nuevo, refs_prueba, refs_hueras = limpieza._purgar_canciones_json(
        json.dumps({"cancion_2": {"id": 2}, "cancion_4": {"id": 4}, "cancion_999": 999}, ensure_ascii=False),
        ids_vivos,
        {2},
    )
    assert nuevo == json.dumps({"cancion_4": {"id": 4}}, ensure_ascii=False)
    assert refs_prueba == 1
    assert refs_hueras == 1


def test_purga_canciones_json_edge_cases(limpieza):
    assert limpieza._purgar_canciones_json(None, {1}, {1}) == (None, 0, 0)
    # JSON inválido: se devuelve tal cual.
    assert limpieza._purgar_canciones_json("no-json", {1}, {1}) == ("no-json", 0, 0)
    # Todos los refs eliminados -> None (convención sin canciones).
    assert limpieza._purgar_canciones_json('{"cancion_1": 1}', {1}, {1}) == (None, 1, 0)


def test_idempotente(limpieza, tmp_path):
    db = tmp_path / "db.sqlite3"
    _build_dirty_db(db)
    conn = sqlite3.connect(db)
    try:
        res1 = limpieza.clean_db(conn)
        assert res1["canciones"]  # la primera pasada sí eliminó

        def snapshot():
            out = {}
            for tabla in (
                "canciones", "cancion_momentos", "slides",
                "presentacion_slides", "presentaciones", "lecturas",
            ):
                out[tabla] = conn.execute(f"SELECT * FROM {tabla} ORDER BY 1").fetchall()
            return out

        antes = snapshot()
        res2 = limpieza.clean_db(conn)
        assert res2["canciones"] == []
        assert res2["cancion_momentos"] == 0
        assert res2["slides"] == []
        assert res2["presentacion_slides"] == 0
        assert res2["presentaciones"] == []
        assert res2["lecturas"] == []
        assert snapshot() == antes
    finally:
        conn.close()


def test_backup_consistente(limpieza, tmp_path):
    db = tmp_path / "db.sqlite3"
    _build_dirty_db(db)
    backup = db.with_name("db.sqlite3.bak-limpieza-20260927-120000")
    limpieza.backup_database(db, backup)
    conn = sqlite3.connect(backup)
    try:
        assert _ids(conn, "SELECT id FROM canciones") == {1, 2, 3, 4}
        assert _ids(conn, "SELECT id FROM slides") == {101, 102, 103, 104, 105}
    finally:
        conn.close()
    # La BD original no se alteró.
    conn2 = sqlite3.connect(db)
    try:
        assert _ids(conn2, "SELECT id FROM canciones") == {1, 2, 3, 4}
    finally:
        conn2.close()


_SCHEMA_DIRTY = """BEGIN TRANSACTION;

CREATE TABLE "canciones" (
"id" INTEGER NOT NULL,
"titulo" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "cancion_momentos" (
"cancion_id" INTEGER NOT NULL,
"momento_liturgico" TEXT NOT NULL,
PRIMARY KEY ("cancion_id", "momento_liturgico")
);
CREATE TABLE "slides" (
"id" INTEGER NOT NULL,
"tipo" TEXT,
"subtipo" TEXT,
"titulo" TEXT,
"notas" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "presentacion_slides" (
"id" INTEGER NOT NULL,
"presentacion_id" INTEGER NOT NULL,
"slide_id" INTEGER NOT NULL,
"numero" INTEGER,
PRIMARY KEY ("id")
);
CREATE TABLE "presentaciones" (
"id" INTEGER NOT NULL,
"fecha_domingo" TEXT,
"lectura_id" INTEGER,
"canciones_json" TEXT,
"estado" TEXT,
"lectura_json" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "lecturas" (
"id" INTEGER NOT NULL,
"fecha" TEXT,
"domingo" TEXT,
"celebracion" TEXT,
PRIMARY KEY ("id")
);
INSERT INTO "canciones" VALUES(1,'Canción A');
INSERT INTO "canciones" VALUES(2,'Canción B');
INSERT INTO "canciones" VALUES(3,'Aleluya');
INSERT INTO "canciones" VALUES(4,'PREPARAD EL CAMINO');
INSERT INTO "cancion_momentos" VALUES(1,'entrada');
INSERT INTO "cancion_momentos" VALUES(2,'salmo');
INSERT INTO "cancion_momentos" VALUES(3,'entrada');
INSERT INTO "cancion_momentos" VALUES(4,'entrada');
INSERT INTO "slides" VALUES(101,'entrada','cancion_1','Canción A','Auto-creada desde canción');
INSERT INTO "slides" VALUES(102,'salmo','cancion_2','SALMO: Canción B','Auto-creada desde canción');
INSERT INTO "slides" VALUES(103,'entrada','cancion_3','Aleluya',NULL);
INSERT INTO "slides" VALUES(104,'entrada','cancion_4','PREPARAD EL CAMINO',NULL);
INSERT INTO "slides" VALUES(105,'portada','general','L DOMINGO XXVI DEL TIEMPO ORDINARIO',NULL);
INSERT INTO "presentacion_slides" VALUES(1,1,101,1);
INSERT INTO "presentacion_slides" VALUES(2,1,102,2);
INSERT INTO "presentacion_slides" VALUES(3,1,103,3);
INSERT INTO "presentaciones" VALUES(1,'2026-10-25',1,'{"cancion_1": {"id": 1}, "cancion_2": {"id": 2}, "cancion_4": {"id": 4}, "cancion_999": {"id": 999}}','publicado','{"celebracion": "l XXXII Domingo del Tiempo Ordinario", "ciclo": "C"}');
INSERT INTO "lecturas" VALUES(1,'2026-10-25','l XXVIII Domingo del Tiempo Ordinario','l XXVIII Domingo del Tiempo Ordinario');
INSERT INTO "lecturas" VALUES(2,'2026-10-18','XXVII Domingo del Tiempo Ordinario','XXVII Domingo del Tiempo Ordinario');
COMMIT;
"""


_SCHEMA_SEMI_LITERAL = """BEGIN TRANSACTION;

CREATE TABLE "canciones" (
"id" INTEGER NOT NULL,
"titulo" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "cancion_momentos" (
"cancion_id" INTEGER NOT NULL,
"momento_liturgico" TEXT NOT NULL,
PRIMARY KEY ("cancion_id", "momento_liturgico")
);
CREATE TABLE "slides" (
"id" INTEGER NOT NULL,
"tipo" TEXT,
"subtipo" TEXT,
"titulo" TEXT,
"notas" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "presentacion_slides" (
"id" INTEGER NOT NULL,
"presentacion_id" INTEGER NOT NULL,
"slide_id" INTEGER NOT NULL,
"numero" INTEGER,
PRIMARY KEY ("id")
);
CREATE TABLE "presentaciones" (
"id" INTEGER NOT NULL,
"fecha_domingo" TEXT,
"lectura_id" INTEGER,
"canciones_json" TEXT,
"estado" TEXT,
"lectura_json" TEXT,
PRIMARY KEY ("id")
);
CREATE TABLE "lecturas" (
"id" INTEGER NOT NULL,
"fecha" TEXT,
"domingo" TEXT,
"celebracion" TEXT,
PRIMARY KEY ("id")
);
INSERT INTO "canciones" VALUES(1,'Café &amp; Te; sigue la letra');
INSERT INTO "canciones" VALUES(2,'Aleluya');
COMMIT;
"""


def test_split_statements_punto_y_coma_dentro_literal(limpieza, tmp_path):
    """Pin de regresión de la corrección de `_split_statements` (L3).

    Un ';' dentro de un literal de cadena (entidades HTML en letras de
    canciones) no debe completar la sentencia.
    """
    schema = tmp_path / "schema.sql"
    schema.write_text(_SCHEMA_SEMI_LITERAL, encoding="utf-8")

    # Algoritmo anterior (pos no avanzaba en sentencia incompleta): bucle
    # infinito; la simulación acotada demuestra que se quedaba dando vueltas
    # sobre el mismo ';'.
    pos = 0
    start = 0
    guard = 0
    spin = False
    while pos < len(_SCHEMA_SEMI_LITERAL) and guard < 10:
        i = _SCHEMA_SEMI_LITERAL.find(";", pos)
        if i == -1:
            break
        candidata = _SCHEMA_SEMI_LITERAL[start : i + 1]
        if candidata.strip() and sqlite3.complete_statement(candidata):
            start = pos = i + 1
            guard = 0
        else:
            guard += 1
            if guard > 2:  # el mismo ';' se re-prueba sin avance
                spin = True
                break
    assert spin, "el algoritmo previo debía buclar sobre el ';' del literal"

    # Algoritmo corregido: cada INSERT es una sentencia completa, sin cortes
    # en el ';' interior.
    spans, cola = limpieza._split_statements(_SCHEMA_SEMI_LITERAL)
    inserts = [
        (a, b)
        for a, b in spans
        if _SCHEMA_SEMI_LITERAL[a:b].lstrip().upper().startswith("INSERT")
    ]
    assert len(inserts) == 2
    a, b = inserts[0]
    assert _SCHEMA_SEMI_LITERAL[a:b].lstrip() == (
        'INSERT INTO "canciones" VALUES(1,'
        "'Café &amp; Te; sigue la letra');"
    )

    # End-to-end: el dump «limpiado» carga íntegro y conserva el literal.
    res = limpieza.clean_schema_sql(schema)
    assert res["escrito"] is False  # nada que limpiar en este dump
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(schema.read_text(encoding="utf-8"))
        titulo = conn.execute(
            "SELECT titulo FROM canciones WHERE id=1"
        ).fetchone()[0]
        assert titulo == "Café &amp; Te; sigue la letra"
    finally:
        conn.close()


def test_clean_schema_sql(limpieza, tmp_path):
    schema = tmp_path / "schema.sql"
    schema.write_text(_SCHEMA_DIRTY, encoding="utf-8")

    res = limpieza.clean_schema_sql(schema)
    assert sorted(res["canciones"]) == [1, 2]
    assert sorted(res["slides"]) == [101, 102]
    assert res["cancion_momentos"] == 2
    assert res["presentacion_slides"] == 2

    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(schema.read_text(encoding="utf-8"))
        assert _ids(conn, "SELECT id FROM canciones") == {3, 4}
        assert _ids(conn, "SELECT cancion_id FROM cancion_momentos") == {3, 4}
        assert _ids(conn, "SELECT id FROM slides") == {103, 104, 105}
        assert _ids(conn, "SELECT slide_id FROM presentacion_slides") == {103}

        cj = json.loads(conn.execute("SELECT canciones_json FROM presentaciones WHERE id=1").fetchone()[0])
        assert set(cj) == {"cancion_4"}

        lj = json.loads(conn.execute("SELECT lectura_json FROM presentaciones WHERE id=1").fetchone()[0])
        assert lj["celebracion"] == "XXXII Domingo del Tiempo Ordinario"

        domingo, celebracion = conn.execute("SELECT domingo, celebracion FROM lecturas WHERE id=1").fetchone()
        assert domingo == "XXVIII Domingo del Tiempo Ordinario"
        assert celebracion == "XXVIII Domingo del Tiempo Ordinario"
    finally:
        conn.close()

    # Idempotencia: segunda pasada no cambia nada.
    texto_despues = schema.read_text(encoding="utf-8")
    res2 = limpieza.clean_schema_sql(schema)
    assert res2["canciones"] == []
    assert res2["slides"] == []
    assert schema.read_text(encoding="utf-8") == texto_despues


def test_schema_sql_real_sin_datos_prueba():
    """data/schema.sql (fichero real, solo lectura) no debe contener datos de prueba."""
    assert SCHEMA_SQL_REAL.exists()
    conn = sqlite3.connect(":memory:")
    try:
        conn.executescript(SCHEMA_SQL_REAL.read_text(encoding="utf-8"))
        ab = (
            "SELECT COUNT(*) FROM canciones WHERE titulo IN ('Canción A', 'Canción B')"
        )
        assert conn.execute(ab).fetchone()[0] == 0
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM slides WHERE titulo IN ('Canción A', 'Canción B')"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM lecturas WHERE celebracion LIKE 'l %' OR domingo LIKE 'l %'"
            ).fetchone()[0]
            == 0
        )
        assert (
            conn.execute(
                "SELECT COUNT(*) FROM presentaciones WHERE lectura_json LIKE '%\"l %'"
            ).fetchone()[0]
            == 0
        )
    finally:
        conn.close()


def test_export_canciones_web(limpieza, tmp_path):
    db = tmp_path / "db.sqlite3"
    conn = sqlite3.connect(db)
    conn.execute('CREATE TABLE "canciones" ("id" INTEGER NOT NULL, "titulo" TEXT, PRIMARY KEY ("id"))')
    conn.executemany("INSERT INTO canciones VALUES (?, ?)", [(1, "Aleluya"), (2, "PREPARAD EL CAMINO")])
    conn.commit()
    conn.close()

    out = tmp_path / "web" / "data" / "canciones.json"
    limpieza.export_canciones_web(db, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert [c["titulo"] for c in data] == ["Aleluya", "PREPARAD EL CAMINO"]


def test_koinonia_normaliza_prefijo_l():
    from src.scrapers.koinonia_scraper import normalizar_celebracion

    assert (
        normalizar_celebracion("l XXXII Domingo del Tiempo Ordinario")
        == "XXXII Domingo del Tiempo Ordinario"
    )
    assert (
        normalizar_celebracion("XXXII Domingo del Tiempo Ordinario")
        == "XXXII Domingo del Tiempo Ordinario"
    )
    assert normalizar_celebracion("") == ""
    assert normalizar_celebracion(None) is None


def test_koinonia_parse_celebracion_sin_prefijo():
    from src.scrapers.koinonia_scraper import KoinoniaParser

    html = """
    <h1>l XXXII Domingo del Tiempo Ordinario</h1>
    <h3>Primera Lectura</h3>
    <p><b>Génesis 1,1</b></p>
    <p>En el principio creó Dios los cielos y la tierra.</p>
    <h3>Salmo</h3>
    <p><b>Salmo 119</b></p>
    <p>Antífona: Tu palabra es lámpara para mis pasos.</p>
    <p>Beato el que camina sin culpas.</p>
    <h3>Evangelio</h3>
    <p><b>Juan 1,1</b></p>
    <p>En el principio era la Palabra.</p>
    """
    resultado = KoinoniaParser().parse(html, "20260927")
    assert resultado["celebracion"] == "XXXII Domingo del Tiempo Ordinario"


def test_ciudadredonda_normaliza_prefijo_l():
    from src.scrapers.ciudadredonda_scraper import normalizar_celebracion

    assert (
        normalizar_celebracion("l XXXII Domingo del Tiempo Ordinario")
        == "XXXII Domingo del Tiempo Ordinario"
    )
    assert (
        normalizar_celebracion("XXXII Domingo del Tiempo Ordinario")
        == "XXXII Domingo del Tiempo Ordinario"
    )
    assert normalizar_celebracion(None) is None


def test_ciudadredonda_parse_celebracion_sin_prefijo():
    from src.scrapers.ciudadredonda_scraper import CiudadRedondaParser

    html = """
    <h1 class="mec-divi-simple-header">Evangelio y Lecturas de l XXXII Domingo del Tiempo Ordinario</h1>
    <h2>Primera Lectura</h2>
    <p><b>Génesis 1,1</b></p>
    <p>En el principio creó Dios los cielos y la tierra.</p>
    <h2>Salmo</h2>
    <p><b>Salmo 119</b></p>
    <p>Antífona: Tu palabra es lámpara para mis pasos.</p>
    <p>Beato el que camina sin culpas.</p>
    <h2>Evangelio</h2>
    <p><b>Juan 1,1</b></p>
    <p>En el principio era la Palabra.</p>
    """
    resultado = CiudadRedondaParser().parse_lecturas(html, "2026-09-27")
    assert resultado["celebracion"] == "XXXII Domingo del Tiempo Ordinario"
