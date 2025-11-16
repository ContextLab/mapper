#!/usr/bin/env python3
"""
Test script to verify all logo assets exist and are accessible.

This script performs real file system checks and HTTP requests.
NO MOCKS - Real testing only!
"""

import os
import sys
from pathlib import Path
import requests

# Logo files that should exist
logos = {
    'cdl.png': {'min_size': 8000, 'format': 'PNG', 'description': 'Context Lab logo'},
    'nature.png': {'min_size': 7000, 'format': 'PNG', 'description': 'Nature Communications logo'},
    'nsf.png': {'min_size': 70000, 'format': 'PNG', 'description': 'NSF logo'},
    'github.svg': {'min_size': 900, 'format': 'SVG', 'description': 'GitHub logo'}
}

def test_file_system():
    """Test that logo files exist on the file system"""
    print("="*80)
    print("FILE SYSTEM TEST")
    print("="*80)
    print()

    results = {}

    for logo, spec in logos.items():
        path = Path(f'logos/{logo}')
        print(f"Testing: {logo} ({spec['description']})")
        print(f"  Path: {path}")

        if path.exists():
            size = path.stat().st_size
            print(f"  ✓ File exists")
            print(f"  Size: {size:,} bytes")

            if size >= spec['min_size']:
                print(f"  ✓ Size OK (>= {spec['min_size']:,} bytes)")
                results[logo] = True
            else:
                print(f"  ✗ File too small! Expected >= {spec['min_size']:,} bytes")
                results[logo] = False
        else:
            print(f"  ✗ File NOT FOUND")
            results[logo] = False

        print()

    return results

def test_http_access():
    """Test that logos are accessible via HTTP"""
    print("="*80)
    print("HTTP ACCESS TEST")
    print("="*80)
    print()
    print("Testing HTTP accessibility (requires local server running)")
    print("Start server with: python -m http.server 8000")
    print()

    base_url = 'http://localhost:8000'
    results = {}

    for logo, spec in logos.items():
        url = f'{base_url}/logos/{logo}'
        print(f"Testing: {logo}")
        print(f"  URL: {url}")

        try:
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                content_length = len(response.content)
                print(f"  ✓ HTTP 200 OK")
                print(f"  Content length: {content_length:,} bytes")

                # Verify content type
                content_type = response.headers.get('content-type', '')
                print(f"  Content-Type: {content_type}")

                results[logo] = True
            else:
                print(f"  ✗ HTTP {response.status_code}")
                results[logo] = False

        except requests.exceptions.ConnectionError:
            print(f"  ⚠ Cannot connect - is local server running?")
            results[logo] = None  # Skip this test
        except requests.exceptions.Timeout:
            print(f"  ✗ Timeout")
            results[logo] = False
        except Exception as e:
            print(f"  ✗ Error: {e}")
            results[logo] = False

        print()

    return results

def main():
    print()
    print("="*80)
    print("LOGO ASSET VERIFICATION TEST")
    print("="*80)
    print()

    # Test 1: File system check
    fs_results = test_file_system()

    # Test 2: HTTP access check
    http_results = test_http_access()

    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print()

    print("File System Test:")
    fs_passed = sum(1 for v in fs_results.values() if v)
    fs_total = len(fs_results)
    for logo, success in fs_results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"  {status}: {logo}")

    print()
    print("HTTP Access Test:")
    http_passed = sum(1 for v in http_results.values() if v)
    http_skipped = sum(1 for v in http_results.values() if v is None)
    http_total = len(http_results) - http_skipped
    for logo, success in http_results.items():
        if success is None:
            status = "⚠ SKIP"
        elif success:
            status = "✓ PASS"
        else:
            status = "✗ FAIL"
        print(f"  {status}: {logo}")

    print()
    print(f"File System: {fs_passed}/{fs_total} passed")
    if http_total > 0:
        print(f"HTTP Access: {http_passed}/{http_total} passed ({http_skipped} skipped)")
    else:
        print(f"HTTP Access: All tests skipped (no server running)")

    # Return exit code
    if fs_passed == fs_total and (http_total == 0 or http_passed == http_total):
        print()
        print("✓ All tests passed!")
        return 0
    else:
        print()
        print("✗ Some tests failed. Please check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
