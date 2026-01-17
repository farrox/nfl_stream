#!/usr/bin/env python3
"""Verify syntax of stream_refresher.py"""
import ast
import sys

def check_syntax(filename):
    try:
        with open(filename, 'r') as f:
            source = f.read()
        
        # Try to parse the AST
        ast.parse(source, filename)
        print(f"✓ Syntax check PASSED for {filename}")
        return True
    except SyntaxError as e:
        print(f"✗ Syntax error in {filename}:")
        print(f"  Line {e.lineno}: {e.text}")
        print(f"  Error: {e.msg}")
        if e.offset:
            print(f"  Position: {e.offset}")
        return False
    except Exception as e:
        print(f"✗ Error checking {filename}: {e}")
        return False

if __name__ == '__main__':
    success = check_syntax('stream_refresher.py')
    sys.exit(0 if success else 1)
