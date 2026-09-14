#!/usr/bin/env python3
"""Motor de matching temático entre lecturas y canciones.

Relaciona las lecturas dominicales con canciones del cancionero por temas comunes.

Arquitectura separada por responsabilidades:
- TextPreprocessor: limpieza y tokenización segura de texto.
- ThemeExtractor: extracción de vectores temáticos ponderados.
- ScoreNormalizer: normalización de scores al rango [0, 1].
- MatchRepository: persistencia de resultados en SQLite.
- MatchingService: orquestación del matching, precálculo y cacheo.
- MatchingEngine: fachada pública de alto nivel (mantiene compatibilidad básica).
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from dataclasses import dataclass, field
import os
from pathlib import Path
from typing import Any

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
PROJECT_DIR = Path(os.environ.get("CCE_PROJECT_DIR", DEFAULT_PROJECT_DIR))
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
CONFIG_PATH = PROJECT_DIR / "data" / "matching_config.json"


# ---------------------------------------------------------------------------
# Excepciones específicas
# ---------------------------------------------------------------------------


class MatchingError(Exception):
    """Excepción base para errores del motor de matching."""


class ConfigError(MatchingError):
    """Error al cargar o validar la configuración."""


class ValidationError(MatchingError):
    """Error de validación de inputs."""


class DatabaseError(MatchingError):
    """Error de acceso a la base de datos."""


# ---------------------------------------------------------------------------
# Datos por defecto
# ---------------------------------------------------------------------------


DEFAULT_CONFIG: dict[str, Any] = {
    "db_path": str(DB_PATH),
    "score_minimo": 0.15,
    "limite_resultados": 5,
    "momento_liturgico_boost": 0.12,
    "cache_activa": True,
    "temas": {
        "perdon": {
            "palabras": ["perdon", "misericordia", "pecado", "culpa", "reconciliacion", "perdona"],
            "peso": 1.5,
        },
        "paz": {
            "palabras": ["paz", "cordero", "reconciliacion", "unidad", "hermanos", "concordia"],
            "peso": 1.2,
        },
        "esperanza": {
            "palabras": ["esperanza", "manana", "futuro", "nuevo", "renovar", "amanecer"],
            "peso": 1.0,
        },
        "amor": {
            "palabras": ["amor", "caridad", "entrega", "querer", "afecto"],
            "peso": 1.3,
        },
        "camino": {
            "palabras": ["camino", "sendero", "verdad", "vida", "seguir", "andar", "senda"],
            "peso": 1.1,
        },
        "luz": {
            "palabras": ["luz", "brillar", "oscuridad", "iluminar", "claridad", "resplandor"],
            "peso": 1.0,
        },
        "agua": {
            "palabras": ["agua", "beber", "sed", "manantial", "rio", "fuente", "bautismo"],
            "peso": 1.0,
        },
        "pan": {
            "palabras": ["pan", "comer", "hambre", "alimento", "nutrir", "mesa", "cuerpo"],
            "peso": 1.2,
        },
        "maria": {
            "palabras": ["maria", "virgen", "amparo", "proteccion", "madre", "magnificat"],
            "peso": 1.4,
        },
        "espiritu": {
            "palabras": ["espiritu", "fuego", "viento", "pentecostes", "consolador"],
            "peso": 1.3,
        },
        "alabanza": {
            "palabras": ["alabar", "gloria", "honor", "santo", "adorar", "cantar", "loar"],
            "peso": 1.1,
        },
        "servicio": {
            "palabras": ["servir", "humilde", "pobre", "ayudar", "dar", "servicio", "ministrar"],
            "peso": 1.0,
        },
        "fe": {
            "palabras": ["fe", "creer", "confiar", "esperar", "firmeza", "conviccion"],
            "peso": 1.2,
        },
        "salvacion": {
            "palabras": ["salvar", "salvacion", "libertad", "redimir", "rescate", "liberar"],
            "peso": 1.3,
        },
    },
    "afinidad_momento_tema": {
        "entrada": ["alabanza", "esperanza", "camino"],
        "perdon": ["perdon"],
        "gloria": ["alabanza"],
        "salmo": ["agua", "luz", "camino", "paz"],
        "aleluya": ["alabanza", "espiritu"],
        "ofertorio": ["pan", "servicio"],
        "santo": ["alabanza", "amor"],
        "padre_nuestro": ["fe", "perdon"],
        "paz": ["paz"],
        "comunion": ["pan", "amor", "espiritu", "maria"],
        "maria": ["maria"],
        "despedida": ["camino", "esperanza", "paz"],
        "general": [],
    },
}


# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatchingConfig:
    """Configuración validada del motor de matching."""

    db_path: Path
    score_minimo: float
    limite_resultados: int
    momento_liturgico_boost: float
    cache_activa: bool
    temas: dict[str, dict[str, Any]]
    afinidad_momento_tema: dict[str, list[str]]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MatchingConfig":
        db_path = Path(data.get("db_path", str(DB_PATH)))
        score_minimo = float(data.get("score_minimo", DEFAULT_CONFIG["score_minimo"]))
        limite_resultados = int(data.get("limite_resultados", DEFAULT_CONFIG["limite_resultados"]))
        momento_liturgico_boost = float(
            data.get("momento_liturgico_boost", DEFAULT_CONFIG["momento_liturgico_boost"])
        )
        cache_activa = bool(data.get("cache_activa", DEFAULT_CONFIG["cache_activa"]))
        temas = data.get("temas", DEFAULT_CONFIG["temas"])
        afinidad = data.get("afinidad_momento_tema", DEFAULT_CONFIG["afinidad_momento_tema"])

        if score_minimo < 0 or score_minimo > 1:
            raise ConfigError("score_minimo debe estar entre 0 y 1")
        if limite_resultados < 1:
            raise ConfigError("limite_resultados debe ser mayor o igual a 1")
        if momento_liturgico_boost < 0 or momento_liturgico_boost > 1:
            raise ConfigError("momento_liturgico_boost debe estar entre 0 y 1")

        return cls(
            db_path=db_path,
            score_minimo=score_minimo,
            limite_resultados=limite_resultados,
            momento_liturgico_boost=momento_liturgico_boost,
            cache_activa=cache_activa,
            temas=temas,
            afinidad_momento_tema=afinidad,
        )

    @classmethod
    def load(cls, config_path: Path | None = None) -> "MatchingConfig":
        path = config_path or CONFIG_PATH
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=2, ensure_ascii=False)
            logger.info("Configuracion por defecto guardada en %s", path)
            return cls.from_dict(DEFAULT_CONFIG)

        try:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ConfigError(f"Archivo de configuracion JSON invalido: {exc}") from exc
        except OSError as exc:
            raise ConfigError(f"No se pudo leer la configuracion: {exc}") from exc

        return cls.from_dict(data)


# ---------------------------------------------------------------------------
# Preprocesamiento
# ---------------------------------------------------------------------------


class TextPreprocessor:
    """Limpia y tokeniza textos usando palabras completas."""

    _PALABRA = re.compile(r"[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]+")

    def __init__(self, quitar_tildes: bool = True) -> None:
        self.quitar_tildes = quitar_tildes
        self._tildes = str.maketrans(
            "áéíóúüÁÉÍÓÚÜ", "aeiouuAEIOUU"
        )

    def tokenize(self, texto: str | None) -> list[str]:
        if not texto:
            return []
        texto = str(texto).lower()
        tokens = self._PALABRA.findall(texto)
        if self.quitar_tildes:
            tokens = [t.translate(self._tildes) for t in tokens]
        return tokens

    def contar_frecuencias(self, texto: str | None) -> dict[str, int]:
        from collections import Counter

        return dict(Counter(self.tokenize(texto)))


# ---------------------------------------------------------------------------
# Extracción de temas
# ---------------------------------------------------------------------------


@dataclass
class ThemeVector:
    """Vector temático normalizado de un texto."""

    temas: dict[str, float] = field(default_factory=dict)
    palabras_halladas: dict[str, list[str]] = field(default_factory=dict)


class ThemeExtractor:
    """Extrae vectores temáticos ponderados a partir de textos."""

    def __init__(self, config: MatchingConfig, preprocessor: TextPreprocessor | None = None) -> None:
        self.config = config
        self.preprocessor = preprocessor or TextPreprocessor()
        self._tema_palabras: dict[str, list[str]] = {}
        self._tema_peso: dict[str, float] = {}
        self._index: dict[str, set[str]] = {}
        for tema, cfg in config.temas.items():
            palabras = [p.lower() for p in cfg.get("palabras", [])]
            self._tema_palabras[tema] = palabras
            self._tema_peso[tema] = float(cfg.get("peso", 1.0))
            for palabra in palabras:
                self._index.setdefault(palabra, set()).add(tema)

    def extract(self, texto: str | None) -> ThemeVector:
        if not texto:
            return ThemeVector()

        frecuencias = self.preprocessor.contar_frecuencias(texto)
        temas: dict[str, float] = {}
        palabras_halladas: dict[str, list[str]] = {}

        for palabra, count in frecuencias.items():
            for tema in self._index.get(palabra, set()):
                temas[tema] = temas.get(tema, 0.0) + count * self._tema_peso[tema]
                palabras_halladas.setdefault(tema, []).append(palabra)

        return ThemeVector(temas=temas, palabras_halladas=palabras_halladas)


# ---------------------------------------------------------------------------
# Normalización
# ---------------------------------------------------------------------------


class ScoreNormalizer:
    """Normaliza scores de matching al rango [0, 1]."""

    def __init__(self, extractor: ThemeExtractor) -> None:
        self.extractor = extractor

    def calcular_score(
        self,
        vector_lectura: ThemeVector,
        vector_cancion: ThemeVector,
        momento_lectura: str | None = None,
        momento_cancion: str | None = None,
        boost: float = 0.12,
        afinidad: dict[str, list[str]] | None = None,
    ) -> float:
        if not vector_lectura.temas or not vector_cancion.temas:
            return 0.0

        temas_comunes = set(vector_lectura.temas.keys()) & set(vector_cancion.temas.keys())
        if not temas_comunes:
            return 0.0

        # Producto de scores como medida de solapamiento temático.
        numerador = sum(
            vector_lectura.temas[tema] * vector_cancion.temas[tema] for tema in temas_comunes
        )

        # Normalización por la energía total de ambos vectores (coseno-like).
        norm_lectura = sum(v * v for v in vector_lectura.temas.values()) ** 0.5
        norm_cancion = sum(v * v for v in vector_cancion.temas.values()) ** 0.5
        denominador = norm_lectura * norm_cancion

        score = numerador / denominador if denominador > 0 else 0.0

        # Boost por afinidad momento litúrgico - tema.
        score = self._aplicar_boost_momento(
            score, temas_comunes, momento_lectura, momento_cancion, boost, afinidad
        )

        return float(min(max(score, 0.0), 1.0))

    def _aplicar_boost_momento(
        self,
        score: float,
        temas_comunes: set[str],
        momento_lectura: str | None,
        momento_cancion: str | None,
        boost: float,
        afinidad: dict[str, list[str]] | None,
    ) -> float:
        afinidad = afinidad or {}

        momentos = []
        if momento_lectura:
            momentos.append(momento_lectura)
        if momento_cancion:
            momentos.append(momento_cancion)

        if not momentos:
            return score

        max_boost = 0.0
        for momento in momentos:
            temas_afines = set(afinidad.get(momento, []))
            if temas_afines & temas_comunes:
                max_boost = max(max_boost, boost)

        return score * (1.0 + max_boost)


# ---------------------------------------------------------------------------
# Validación
# ---------------------------------------------------------------------------


class InputValidator:
    """Valida los inputs del motor de matching."""

    @staticmethod
    def validar_id(valor: Any, nombre: str) -> int:
        try:
            valor_int = int(valor)
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"{nombre} debe ser un entero valido") from exc
        if valor_int <= 0:
            raise ValidationError(f"{nombre} debe ser mayor que cero")
        return valor_int

    @staticmethod
    def validar_score(valor: Any) -> float:
        try:
            score = float(valor)
        except (TypeError, ValueError) as exc:
            raise ValidationError("score debe ser un numero valido entre 0 y 1") from exc
        if score < 0.0 or score > 1.0:
            raise ValidationError("score debe estar entre 0 y 1")
        return score

    @staticmethod
    def validar_limite(valor: Any) -> int:
        try:
            limite = int(valor)
        except (TypeError, ValueError) as exc:
            raise ValidationError("limite debe ser un entero valido") from exc
        if limite < 1:
            raise ValidationError("limite debe ser mayor o igual a 1")
        return limite


# ---------------------------------------------------------------------------
# Repositorio
# ---------------------------------------------------------------------------


class MatchRepository:
    """Persistencia de matches en SQLite usando sqlite3.Row."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def ensure_table(self) -> None:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lectura_id INTEGER NOT NULL,
                        cancion_id INTEGER NOT NULL,
                        score REAL NOT NULL,
                        momento_liturgico TEXT,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (lectura_id) REFERENCES lecturas(id),
                        FOREIGN KEY (cancion_id) REFERENCES canciones(id)
                    )
                    """
                )
        except sqlite3.Error as exc:
            raise DatabaseError(f"Error al crear tabla matches: {exc}") from exc

    def guardar(
        self,
        lectura_id: int,
        cancion_id: int,
        score: float,
        momento_liturgico: str | None = None,
    ) -> None:
        self.ensure_table()
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO matches (lectura_id, cancion_id, score, momento_liturgico)
                    VALUES (?, ?, ?, ?)
                    """,
                    (lectura_id, cancion_id, score, momento_liturgico or "general"),
                )
                conn.commit()
                logger.info("Match guardado: lectura %s -> cancion %s", lectura_id, cancion_id)
        except sqlite3.Error as exc:
            raise DatabaseError(f"Error al guardar match: {exc}") from exc

    def obtener_por_lectura(self, lectura_id: int) -> list[sqlite3.Row]:
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT * FROM matches WHERE lectura_id = ? ORDER BY score DESC",
                    (lectura_id,),
                )
                return cursor.fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Error al obtener matches: {exc}") from exc


