"""Unbound Manager - A modern DNS server management tool."""

from .constants import APP_VERSION

__version__ = APP_VERSION
__author__ = "Regix"

from .cli import main

__all__ = ["main", "__version__"]