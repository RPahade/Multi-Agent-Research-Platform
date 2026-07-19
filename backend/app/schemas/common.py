"""Shared schema utilities: pagination params and a generic page envelope."""

from __future__ import annotations

from math import ceil
from typing import Generic, TypeVar

from fastapi import Query
from pydantic import BaseModel

T = TypeVar("T")


class PageParams:
    """Common pagination query params (?page=&size=), used as a dependency."""

    def __init__(
        self,
        page: int = Query(1, ge=1, description="1-based page number"),
        size: int = Query(20, ge=1, le=100, description="items per page (max 100)"),
    ) -> None:
        self.page = page
        self.size = size


class Page(BaseModel, Generic[T]):
    """A paginated list response."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int

    @classmethod
    def create(cls, items: list[T], total: int, params: PageParams) -> "Page[T]":
        return cls(
            items=items,
            total=total,
            page=params.page,
            size=params.size,
            pages=ceil(total / params.size) if params.size else 0,
        )
