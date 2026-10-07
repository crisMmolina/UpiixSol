"""Cursor (keyset) pagination. No endpoint returns more than 50 items (IDEA §5).

    from app.pagination import CursorParam, LimitParam, paginate
    def list_posts(cursor: CursorParam = None, limit: LimitParam = 20, db=...):
        stmt = select(Post).where(...)
        return paginate(db, stmt, [Post.created_at, Post.id], cursor=cursor, limit=limit)

`order_by` columns must end with a unique column (usually the id) so pages never overlap.
"""

import base64
import binascii
import json
from collections.abc import Callable, Sequence
from datetime import datetime
from typing import Annotated, Any

from fastapi import Query
from sqlalchemy import Select, tuple_
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.types import TypeDecorator

from app.errors import AppError
from app.schemas.common import Page

MAX_LIMIT = 50
LimitParam = Annotated[int, Query(ge=1, le=MAX_LIMIT)]
CursorParam = Annotated[str | None, Query(max_length=500)]


def encode_cursor(values: Sequence[Any]) -> str:
    payload = [v.isoformat() if isinstance(v, datetime) else v for v in values]
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode()).decode().rstrip("=")


def _python_type(column: InstrumentedAttribute) -> type:
    sql_type = column.type
    if isinstance(sql_type, TypeDecorator):  # e.g. UTCDateTime → its DateTime impl
        sql_type = sql_type.impl_instance
    return sql_type.python_type


def decode_cursor(cursor: str, columns: Sequence[InstrumentedAttribute]) -> list[Any]:
    try:
        raw = base64.urlsafe_b64decode(cursor + "=" * (-len(cursor) % 4))
        values = json.loads(raw)
        if not isinstance(values, list) or len(values) != len(columns):
            raise ValueError
        return [
            datetime.fromisoformat(v) if _python_type(col) is datetime else _python_type(col)(v)
            for v, col in zip(values, columns, strict=True)
        ]
    except (ValueError, TypeError, OverflowError, binascii.Error, json.JSONDecodeError) as exc:
        raise AppError(422, "Cursor de paginación inválido.", code="invalid_cursor") from exc


def paginate[T](
    db: Session,
    stmt: Select,
    order_by: Sequence[InstrumentedAttribute],
    *,
    cursor: str | None,
    limit: int,
    descending: bool = True,
    transform: Callable[[Any], T] = lambda row: row,
) -> Page[T]:
    limit = max(1, min(limit, MAX_LIMIT))
    if cursor:
        values = decode_cursor(cursor, order_by)
        key = tuple_(*order_by)
        stmt = stmt.where(key < tuple_(*values) if descending else key > tuple_(*values))
    ordering = [c.desc() for c in order_by] if descending else [c.asc() for c in order_by]
    rows = list(db.scalars(stmt.order_by(*ordering).limit(limit + 1)))
    has_more = len(rows) > limit
    rows = rows[:limit]
    next_cursor = encode_cursor([getattr(rows[-1], c.key) for c in order_by]) if has_more else None
    return Page[T](items=[transform(row) for row in rows], next_cursor=next_cursor)
