import base64
import typing
from hashlib import sha256
from typing import Optional
from sqlalchemy import select
from kts_backend.base.base_accessor import BaseAccessor
from kts_backend.admin.models import Admin, AdminModel
from kts_backend.admin.models import Admin
import bcrypt

if typing.TYPE_CHECKING:
    from kts_backend.web.app import Application


class AdminAccessor(BaseAccessor):
    async def get_by_email(self, email: str) -> Admin | None:
        async with self.app.database.session() as session:
            admin = (
                await session.execute(
                    select(AdminModel).where(AdminModel.email == email)
                )
            ).scalar()
        if not admin:
            return
        return admin.to_dc()

    async def create_admin(self, email: str, password: str) -> Admin:
        async with self.app.database.session.begin() as session:
            new_admin = AdminModel(
                email=email, password=self._password_hasher(password)
            )
            session.add(new_admin)
            return new_admin.to_dc()

    @staticmethod
    def _password_hasher(raw_password: str) -> str:
        hash_binary = bcrypt.hashpw(
            raw_password.encode("utf-8"), bcrypt.gensalt()
        )
        encoded = base64.b64encode(hash_binary)
        return encoded.decode("utf-8")
