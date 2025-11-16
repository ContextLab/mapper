#!/usr/bin/env python3
"""
Test script to validate all external links in the About modal.

This script makes real HTTP requests to verify that all links work correctly.
NO MOCKS - Real testing only!
"""

import requests
import time
import sys

# Links from the About modal
links = {
    'Paper (preprint)': 'https://osf.io/preprints/psyarxiv/dh3q2_v2',
    'GitHub Repository': 'https://github.com/ContextLab/efficient-learning-khan',
    'NSF Grant': 'https://www.nsf.gov/awardsearch/show-award/?AWD_ID=2145172&HistoricalAwards=false',
    'Context Lab': 'https://context-lab.com',
    'Contact Page': 'https://www.context-lab.com/contact'
}

def test_link(name, url):
    """Test a single link with real HTTP request"""
    try:
        print(f"Testing: {name}")
        print(f"  URL: {url}")

        # Make HEAD request first (faster)
        response = requests.head(url, timeout=10, allow_redirects=True)

        # Some servers don't support HEAD, try GET if HEAD fails
        if response.status_code >= 400:
            response = requests.get(url, timeout=10, allow_redirects=True)

        if 200 <= response.status_code < 400:
            print(f"  ✓ Status: {response.status_code}")
            if response.url != url:
                print(f"  → Redirected to: {response.url}")
            return True
        else:
            print(f"  ✗ Status: {response.status_code}")
            return False

    except requests.exceptions.Timeout:
        print(f"  ✗ Timeout after 10 seconds")
        return False
    except requests.exceptions.RequestException as e:
        print(f"  ✗ Error: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Unexpected error: {e}")
        return False

def main():
    print("="*80)
    print("ABOUT MODAL LINK VALIDATION TEST")
    print("="*80)
    print()
    print("Testing all external links with real HTTP requests...")
    print()

    results = {}

    for name, url in links.items():
        success = test_link(name, url)
        results[name] = success
        print()
        time.sleep(1)  # Be nice to servers

    # Summary
    print("="*80)
    print("TEST SUMMARY")
    print("="*80)
    print()

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, success in results.items():
        status = "✓ PASS" if success else "✗ FAIL"
        print(f"{status}: {name}")

    print()
    print(f"Results: {passed}/{total} links working")

    if passed == total:
        print()
        print("✓ All links are working correctly!")
        return 0
    else:
        print()
        print("✗ Some links failed. Please check the output above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
