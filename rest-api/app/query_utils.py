"""
query_utils.py: small helpers for reading query-string parameters.
"""

from fastapi import HTTPException


def parse_ids(value: str | None, name: str) -> list[int] | None:
    """
    Turn "1,2,3" into [1, 2, 3]. Returns None when the parameter was not sent.

    Used for BATCH lookups such as GET /books?ids=1,2,3, which let a client
    (like the GraphQL gateway) fetch many items in ONE request instead of one
    request per item.
    """
    if value is None:
        return None
    try:
        return [int(part) for part in value.split(",") if part.strip()]
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{name} must be comma-separated integers")