# ---------------------------------------------------------------------------
# Servicio de matching
# ---------------------------------------------------------------------------


class MatchingService:
    """Orquesta la extracción, scoring, cacheo y ranking de matches."""

    def __init__(
        self,
        config: MatchingConfig,
        extractor: ThemeExtractor | None = None,
        normalizer: ScoreNormalizer | None = None,
        repository: MatchRepository | None = None,
        validator: InputValidator | None = None,
        preprocessor: TextPreprocessor | None = None,
    ) -> None:
        self.config = config
        self.extractor = extractor or ThemeExtractor(config, preprocessor)
        self.normalizer = normalizer or ScoreNormalizer(self.extractor)
        self.repository = repository or MatchRepository(config.db_path)
        self.validator = validator or InputValidator()
        self._lectura_cache: dict[int, tuple[ThemeVector, str | None]] = {}
        self._cancion_cache: dict[int, tuple[ThemeVector, str | None, str]] = {}

    def analizar_lectura(self, lectura_id: int) -> tuple[ThemeVector, str | None]:
        if self.config.cache_activa and lectura_id in self._lectura_cache:
            return self._lectura_cache[lectura_id]

        lectura_id = self.validator.validar_id(lectura_id, "lectura_id")

        try:
            with sqlite3.connect(str(self.config.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    """
                    SELECT primera_lectura_texto, salmo_texto,
                           segunda_lectura_texto, evangelio_texto,
                           COALESCE(celebracion, domingo) AS celebracion
                    FROM lecturas WHERE id = ?
                    """,
                    (lectura_id,),
                )
                row = cursor.fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Error al analizar lectura {lectura_id}: {exc}") from exc

        if not row:
            raise DatabaseError(f"No se encontro lectura con ID {lectura_id}")

        texto_completo = " ".join(str(c) for c in row[:4] if c)
        vector = self.extractor.extract(texto_completo)
        momento = self._inferir_momento_lectura(row["celebracion"])
        resultado = (vector, momento)

        if self.config.cache_activa:
            self._lectura_cache[lectura_id] = resultado

        return resultado

    def analizar_cancion(self, cancion_id: int) -> tuple[ThemeVector, str | None, str]:
        if self.config.cache_activa and cancion_id in self._cancion_cache:
            return self._cancion_cache[cancion_id]

        cancion_id = self.validator.validar_id(cancion_id, "cancion_id")

        try:
            with sqlite3.connect(str(self.config.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT letra_sin_acordes, momento_liturgico, titulo FROM canciones WHERE id = ?",
                    (cancion_id,),
                )
                row = cursor.fetchone()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Error al analizar cancion {cancion_id}: {exc}") from exc

        if not row or not row["letra_sin_acordes"]:
            raise DatabaseError(f"No se encontro cancion con ID {cancion_id} o carece de letra")

        vector = self.extractor.extract(row["letra_sin_acordes"])
        momento = (row["momento_liturgico"] or "general").strip().lower()
        resultado = (vector, momento, row["titulo"])

        if self.config.cache_activa:
            self._cancion_cache[cancion_id] = resultado

        return resultado

    def encontrar_canciones_para_lectura(
        self,
        lectura_id: int,
        limite: int | None = None,
        score_minimo: float | None = None,
    ) -> list[dict[str, Any]]:
        lectura_id = self.validator.validar_id(lectura_id, "lectura_id")
        limite = self.validator.validar_limite(limite or self.config.limite_resultados)
        score_minimo = self.validator.validar_score(score_minimo or self.config.score_minimo)

        vector_lectura, momento_lectura = self.analizar_lectura(lectura_id)
        if not vector_lectura.temas:
            logger.warning("No se pudieron extraer temas de la lectura %s", lectura_id)
            return []

        try:
            with sqlite3.connect(str(self.config.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT id, titulo, momento_liturgico FROM canciones")
                canciones = cursor.fetchall()
        except sqlite3.Error as exc:
            raise DatabaseError(f"Error al listar canciones: {exc}") from exc

        matches: list[dict[str, Any]] = []
        for row in canciones:
            cancion_id = row["id"]
            try:
                vector_cancion, momento_cancion, titulo = self.analizar_cancion(cancion_id)
            except DatabaseError:
                continue

            score = self.normalizer.calcular_score(
                vector_lectura,
                vector_cancion,
                momento_lectura=momento_lectura,
                momento_cancion=momento_cancion,
                boost=self.config.momento_liturgico_boost,
                afinidad=self.config.afinidad_momento_tema,
            )

            if score >= score_minimo:
                temas_comunes = sorted(
                    set(vector_lectura.temas.keys()) & set(vector_cancion.temas.keys()),
                    key=lambda t: vector_lectura.temas[t] * vector_cancion.temas[t],
                    reverse=True,
                )
                matches.append({
                    "cancion_id": cancion_id,
                    "titulo": titulo,
                    "score": round(score, 3),
                    "temas_comunes": temas_comunes,
                    "momento_liturgico": momento_cancion,
                })

        matches.sort(key=lambda x: x["score"], reverse=True)
        return matches[:limite]

    def guardar_match(
        self,
        lectura_id: int,
        cancion_id: int,
        score: float,
        momento_liturgico: str | None = None,
    ) -> None:
        lectura_id = self.validator.validar_id(lectura_id, "lectura_id")
        cancion_id = self.validator.validar_id(cancion_id, "cancion_id")
        score = self.validator.validar_score(score)
        self.repository.guardar(lectura_id, cancion_id, score, momento_liturgico)

    @staticmethod
    def _inferir_momento_lectura(celebracion: str | None) -> str | None:
        if not celebracion:
            return None
        celebracion_lower = celebracion.lower()
        mapping = {
            "adviento": "entrada",
            "navidad": "entrada",
            "cuaresma": "perdon",
            "semana santa": "perdon",
            "pascua": "aleluya",
            "pentecostes": "espiritu",
            "ordinario": "general",
        }
        for clave, momento in mapping.items():
            if clave in celebracion_lower:
                return momento
        return None


# ---------------------------------------------------------------------------
# Fachada
# ---------------------------------------------------------------------------


class MatchingEngine:
    """Fachada pública compatible con el uso anterior del motor de matching."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        config = MatchingConfig.load()
        if db_path:
            config = MatchingConfig.from_dict({**DEFAULT_CONFIG, "db_path": str(db_path)})
        self.service = MatchingService(config)

    def extraer_temas_de_texto(self, texto: str | None) -> list[dict[str, Any]]:
        vector = self.service.extractor.extract(texto)
        items = [
            {"tema": tema, "score": score, "palabras": vector.palabras_halladas.get(tema, [])}
            for tema, score in vector.temas.items()
        ]
        items.sort(key=lambda x: x["score"], reverse=True)
        return items

    def analizar_lectura(self, lectura_id: int) -> list[dict[str, Any]] | None:
        try:
            vector, _ = self.service.analizar_lectura(lectura_id)
            return self._vector_a_lista(vector)
        except MatchingError:
            return None

    def analizar_cancion(self, cancion_id: int) -> list[dict[str, Any]] | None:
        try:
            vector, _, _ = self.service.analizar_cancion(cancion_id)
            return self._vector_a_lista(vector)
        except MatchingError:
            return None

    def calcular_match(
        self,
        temas_lectura: list[dict[str, Any]],
        temas_cancion: list[dict[str, Any]],
    ) -> float:
        vector_lectura = ThemeVector(temas={t["tema"]: t["score"] for t in temas_lectura})
        vector_cancion = ThemeVector(temas={t["tema"]: t["score"] for t in temas_cancion})
        return self.service.normalizer.calcular_score(vector_lectura, vector_cancion)

    def encontrar_canciones_para_lectura(
        self,
        lectura_id: int,
        limite: int = 5,
        score_minimo: float = 0.15,
    ) -> list[dict[str, Any]]:
        return self.service.encontrar_canciones_para_lectura(
            lectura_id, limite=limite, score_minimo=score_minimo
        )

    def guardar_match(
        self,
        lectura_id: int,
        cancion_id: int,
        score: float,
        momento_liturgico: str = "general",
    ) -> None:
        self.service.guardar_match(lectura_id, cancion_id, score, momento_liturgico)

    def _vector_a_lista(self, vector: ThemeVector) -> list[dict[str, Any]]:
        items = [
            {"tema": tema, "score": score, "palabras": vector.palabras_halladas.get(tema, [])}
            for tema, score in vector.temas.items()
        ]
        items.sort(key=lambda x: x["score"], reverse=True)
        return items
