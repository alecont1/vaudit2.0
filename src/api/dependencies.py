"""Shared FastAPI dependencies.

Central location for dependency injection functions.
"""

from src.storage.database import get_session

__all__ = ["get_session"]
