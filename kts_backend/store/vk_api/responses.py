from dataclasses import dataclass, asdict


@dataclass(init=False)
class VKUser:
    id: int
    first_name: str
    last_name: str

    def __init__(self, data: dict):
        self.id = data["id"]
        self.first_name = data["first_name"]
        self.last_name = data["last_name"]

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def as_dict(self) -> dict:
        return asdict(self)
