#!/usr/bin/env python3
"""
Aircraft Registry Synchronization Script

This script fetches aircraft data from the Swiss BAZL (Federal Office of Civil Aviation) 
and processes it into our aircraft registry format.

Usage:
    python3 sync_aircraft.py
"""

import json
import csv
import io
import requests
from datetime import datetime, timezone
from typing import Dict, List, Optional
import jsonschema
import os

class AircraftSyncer:
    """Handles synchronization of aircraft data from BAZL."""
    
    BAZL_ENDPOINT = "https://app02.bazl.admin.ch/web/bazl-backend/lfr/csv"
    QUERY_PAYLOAD = {
        "sort_list": "registration",
        "language": "en",
        "queryProperties": {
            "aircraftStatus": [
                "Registered",
                "Reserved", 
                "Reservation Expired",
                "Registration in Progress"
            ]
        }
    }
    
    # CSV column mappings (note the spaces in column names)
    COLUMN_MAPPING = {
        "registration": " Registration",
        "icao_aircraft_type": " ICAO Aircraft Type", 
        "aircraft_type": " Aircraft Type",
        "mtom": " MTOM"
    }

    def __init__(self, overrides_file: Optional[str] = None):
        """Initialize the syncer with optional overrides file."""
        self.overrides_file = overrides_file
        self.overrides = self._load_overrides() if overrides_file else {}
        
    def _load_overrides(self) -> Dict:
        """Load custom aircraft overrides from file."""
        if not os.path.exists(self.overrides_file):
            return {}
            
        try:
            with open(self.overrides_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"Warning: Could not load overrides file {self.overrides_file}: {e}")
            return {}

    def fetch_aircraft_data(self) -> str:
        """Fetch raw CSV data from BAZL endpoint."""
        print("Fetching aircraft data from BAZL...")
        
        try:
            response = requests.post(
                self.BAZL_ENDPOINT,
                json=self.QUERY_PAYLOAD,
                headers={'Content-Type': 'application/json'},
                timeout=30
            )
            response.raise_for_status()
            
            # Handle UTF-16 encoding (check for BOM)
            content = response.content
            if content.startswith(b'\xff\xfe') or content.startswith(b'\xfe\xff'):
                # UTF-16 with BOM
                csv_text = content.decode('utf-16')
            elif content.startswith(b'\xff\xfe\x00\x00') or content.startswith(b'\x00\x00\xfe\xff'):
                # UTF-32 with BOM
                csv_text = content.decode('utf-32')
            else:
                # Default to UTF-8
                csv_text = content.decode('utf-8')
            
            return csv_text
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch data from BAZL: {e}")
        except UnicodeDecodeError as e:
            raise Exception(f"Failed to decode CSV data: {e}")

    def parse_csv_data(self, csv_content: str) -> List[Dict]:
        """Parse CSV content and extract relevant aircraft information."""
        print("Parsing CSV data...")
        
        aircraft_list = []
        csv_reader = csv.DictReader(
            io.StringIO(csv_content), 
            delimiter=';'
        )
        
        row_count = 0
        for row in csv_reader:
            row_count += 1
            try:
                # Extract relevant fields
                registration = row.get(self.COLUMN_MAPPING["registration"], "").strip()
                icao_type = row.get(self.COLUMN_MAPPING["icao_aircraft_type"], "").strip()
                aircraft_type = row.get(self.COLUMN_MAPPING["aircraft_type"], "").strip()
                mtom_str = row.get(self.COLUMN_MAPPING["mtom"], "").strip()
                
                # Skip rows with missing essential data
                if not registration or not icao_type or not aircraft_type:
                    continue
                
                # Parse MTOM as integer, handle empty/invalid values
                mtom = None
                if mtom_str:
                    try:
                        mtom = int(mtom_str)
                    except ValueError:
                        pass  # Keep as None if not a valid integer
                
                aircraft_data = {
                    "registration": registration,
                    "icao_aircraft_type": icao_type,
                    "aircraft_type": aircraft_type,
                    "mtom": mtom
                }
                
                aircraft_list.append(aircraft_data)
                
            except Exception as e:
                print(f"Warning: Error processing row for {row.get(self.COLUMN_MAPPING['registration'], 'unknown')}: {e}")
                continue
        
        return aircraft_list

    def apply_overrides(self, aircraft_list: List[Dict]) -> List[Dict]:
        """Apply custom overrides and add additional aircraft."""
        if not self.overrides:
            return aircraft_list
            
        print(f"Applying {len(self.overrides)} custom overrides...")
        
        # Create a lookup dict by registration for efficient updates
        aircraft_dict = {aircraft["registration"]: aircraft for aircraft in aircraft_list}
        
        # Apply overrides (skip comment fields that start with _)
        for reg, override_data in self.overrides.items():
            if reg.startswith('_'):
                continue  # Skip comment fields
                
            if reg in aircraft_dict:
                # Update existing aircraft
                aircraft_dict[reg].update(override_data)
                print(f"Updated aircraft {reg} with custom data")
            else:
                # Add new aircraft
                new_aircraft = {"registration": reg}
                new_aircraft.update(override_data)
                aircraft_dict[reg] = new_aircraft
                print(f"Added new aircraft {reg} from overrides")
        
        return list(aircraft_dict.values())

    def create_registry(self, aircraft_list: List[Dict]) -> Dict:
        """Create the final registry structure."""
        # Sort by registration
        aircraft_list.sort(key=lambda x: x["registration"])
        
        registry = {
            "version": "1.0.0",
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_count": len(aircraft_list),
            "aircraft": aircraft_list
        }
        
        return registry

    def validate_registry(self, registry: Dict) -> bool:
        """Validate registry against schema."""
        print("Validating registry against schema...")
        
        try:
            with open('schema.json', 'r', encoding='utf-8') as f:
                schema = json.load(f)
            
            jsonschema.validate(registry, schema)
            print("✓ Registry validation successful")
            return True
            
        except jsonschema.ValidationError as e:
            print(f"✗ Registry validation failed: {e}")
            return False
        except FileNotFoundError:
            print("Warning: schema.json not found, skipping validation")
            return True
        except Exception as e:
            print(f"Warning: Error during validation: {e}")
            return True

    def save_registry(self, registry: Dict, filename: str = "aircraft-staging.json"):
        """Save registry to file."""
        print(f"Saving registry to {filename}...")
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(registry, f, indent=2, ensure_ascii=False)
        
        print(f"✓ Saved {registry['total_count']} aircraft to {filename}")

    def sync(self) -> bool:
        """Main synchronization method."""
        try:
            # Fetch data
            csv_content = self.fetch_aircraft_data()
            
            # Parse CSV
            aircraft_list = self.parse_csv_data(csv_content)

            if len(aircraft_list) == 0:
                print(f"CSV download contained 0 aircraft, which cannot be correct. Aborting...")
                exit(1)
            else:
                print(f"Parsed {len(aircraft_list)} aircraft from CSV")
            
            # Apply overrides
            aircraft_list = self.apply_overrides(aircraft_list)
            
            # Create registry
            registry = self.create_registry(aircraft_list)
            
            # Validate
            if not self.validate_registry(registry):
                print("⚠ Continuing despite validation errors...")
            
            # Save to staging
            self.save_registry(registry)
            
            print(f"✓ Synchronization completed successfully!")
            print(f"  Total aircraft: {registry['total_count']}")
            print(f"  Last updated: {registry['last_updated']}")
            
            return True
            
        except Exception as e:
            print(f"✗ Synchronization failed: {e}")
            return False


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Sync aircraft data from BAZL')
    parser.add_argument(
        '--overrides', 
        help='Path to JSON file containing aircraft overrides',
        default='aircraft-overrides.json'
    )
    
    args = parser.parse_args()
    
    # Create syncer
    syncer = AircraftSyncer(overrides_file=args.overrides)
    
    # Run sync
    success = syncer.sync()
    exit(0 if success else 1)


if __name__ == "__main__":
    main()
