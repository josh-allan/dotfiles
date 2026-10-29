"""Validates herdr's JSON replies into Pydantic models."""

from pydantic import BaseModel, ValidationError

from herdr_tools.client import HerdrError


class Reply[T](BaseModel):
    """The result envelope every herdr CLI JSON reply uses."""

    result: T


def parse[M: BaseModel](shape: type[M], output: str) -> M:
    """Validate `output` as `shape`; raise `HerdrError` when it does not fit."""
    try:
        return shape.model_validate_json(output)
    except ValidationError as error:
        raise HerdrError(f"unexpected herdr reply: {error}") from error
