from aiohttp.web_exceptions import HTTPUnauthorized, HTTPNotFound, HTTPForbidden
from aiohttp_apispec import docs, request_schema, response_schema
from aiohttp_session import new_session, get_session

from app.admin.schemes import (
    AdminResponseSchema,
    AdminAuthRequestSchema,
)
from app.admin.decorators import auth_required
from app.web.app import View
from app.web.utils import json_response


class AdminLoginView(View):
    @docs(
        tags=["admin"],
        summary="Get info about current user",
        description="Get info about current user",
    )
    @request_schema(AdminAuthRequestSchema)
    @response_schema(AdminResponseSchema, 200)
    async def post(self):
        data_from_db = await self.store.admins.get_by_email(self.data["email"])
        if data_from_db is None:
            raise HTTPForbidden
        response_data = AdminResponseSchema().dump(data_from_db)

        session = await new_session(request=self.request)
        session["user_data"] = response_data
        return json_response(data=response_data)


class AdminCreateView(View):
    @docs(
        tags=["admin"],
        summary="Get info about current user",
        description="Get info about current user",
    )
    @response_schema(AdminResponseSchema, 200)
    async def post(self):
        data_from_db = await self.store.admins.create_admin(
            "admin@admin.com", "123"
        )
        if data_from_db is None:
            raise HTTPForbidden
        response_data = AdminResponseSchema().dump(data_from_db)

        session = await new_session(request=self.request)
        session["user_data"] = response_data
        return json_response(data=response_data)


class AdminCurrentView(View):
    @auth_required
    @docs(
        tags=["admin"],
        summary="Get info about current user",
        description="Get info about current user",
    )
    @response_schema(AdminResponseSchema, 200)
    async def get(self):
        return json_response(
            data=AdminResponseSchema().dump(self.request.admin)
        )
