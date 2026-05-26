"""Domain-level errors. API layer maps these to HTTP responses."""

from __future__ import annotations


class EngramError(Exception):
    """Base class for domain errors."""


class NotFoundError(EngramError):
    """A referenced entity does not exist."""


class ConflictError(EngramError):
    """The operation conflicts with existing state (e.g. duplicate link)."""


class ValidationError(EngramError):
    """The request is semantically invalid (e.g. self-link)."""
