#!/usr/bin/env python3
"""Quick syntax check for stream_refresher.py"""

import py_compile
import sys

try:
    py_compile.compile('stream_refresher.py', doraise=True)
    print("✓ Syntax check passed! No errors found.")
    sys.exit(0)
except py_compile.PyCompileError as e:
    print(f"✗ Syntax error found:")
    print(e)
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    sys.exit(1)
