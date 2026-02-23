#!/usr/bin/env python3
"""Compatibility entrypoint for the GhostRoute CLI.

Historically this project exposed console_scripts as:
  - ghostroute=main:main

We now keep the implementation inside the `ghostroute` package while preserving
the original module entrypoint to avoid breaking existing installs.
"""

from ghostroute.cli import main


if __name__ == "__main__":
    main()
