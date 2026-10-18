"""Tests para src/matching_engine.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.matching_engine import (
    ConfigError,
    InputValidator,
    MatchingConfig,
    MatchRepository,
    ScoreNormalizer,
    TextPreprocessor,
    ThemeExtractor,
    ThemeVector,
)


class TestMatchingConfig:
    def test_from_dict_defaults(self) -> None:
        cfg = MatchingConfig.from_dict({})
        assert cfg.score_minimo == 0.15
        assert cfg.limite_resultados == 5

    def test_from_dict_valid(self) -> None:
        cfg = MatchingConfig.from_dict(
            {"score_minimo": 0.5, "limite_resultados": 10, "momento_liturgico_boost": 0.2}
        )
        assert cfg.score_minimo == 0.5
        assert cfg.limite_resultados == 10
        assert cfg.momento_liturgico_boost == 0.2

    def test_from_dict_invalid(self) -> None:
        with pytest.raises(ConfigError, match="score_minimo"):
            MatchingConfig.from_dict({"score_minimo": 1.5})
        with pytest.raises(ConfigError, match="limite_resultados"):
            MatchingConfig.from_dict({"limite_resultados": 0})

    def test_load_default(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "matching_config.json"
        cfg = MatchingConfig.load(cfg_path)
        assert cfg_path.exists()
        assert cfg.score_minimo == 0.15

    def test_load_existing(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "matching_config.json"
        cfg_path.write_text(json.dumps({"score_minimo": 0.3, "limite_resultados": 3}, ensure_ascii=False))
        cfg = MatchingConfig.load(cfg_path)
        assert cfg.score_minimo == 0.3
        assert cfg.limite_resultados == 3

    def test_load_invalid_json(self, tmp_path: Path) -> None:
        cfg_path = tmp_path / "matching_config.json"
        cfg_path.write_text("not json")
        with pytest.raises(ConfigError, match="JSON invalido"):
            MatchingConfig.load(cfg_path)


class TestTextPreprocessor:
    def test_tokenize(self) -> None:
        tp = TextPreprocessor()
        assert tp.tokenize("La paz del Señor") == ["la", "paz", "del", "señor"]

    def test_tokenize_empty(self) -> None:
        tp = TextPreprocessor()
        assert tp.tokenize(None) == []
        assert tp.tokenize("") == []

    def test_contar_frecuencias(self) -> None:
        tp = TextPreprocessor()
        assert tp.contar_frecuencias("paz paz amor") == {"paz": 2, "amor": 1}


class TestThemeExtractor:
    def test_extract_temas(self) -> None:
        cfg = MatchingConfig.from_dict({})
        te = ThemeExtractor(cfg)
        vector = te.extract("amor y paz en el corazón")
        assert "amor" in vector.temas
        assert "paz" in vector.temas
        assert vector.temas["amor"] == 1.3
        assert "amor" in vector.palabras_halladas["amor"]

    def test_extract_empty(self) -> None:
        cfg = MatchingConfig.from_dict({})
        te = ThemeExtractor(cfg)
        assert te.extract("") == ThemeVector()


class TestScoreNormalizer:
    def test_score_sin_temas_comunes(self) -> None:
        cfg = MatchingConfig.from_dict({})
        sn = ScoreNormalizer(ThemeExtractor(cfg))
        v1 = ThemeVector(temas={"amor": 1.0})
        v2 = ThemeVector(temas={"paz": 1.0})
        assert sn.calcular_score(v1, v2) == 0.0

    def test_score_con_temas_comunes(self) -> None:
        cfg = MatchingConfig.from_dict({})
        sn = ScoreNormalizer(ThemeExtractor(cfg))
        v1 = ThemeVector(temas={"amor": 1.0})
        v2 = ThemeVector(temas={"amor": 1.0})
        score = sn.calcular_score(v1, v2)
        assert 0.0 < score <= 1.0

    def test_boost_momento(self) -> None:
        cfg = MatchingConfig.from_dict({})
        sn = ScoreNormalizer(ThemeExtractor(cfg))
        v1 = ThemeVector(temas={"amor": 1.0})
        v2 = ThemeVector(temas={"amor": 1.0})
        score = sn.calcular_score(v1, v2, momento_lectura="santo", momento_cancion="santo", boost=0.1)
        assert score == 1.0  # se clampa a 1.0


class TestInputValidator:
    def test_validar_id(self) -> None:
        assert InputValidator.validar_id(5, "id") == 5
        assert InputValidator.validar_id("7", "id") == 7
        with pytest.raises(Exception):
            InputValidator.validar_id(-1, "id")
        with pytest.raises(Exception):
            InputValidator.validar_id("abc", "id")

    def test_validar_score(self) -> None:
        assert InputValidator.validar_score(0.5) == 0.5
        with pytest.raises(Exception):
            InputValidator.validar_score(1.5)

    def test_validar_limite(self) -> None:
        assert InputValidator.validar_limite(3) == 3
        with pytest.raises(Exception):
            InputValidator.validar_limite(0)


class TestMatchRepository:
    def test_ensure_table_y_guardar(self, tmp_path: Path) -> None:
        db = tmp_path / "test.sqlite3"
        repo = MatchRepository(db)
        repo.ensure_table()
        repo.guardar(1, 2, 0.85, "entrada")
        rows = repo.obtener_por_lectura(1)
        assert len(rows) == 1
        assert rows[0]["cancion_id"] == 2
        assert rows[0]["score"] == 0.85
