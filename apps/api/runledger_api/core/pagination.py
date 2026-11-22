"""One pagination standard for list endpoints (review: pagination audit).

Every collection endpoint takes ``?limit=&offset=`` (default 200, max 1000) so no list
grows without bound, and reports the full size in response headers:

    X-Total-Count: <rows matching the filters>
    X-Has-More:    true | false

Response bodies are unchanged, so existing clients keep working; clients that page read
the headers (``apps/web/lib/api.ts`` → ``apiFetchPage``).

Usage in a router::

    @router.get("/things")
    async def list_things(page: PageDep, response: Response, db: DbDep):
        stmt = select(Thing).where(...).order_by(Thing.created_at.desc(), Thing.id)
        rows = await paginate(db, stmt, page, response)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

DEFAULT_LIMIT = 200
MAX_LIMIT = 1000


@dataclass(frozen=True)
class PageParams:
    limit: int
    offset: int


def page_params(
    limit: Annotated[
        int, Query(ge=1, le=MAX_LIMIT, description="Max rows to return")
    ] = DEFAULT_LIMIT,
    offset: Annotated[int, Query(ge=0, description="Rows to skip")] = 0,
) -> PageParams:
    return PageParams(limit=limit, offset=offset)


PageDep = Annotated[PageParams, Depends(page_params)]


def set_page_headers(response: Response, total: int, page: PageParams, returned: int) -> None:
    response.headers["X-Total-Count"] = str(total)
    response.headers["X-Has-More"] = "true" if page.offset + returned < total else "false"


async def paginate(
    db: AsyncSession, stmt: Any, page: PageParams, response: Response | None = None
) -> list[Any]:
    """Run ``stmt`` (an ORM select) for one page; set the total headers when given."""
    total = (
        await db.execute(select(func.count()).select_from(stmt.order_by(None).subquery()))
    ).scalar_one()
    rows = list((await db.execute(stmt.limit(page.limit).offset(page.offset))).scalars().all())
    if response is not None:
        set_page_headers(response, int(total), page, len(rows))
    return rows


def paginate_list(
    items: list[Any], page: PageParams, response: Response | None = None
) -> list[Any]:
    """Page an already-built list (aggregations, merged sources)."""
    chunk = items[page.offset : page.offset + page.limit]
    if response is not None:
        set_page_headers(response, len(items), page, len(chunk))
    return chunk
