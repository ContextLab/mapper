#!/usr/bin/env python3
"""Quick script to inspect Wikipedia data structure."""

import pickle
import hypertools as hyp

print("="*80)
print("Inspecting Wikipedia Data Sources")
print("="*80)

# 1. Hypertools
print("\n1. Hypertools wiki dataset:")
try:
    wiki_hyp = hyp.load('wiki')
    print(f"   Type: {type(wiki_hyp)}")

    if isinstance(wiki_hyp, dict):
        print(f"   Keys: {list(wiki_hyp.keys())}")
        for key in wiki_hyp.keys():
            val = wiki_hyp[key]
            print(f"   {key}: type={type(val)}, len={len(val) if hasattr(val, '__len__') else 'N/A'}")
            if hasattr(val, '__len__') and len(val) > 0:
                print(f"     First item type: {type(val[0])}")
                if isinstance(val[0], str):
                    print(f"     First item preview: {val[0][:100]}...")
    elif isinstance(wiki_hyp, list):
        print(f"   Length: {len(wiki_hyp)}")
        if len(wiki_hyp) > 0:
            print(f"   First item type: {type(wiki_hyp[0])}")
            if isinstance(wiki_hyp[0], str):
                print(f"   First item: {wiki_hyp[0][:200]}...")
except Exception as e:
    print(f"   Error: {e}")

# 2. Dropbox pickle
print("\n2. Dropbox wikipedia.pkl:")
try:
    with open('wikipedia.pkl', 'rb') as f:
        wiki_db = pickle.load(f)

    print(f"   Type: {type(wiki_db)}")

    if isinstance(wiki_db, dict):
        print(f"   Keys: {list(wiki_db.keys())[:10]}")  # Show first 10 keys
        for key in list(wiki_db.keys())[:5]:  # Inspect first 5
            val = wiki_db[key]
            print(f"   {key}: type={type(val)}")
            if isinstance(val, str):
                print(f"     Value preview: {val[:100]}...")
            elif hasattr(val, '__len__'):
                print(f"     Length: {len(val)}")
    elif isinstance(wiki_db, list):
        print(f"   Length: {len(wiki_db)}")
        if len(wiki_db) > 0:
            print(f"   First item type: {type(wiki_db[0])}")
            item = wiki_db[0]
            if isinstance(item, dict):
                print(f"   First item keys: {list(item.keys())}")
                for k in list(item.keys())[:3]:
                    print(f"     {k}: {str(item[k])[:100]}...")
            elif isinstance(item, str):
                print(f"   First item: {item[:200]}...")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "="*80)
