"""ALG4-223: POST /api/v1/reviews."""

import pytest

from src.reviews.dependencies import get_review_service
from src.reviews.service import ReviewService
from tests import fakes

URL = "/api/v1/reviews"


def client(uid: str = fakes.BORROWER):
    store = fakes.FakeStore()
    return fakes.client_as(
        uid, {get_review_service: lambda: ReviewService(store)}
    ), store


def test_review_is_saved():
    context, store = client()
    with context as c:
        response = c.post(
            URL, json={"rating": 5, "comment": " Quick answers from my broker "}
        )
    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == 5
    assert body["comment"] == "Quick answers from my broker"
    assert body["userId"] == fakes.BORROWER
    assert store.saved[0].rating == 5


def test_empty_comment_is_stored_as_none():
    context, store = client()
    with context as c:
        assert (
            c.post(URL, json={"rating": 3, "comment": "   "}).json()["comment"] is None
        )
        assert c.post(URL, json={"rating": 4}).json()["comment"] is None
    assert [r.comment for r in store.saved] == [None, None]


@pytest.mark.parametrize(
    "payload", [{"rating": 0}, {"rating": 6}, {"rating": 4, "comment": "x" * 257}, {}]
)
def test_invalid_review_is_rejected(payload):
    context, store = client()
    with context as c:
        assert c.post(URL, json=payload).status_code == 422
    assert store.saved == []


def test_only_borrowers_review():
    context, _ = client(fakes.OFFICER)
    with context as c:
        assert c.post(URL, json={"rating": 5}).status_code == 403
