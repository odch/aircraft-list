#!/usr/bin/env python3
"""
Aircraft Registry Auto-Release Check

Decides whether the staged changes are small enough to be released
automatically (after a grace period, unless someone objects) or whether
they need a manual review.

Usage:
    python3 check_auto_release.py [--max-changes N] [--max-removals N]

When run inside GitHub Actions, the decision is also appended to $GITHUB_ENV
as AUTO_RELEASE (true/false) and AUTO_RELEASE_REASON.
"""
import argparse
import json
import os
import sys
from typing import Dict


def load_aircraft(filename: str) -> Dict[str, Dict]:
    """Load a registry file and return its aircraft keyed by registration."""
    with open(filename, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return {a['registration']: a for a in data['aircraft']}


def decide(prod: Dict[str, Dict], staging: Dict[str, Dict],
           max_changes: int, max_removals: int) -> Dict:
    """Count the changes between production and staging and decide."""
    added = len(staging.keys() - prod.keys())
    removed = len(prod.keys() - staging.keys())
    modified = sum(1 for reg in prod.keys() & staging.keys() if prod[reg] != staging[reg])
    total = added + removed + modified

    if not prod:
        eligible, reason = False, 'no production data to compare against'
    elif total > max_changes:
        eligible, reason = False, f'{total} changes exceed the auto-release limit of {max_changes}'
    elif removed > max_removals:
        eligible, reason = False, f'{removed} removals exceed the auto-release limit of {max_removals}'
    else:
        eligible, reason = True, (f'{total} changes incl. {removed} removals; '
                                  f'limits are {max_changes} changes and {max_removals} removals')

    return {
        'added': added,
        'removed': removed,
        'modified': modified,
        'total': total,
        'eligible': eligible,
        'reason': reason,
    }


def main():
    parser = argparse.ArgumentParser(description='Decide whether staged aircraft changes can be auto-released')
    parser.add_argument('--production', default='aircraft.json')
    parser.add_argument('--staging', default='aircraft-staging.json')
    parser.add_argument('--max-changes', type=int,
                        default=int(os.environ.get('AUTO_RELEASE_MAX_CHANGES', 50)))
    parser.add_argument('--max-removals', type=int,
                        default=int(os.environ.get('AUTO_RELEASE_MAX_REMOVALS', 25)))
    args = parser.parse_args()

    try:
        staging = load_aircraft(args.staging)
    except (OSError, ValueError, KeyError) as e:
        print(f"❌ Could not read staging data from {args.staging}: {e}")
        sys.exit(1)

    # A missing or unreadable production file never qualifies for auto-release
    try:
        prod = load_aircraft(args.production)
    except (OSError, ValueError, KeyError):
        prod = {}

    result = decide(prod, staging, args.max_changes, args.max_removals)

    print(f"📊 Added: {result['added']}, removed: {result['removed']}, "
          f"modified: {result['modified']}, total: {result['total']}")
    if result['eligible']:
        print(f"✅ Auto-release: {result['reason']}")
    else:
        print(f"✋ Manual review required: {result['reason']}")

    github_env = os.environ.get('GITHUB_ENV')
    if github_env:
        with open(github_env, 'a', encoding='utf-8') as f:
            f.write(f"AUTO_RELEASE={'true' if result['eligible'] else 'false'}\n")
            f.write(f"AUTO_RELEASE_REASON={result['reason']}\n")


if __name__ == "__main__":
    main()
