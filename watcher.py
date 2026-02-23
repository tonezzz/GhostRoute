#!/usr/bin/env python3
"""Compatibility entrypoint for GhostRoute watcher.

Historically:
  - ghostroute-watcher=watcher:main

Implementation now lives in `ghostroute.watcher`.
"""

from ghostroute.watcher import main


if __name__ == "__main__":
    main()
