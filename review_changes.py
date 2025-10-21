#!/usr/bin/env python3
"""
Aircraft Registry Change Review Script

This script compares the staging aircraft data with the production data
and provides a detailed report of what has changed.

Usage:
    python3 review_changes.py
"""

import json
import os
from typing import Dict, List, Set, Tuple
from datetime import datetime


class ChangeReviewer:
    """Handles comparison between staging and production aircraft data."""
    
    def __init__(self, 
                 staging_file: str = "aircraft-staging.json",
                 production_file: str = "aircraft.json"):
        self.staging_file = staging_file
        self.production_file = production_file

    def load_registry(self, filename: str) -> Dict:
        """Load aircraft registry from JSON file."""
        if not os.path.exists(filename):
            return {
                "version": "0.0.0",
                "last_updated": "1970-01-01T00:00:00+00:00",
                "total_count": 0,
                "aircraft": []
            }
        
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Error loading {filename}: {e}")
            return {"aircraft": [], "total_count": 0}

    def create_aircraft_lookup(self, registry: Dict) -> Dict[str, Dict]:
        """Create a lookup dictionary by registration code."""
        return {aircraft["registration"]: aircraft for aircraft in registry.get("aircraft", [])}

    def compare_aircraft(self, old_aircraft: Dict, new_aircraft: Dict) -> Dict:
        """Compare two aircraft entries and return differences."""
        changes = {}
        
        for field in ["icao_aircraft_type", "aircraft_type", "mtom"]:
            old_value = old_aircraft.get(field)
            new_value = new_aircraft.get(field)
            
            if old_value != new_value:
                changes[field] = {
                    "old": old_value,
                    "new": new_value
                }
        
        return changes

    def analyze_changes(self) -> Dict:
        """Analyze differences between staging and production data."""
        print("Loading aircraft registries...")
        
        staging = self.load_registry(self.staging_file)
        production = self.load_registry(self.production_file)
        
        staging_aircraft = self.create_aircraft_lookup(staging)
        production_aircraft = self.create_aircraft_lookup(production)
        
        staging_registrations = set(staging_aircraft.keys())
        production_registrations = set(production_aircraft.keys())
        
        # Find additions, removals, and modifications
        added = staging_registrations - production_registrations
        removed = production_registrations - staging_registrations
        common = staging_registrations & production_registrations
        
        modified = {}
        for registration in common:
            changes = self.compare_aircraft(
                production_aircraft[registration],
                staging_aircraft[registration]
            )
            if changes:
                modified[registration] = changes
        
        return {
            "staging_info": {
                "file": self.staging_file,
                "version": staging.get("version", "unknown"),
                "last_updated": staging.get("last_updated", "unknown"),
                "total_count": staging.get("total_count", 0)
            },
            "production_info": {
                "file": self.production_file,
                "version": production.get("version", "unknown"),  
                "last_updated": production.get("last_updated", "unknown"),
                "total_count": production.get("total_count", 0)
            },
            "added": {reg: staging_aircraft[reg] for reg in sorted(added)},
            "removed": {reg: production_aircraft[reg] for reg in sorted(removed)},
            "modified": modified
        }

    def print_summary(self, changes: Dict):
        """Print a summary of changes."""
        print("\n" + "="*70)
        print("AIRCRAFT REGISTRY CHANGE SUMMARY")
        print("="*70)
        
        # File information
        staging_info = changes["staging_info"]
        production_info = changes["production_info"]
        
        print(f"\nStaging:    {staging_info['file']}")
        print(f"            Version: {staging_info['version']}")
        print(f"            Updated: {staging_info['last_updated']}")
        print(f"            Count:   {staging_info['total_count']:,}")
        
        print(f"\nProduction: {production_info['file']}")
        print(f"            Version: {production_info['version']}")
        print(f"            Updated: {production_info['last_updated']}")
        print(f"            Count:   {production_info['total_count']:,}")
        
        # Change statistics
        added_count = len(changes["added"])
        removed_count = len(changes["removed"])
        modified_count = len(changes["modified"])
        total_changes = added_count + removed_count + modified_count
        
        print(f"\nCHANGE STATISTICS:")
        print(f"  Added aircraft:    {added_count:>6,}")
        print(f"  Removed aircraft:  {removed_count:>6,}")
        print(f"  Modified aircraft: {modified_count:>6,}")
        print(f"  Total changes:     {total_changes:>6,}")
        
        if total_changes == 0:
            print("\n✓ No changes detected - registries are identical")
            return
        
        # Detailed changes
        if changes["added"]:
            print(f"\n📍 ADDED AIRCRAFT ({len(changes['added'])})")
            print("-" * 70)
            for reg, aircraft in list(changes["added"].items())[:10]:  # Show first 10
                print(f"  {reg:<12} | {aircraft.get('icao_aircraft_type', 'N/A'):<8} | {aircraft.get('aircraft_type', 'N/A')}")
            
            if len(changes["added"]) > 10:
                print(f"  ... and {len(changes['added']) - 10} more")
        
        if changes["removed"]:
            print(f"\n🗑️  REMOVED AIRCRAFT ({len(changes['removed'])})")
            print("-" * 70)
            for reg, aircraft in list(changes["removed"].items())[:10]:  # Show first 10
                print(f"  {reg:<12} | {aircraft.get('icao_aircraft_type', 'N/A'):<8} | {aircraft.get('aircraft_type', 'N/A')}")
            
            if len(changes["removed"]) > 10:
                print(f"  ... and {len(changes['removed']) - 10} more")
        
        if changes["modified"]:
            print(f"\n✏️  MODIFIED AIRCRAFT ({len(changes['modified'])})")
            print("-" * 70)
            count = 0
            for reg, mods in changes["modified"].items():
                if count >= 10:  # Show first 10
                    break
                print(f"  {reg}:")
                for field, change in mods.items():
                    print(f"    {field}: {change['old']} → {change['new']}")
                count += 1
            
            if len(changes["modified"]) > 10:
                print(f"  ... and {len(changes['modified']) - 10} more")

    def review(self):
        """Main review method."""
        try:
            changes = self.analyze_changes()
            self.print_summary(changes)
            
            total_changes = len(changes["added"]) + len(changes["removed"]) + len(changes["modified"])
            
            if total_changes > 0:
                print(f"\n{'='*70}")
                print("NEXT STEPS:")
                print("  To approve changes: python3 release.py")
                print("  To reject changes:  Do nothing (changes remain in staging)")
                print("="*70)
            
            return total_changes > 0
            
        except Exception as e:
            print(f"Error during review: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Review aircraft registry changes')
    parser.add_argument(
        '--staging',
        default='aircraft-staging.json',
        help='Path to staging aircraft file'
    )
    parser.add_argument(
        '--production', 
        default='aircraft.json',
        help='Path to production aircraft file'
    )
    
    args = parser.parse_args()
    
    reviewer = ChangeReviewer(args.staging, args.production)
    has_changes = reviewer.review()
    
    exit(0 if has_changes else 1)


if __name__ == "__main__":
    main()
