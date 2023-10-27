from aiohttp.web import (
    Application as AiohttpApplication,
    View as AiohttpView,
    Request as AiohttpRequest,
)

import logging


from app.web.config import Config, setup_config
from app.web.routes import setup_routes
from app.web.mw import setup_middlewares

from aiohttp_apispec import setup_aiohttp_apispec
from aiohttp_session import setup as setup_aiohttp_session
from aiohttp_session.cookie_storage import EncryptedCookieStorage
from app.store import setup_store, Store
from app.store.database.database import Database
from app.logger import setup_logging

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
    setup_store(app)

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
