"""Parsing herdr's JSON replies."""

import pytest
from pydantic import BaseModel

from herdr_tools.client import HerdrError
from herdr_tools.replies import Reply, parse


class _Tab(BaseModel):
    tab_id: str


def test_parse_reads_the_result_envelope() -> None:
    reply: Reply[_Tab] = parse(Reply[_Tab], '{"id": "1", "result": {"tab_id": "t_1"}}')

    assert reply.result.tab_id == "t_1"


def test_parse_raises_herdr_error_on_unexpected_shape() -> None:
    with pytest.raises(HerdrError, match="unexpected herdr reply"):
        parse(Reply[_Tab], '{"id": "1", "result": {}}')
