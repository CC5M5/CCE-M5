"""Adaptador WSGI para montar apps Flask de editores bajo FastAPI.

Cada editor Flask espera servirse desde la raíz (/). Al montarlas en FastAPI
bajo /editor-acordes/ y /editor-diapositivas/ debemos reescribir el SCRIPT_NAME
y PATH_INFO del entorno WSGI para que Flask resuelva sus rutas correctamente.

Las URLs generadas por Flask (url_for) y redirects a / seguirán apuntando al
path raíz del editor; en la práctica los editores usan URLs relativas o
hardcodeadas en los templates, por lo que esto es suficiente para conservar
la funcionalidad legacy mientras se centraliza el servidor.
"""

from __future__ import annotations

from a2wsgi import WSGIMiddleware


class PrefixedWSGIMiddleware(WSGIMiddleware):
    """WSGI middleware que expone una app Flask bajo un path prefix de FastAPI.

    Se usa con app.add_route("/editor-acordes/{path:path}", ...) para que el
    scope de Starlette llegue con el path completo. El middleware ajusta
    SCRIPT_NAME y PATH_INFO del entorno WSGI antes de invocar Flask.
    """

    def __init__(self, flask_app, *, prefix: str) -> None:  # noqa: D107
        super().__init__(flask_app)
        self.prefix = prefix.rstrip("/")

    async def __call__(self, scope, receive, send):  # noqa: D102
        if scope["type"] == "http":
            scope["root_path"] = self.prefix
            path = scope.get("path", "/")
            if not path.startswith(self.prefix + "/") and path != self.prefix:
                # Normalizar si Starlette quitó el prefijo (no debería con add_route)
                path = self.prefix + path
            scope["path"] = path
        return await super().__call__(scope, receive, send)
