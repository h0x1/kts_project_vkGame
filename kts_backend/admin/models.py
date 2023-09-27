from dataclasses import dataclass
from typing import Optional
from sqlalchemy import Column, String, BigInteger

from kts_backend.database.sqlalchemy_base import db


@dataclass
class Admin:
    id: int
    email: str
    password: Optional[str] = None


class AdminModel(db):
    __tablename__ = "admins"
    id = Column(BigInteger, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)

    def to_dc(self) -> Admin:
        return Admin(id=self.id, email=self.email, password=self.password)
