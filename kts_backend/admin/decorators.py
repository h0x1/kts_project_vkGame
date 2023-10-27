from functools import wraps

from aiohttp.web_exceptions import HTTPForbidden, HTTPUnauthorized
from aiohttp_session import get_session

from app.web.app import View


def auth_required(wrapped_func):
    @wraps(wrapped_func)
    async def wrapper(self: View, *args, **kwargs):
        if self.request.admin is None:
            raise HTTPUnauthorized

        return await wrapped_func(self, *args, **kwargs)

    return wrapper
