#!/usr/bin/env python3
"""
Aircraft Registry Validation Script

Validates aircraft registry JSON files against the defined schema.
Used by GitHub workflows for automated validation.

Usage:
    python3 validate.py [filename]
    
If no filename provided, validates 'aircraft.json' by default.
"""

import json
import sys
import os
import jsonschema
from pathlib import Path

def validate_aircraft_registry(data_file='aircraft.json', schema_file='schema.json'):
    """
    Validate aircraft registry data against JSON schema.
    
    Args:
        data_file: Path to the aircraft data file
        schema_file: Path to the JSON schema file
    
    Returns:
        bool: True if validation passes, False otherwise
    """
    
    # Check if data file exists
    if not os.path.exists(data_file):
        print(f"❌ Data file not found: {data_file}")
        return False
    
    # Check if schema file exists
    if not os.path.exists(schema_file):
        print(f"⚠️ Schema file not found: {schema_file}")
        print("Skipping schema validation (file not required for basic validation)")
        return validate_basic_structure(data_file)
    
    try:
        # Load data
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Load schema
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema = json.load(f)
        
        # Validate against schema
        jsonschema.validate(data, schema)
        
        # Additional custom validations
        if not validate_custom_rules(data):
            return False
        
        print(f"✅ {data_file} is valid")
        print(f"   - Aircraft count: {data.get('total_count', 0):,}")
        print(f"   - Version: {data.get('version', 'unknown')}")
        print(f"   - Last updated: {data.get('last_updated', 'unknown')}")
        
        return True
        
    except jsonschema.ValidationError as e:
        print(f"❌ Schema validation failed for {data_file}:")
        print(f"   Error: {e.message}")
        if e.absolute_path:
            print(f"   Path: {' -> '.join(map(str, e.absolute_path))}")
        return False
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in {data_file}:")
        print(f"   {e}")
        return False
        
    except Exception as e:
        print(f"❌ Validation error for {data_file}:")
        print(f"   {e}")
        return False

def validate_basic_structure(data_file):
    """
    Perform basic structural validation without schema.
    
    Args:
        data_file: Path to the aircraft data file
    
    Returns:
        bool: True if basic structure is valid
    """
    try:
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Check required fields
        required_fields = ['version', 'last_updated', 'total_count', 'aircraft']
        for field in required_fields:
            if field not in data:
                print(f"❌ Missing required field: {field}")
                return False
        
        # Check data types
        if not isinstance(data['aircraft'], list):
            print("❌ 'aircraft' field must be a list")
            return False
        
        if not isinstance(data['total_count'], int):
            print("❌ 'total_count' field must be an integer")
            return False
        
        # Check count consistency
        actual_count = len(data['aircraft'])
        declared_count = data['total_count']
        
        if actual_count != declared_count:
            print(f"❌ Count mismatch: declared {declared_count}, actual {actual_count}")
            return False
        
        print(f"✅ {data_file} has valid basic structure")
        return True
        
    except Exception as e:
        print(f"❌ Basic validation failed for {data_file}: {e}")
        return False

def validate_custom_rules(data):
    """
    Apply custom validation rules specific to aircraft registry.
    
    Args:
        data: Parsed JSON data
    
    Returns:
        bool: True if custom rules pass
    """
    aircraft_list = data.get('aircraft', [])
    
    # Check for duplicate registrations
    registrations = []
    for i, aircraft in enumerate(aircraft_list):
        if not isinstance(aircraft, dict):
            print(f"❌ Aircraft at index {i} is not an object")
            return False
        
        registration = aircraft.get('registration')
        if registration:
            if registration in registrations:
                print(f"❌ Duplicate registration found: {registration}")
                return False
            registrations.append(registration)
    
    # Check for required fields in aircraft objects
    required_aircraft_fields = ['registration']
    for i, aircraft in enumerate(aircraft_list):
        for field in required_aircraft_fields:
            if field not in aircraft or not aircraft[field]:
                print(f"❌ Aircraft at index {i} missing required field: {field}")
                return False
    
    return True

def main():
    """Main entry point."""
    
    # Determine which file to validate
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    else:
        data_file = 'aircraft.json'
    
    print(f"🔍 Validating {data_file}...")
    
    # Validate the file
    success = validate_aircraft_registry(data_file)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
