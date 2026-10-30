import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Kind = Literal["meal", "supplement", "training"]
_HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class RegisterCoach(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    invite_code: str


class Login(BaseModel):
    email: str
    password: str


class StudentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(min_length=3, max_length=120)
    password: str = Field(min_length=8, max_length=128)


class ItemIn(BaseModel):
    kind: Kind
    slot: str = ""
    title: str = Field(default="", max_length=200)
    details: dict = Field(default_factory=dict)

    @field_validator("slot")
    @classmethod
    def _slot(cls, v, info):
        return v.strip()


class ItemPatch(BaseModel):
    slot: str | None = None
    title: str | None = Field(default=None, max_length=200)
    details: dict | None = None
    active: bool | None = None
    position: int | None = None


class MoodIn(BaseModel):
    mood: str = Field(default="", max_length=40)
    note: str = Field(default="", max_length=300)


class GymIn(BaseModel):
    action: Literal["in", "out"]


def valid_hhmm(v: str) -> bool:
    return bool(_HHMM.match(v))
