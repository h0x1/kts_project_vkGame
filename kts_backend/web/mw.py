import json
import typing

from aiohttp.web_exceptions import (
    HTTPUnprocessableEntity,
    HTTPForbidden,
    HTTPClientError,
)
from aiohttp.web_middlewares import middleware
from aiohttp_apispec import validation_middleware
from aiohttp_session import get_session

from kts_backend.web.utils import error_json_response

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application, Request

HTTP_ERROR_CODES = {
    400: "bad_request",
    401: "unauthorized",
    403: "forbidden",
    404: "not_found",
    405: "not_implemented",
    409: "conflict",
    500: "internal_server_error",
}


@middleware
async def error_handling_middleware(request: "Request", handler):
    try:
        response = await handler(request)
        return response
    except HTTPUnprocessableEntity as e:
        return error_json_response(
            http_status=400,
            status=HTTP_ERROR_CODES[400],
            message=e.reason,
            data=json.loads(e.text),
        )
    except HTTPClientError as e:
        return error_json_response(
            http_status=e.status_code,
            status=HTTP_ERROR_CODES[e.status_code],
            message=e.reason,
            data=e.text,
        )
    except Exception as e:
        return error_json_response(
            http_status=500, status="internal server error", message=str(e)
        )


@middleware
async def auth_check_middleware(request: "Request", handler):
    session = await get_session(request)

    if (user_data := session.get("user_data")) is not None:
        try:
            session_email = user_data["email"]
            session_id = user_data["id"]
        except KeyError:
            raise HTTPForbidden(reason=f"Forbidden")

        db_data = await request.app.store.admins.get_by_email(session_email)

        if (db_data is None) or (db_data.id != session_id):
            raise HTTPForbidden(reason=f"Forbidden")

        request.admin = db_data
    else:
        request.admin = None

    response = await handler(request)
    return response


def setup_middlewares(app: "Application"):
    app.middlewares.append(error_handling_middleware)
    app.middlewares.append(auth_check_middleware)
    app.middlewares.append(validation_middleware)
