from typing import Sequence, Callable

from aiohttp.web import (
    Application as AiohttpApplication,
    View as AiohttpView,
    Request as AiohttpRequest,
)
from pyparsing import Optional

import logging


from kts_backend.web.config import Config, setup_config
from kts_backend.web.routes import setup_routes
from kts_backend.web.mw import setup_middlewares

from aiohttp_apispec import setup_aiohttp_apispec
from aiohttp_session import setup as setup_aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from kts_backend.admin.models import Admin
from kts_backend.store import Store, BotManager
from kts_backend.database.database import Database
from kts_backend.logger import setup_logging

from .urls import register_urls

__all__ = "ApiApplication"


class Application(AiohttpApplication):
    config = Config
    store = Store
    database = Database
    logger: logging.Logger


def setup_app(config_path: str) -> Application:
    app = Application()

    setup_config(app, config_path)
    setup_logging(app)
    setup_routes(app)
    setup_aiohttp_session(app, EncryptedCookieStorage(app.config.session.key))
    setup_middlewares(app)
    setup_aiohttp_apispec(
        app, title="vkGame", url="/docs/json", swagger_path="/docs"
    )

    app.store = Store(app)
    app.database = Database(app)
    app.on_startup.append(app.database.connect)
    app.on_cleanup.append(app.database.disconnect)
    return app


class Request(AiohttpRequest):
    @property
    def app(self) -> Application:
        return super().app()


class View(AiohttpView):
    @property
    def request(self) -> Request:
        return super().request

    @property
    def store(self) -> Store:
        return self.request.app.store

    @property
    def data(self) -> dict:
        return self.request.get("data", {})
