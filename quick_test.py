#!/usr/bin/env python3
"""Quick syntax and import test"""

print("Testing syntax...")
try:
    import py_compile
    py_compile.compile('stream_refresher.py', doraise=True)
    print("✓ Syntax check PASSED!")
except py_compile.PyCompileError as e:
    print(f"✗ Syntax error: {e}")
    exit(1)
except Exception as e:
    print(f"✗ Error: {e}")
    exit(1)

print("\nTesting import...")
try:
    import stream_refresher
    print("✓ Import test PASSED!")
    print(f"✓ Server will run on port 8080")
except Exception as e:
    print(f"✗ Import error: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print("\n✅ All checks passed! You can now run:")
print("   python3 stream_refresher.py")
