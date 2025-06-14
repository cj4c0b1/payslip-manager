"""
Authentication package for the renato application.

This package provides passwordless authentication using magic links.
"""

from .models import MagicToken  # noqa

__version__ = "0.1.0"
__all__ = ["MagicToken"]
