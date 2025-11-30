#!/usr/bin/env python3
"""
Scan directory for .adg files and output list
"""

import sys
from pathlib import Path

def scan_adg_files(directory):
    """Recursively scan for .adg files"""
    dir_path = Path(directory)
    if not dir_path.exists():
        print(f"Error: Directory does not exist: {directory}", file=sys.stderr)
        return []

    adg_files = sorted(dir_path.rglob("*.adg"))
    return [str(f) for f in adg_files]

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: scan_adg_files.py /path/to/directory")
        sys.exit(1)

    directory = sys.argv[1]
    files = scan_adg_files(directory)

    # Output one file per line
    for f in files:
        print(f)
