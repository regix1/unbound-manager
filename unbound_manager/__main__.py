#!/usr/bin/env python3
"""Entry point for the unbound-manager application."""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())