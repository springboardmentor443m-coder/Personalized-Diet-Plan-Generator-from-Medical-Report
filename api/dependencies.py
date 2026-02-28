"""API key authentication dependency."""

import logging

from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from config.settings import API_KEY

logger = logging.getLogger(__name__)

_header_scheme = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(
    api_key: str | None = Security(_header_scheme),
) -> str | None:
    """Validate X-API-Key header. Skips check if API_KEY is unset (dev mode)."""
    if not API_KEY:
        # No key configured → open access (development mode)
        return None

    if not api_key:
        logger.warning("Request rejected: missing X-API-Key header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-API-Key header.",
        )

    if api_key != API_KEY:
        logger.warning("Request rejected: invalid API key")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid API key.",
        )

    return api_key
