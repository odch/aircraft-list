#!/usr/bin/env python3
"""
Aircraft Registry Release Tool

Promotes staging version to production after manual review and approval.
"""
import json
import shutil
import sys
import subprocess
from datetime import datetime
from pathlib import Path

def get_current_version() -> str:
    """Get current version from VERSION file."""
    try:
        with open('VERSION', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return '1.0.0'

def parse_version(version: str) -> tuple:
    """Parse semantic version string into tuple of integers."""
    try:
        major, minor, patch = version.split('.')
        return int(major), int(minor), int(patch)
    except (ValueError, IndexError):
        return 1, 0, 0

def bump_version(current: str, bump_type: str) -> str:
    """Bump version based on type (patch/minor/major)."""
    major, minor, patch = parse_version(current)

    if bump_type == 'patch':
        patch += 1
    elif bump_type == 'minor':
        minor += 1
        patch = 0
    elif bump_type == 'major':
        major += 1
        minor = 0
        patch = 0
    else:
        raise ValueError(f"Invalid bump type: {bump_type}")

    return f"{major}.{minor}.{patch}"

def prompt_version_update() -> tuple:
    """Prompt user for version update and return (new_version, commit_message)."""
    current_version = get_current_version()

    print(f"\n🏷️ Current version: {current_version}")
    print("\n🔄 Version update options:")
    print("  1. 🟢 PATCH (1.0.0 → 1.0.1) - Data updates, new aircraft, corrections")
    print("  2. 🟡 MINOR (1.0.0 → 1.1.0) - New fields, backward-compatible changes")
    print("  3. 🔴 MAJOR (1.0.0 → 2.0.0) - Breaking changes, schema updates")
    print("  4. ⏭️  SKIP - Keep current version")
    print("  5. 📝 CUSTOM - Enter custom version")

    while True:
        choice = input("\n🤔 Choose version update (1-5): ").strip()

        if choice == '1':
            new_version = bump_version(current_version, 'patch')
            reason = input("📝 Brief description of changes: ").strip()
            commit_msg = f"🏷️ v{new_version} - {reason}" if reason else f"🏷️ v{new_version} - Data updates"
            return new_version, commit_msg

        elif choice == '2':
            new_version = bump_version(current_version, 'minor')
            reason = input("📝 Brief description of new features: ").strip()
            commit_msg = f"🏷️ v{new_version} - {reason}" if reason else f"🏷️ v{new_version} - New features"
            return new_version, commit_msg

        elif choice == '3':
            new_version = bump_version(current_version, 'major')
            reason = input("📝 Brief description of breaking changes: ").strip()
            commit_msg = f"🏷️ v{new_version} - BREAKING: {reason}" if reason else f"🏷️ v{new_version} - Breaking changes"
            return new_version, commit_msg

        elif choice == '4':
            return current_version, None

        elif choice == '5':
            custom_version = input("📝 Enter version (e.g., 1.2.3): ").strip()
            try:
                parse_version(custom_version)  # Validate format
                reason = input("📝 Brief description: ").strip()
                commit_msg = f"🏷️ v{custom_version} - {reason}" if reason else f"🏷️ v{custom_version} - Custom version"
                return custom_version, commit_msg
            except (ValueError, IndexError):
                print("❌ Invalid version format. Please use X.Y.Z format.")
                continue

        else:
            print("❌ Invalid choice. Please enter 1-5.")
            continue

def update_version_file(new_version: str) -> bool:
    """Update VERSION file with new version."""
    try:
        with open('VERSION', 'w') as f:
            f.write(new_version + '\n')
        print(f"✅ Updated VERSION file to {new_version}")
        return True
    except Exception as e:
        print(f"❌ Failed to update VERSION file: {e}")
        return False

def commit_version_change(version: str, commit_message: str) -> bool:
    """Commit version change to git."""
    try:
        # Check if git is available and we're in a repo
        subprocess.run(['git', 'status'], check=True, capture_output=True)

        # Add VERSION file and commit
        subprocess.run(['git', 'add', 'VERSION'], check=True)
        subprocess.run(['git', 'commit', '-m', commit_message], check=True)
        print(f"✅ Version change committed to git")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠️ Git commit failed or not in git repository")
        print("💡 Please manually commit the VERSION file change")
        return False

def backup_production(prod_file: str = 'aircraft.json') -> str:
    """Create backup of current production file."""
    if not Path(prod_file).exists():
        return ""

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f"backups/aircraft_backup_{timestamp}.json"

    # Create backups directory if it doesn't exist
    Path("backups").mkdir(exist_ok=True)

    shutil.copy2(prod_file, backup_file)
    return backup_file

def validate_staging(staging_file: str = 'aircraft-staging.json') -> bool:
    """Validate staging file before promotion."""
    try:
        with open(staging_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Basic validation
        required_fields = ['version', 'last_updated', 'total_count', 'aircraft']
        for field in required_fields:
            if field not in data:
                print(f"❌ Missing required field: {field}")
                return False

        if not isinstance(data['aircraft'], list):
            print("❌ Aircraft must be a list")
            return False

        if data['total_count'] != len(data['aircraft']):
            print(f"❌ Count mismatch: total_count={data['total_count']}, actual={len(data['aircraft'])}")
            return False

        # Sample aircraft validation
        if data['aircraft']:
            sample = data['aircraft'][0]
            required_aircraft_fields = ['registration']
            for field in required_aircraft_fields:
                if field not in sample:
                    print(f"❌ Missing aircraft field: {field}")
                    return False

        print(f"✅ Staging validation passed: {len(data['aircraft'])} aircraft")
        return True

    except FileNotFoundError:
        print(f"❌ Staging file not found: {staging_file}")
        return False
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in staging file: {e}")
        return False

def release_to_production(staging_file: str = 'aircraft-staging.json',
                         prod_file: str = 'aircraft.json',
                         force: bool = False) -> bool:
    """Release staging version to production."""
    print("🚀 Starting release process...")
    print(f"🚧 Staging: {staging_file}")
    print(f"📦 Production: {prod_file}")
    print("-" * 50)

    # Check if staging file exists
    if not Path(staging_file).exists():
        print(f"❌ Staging file not found: {staging_file}")
        print("💡 Run sync first to generate staging data")
        return False

    # Validate staging
    if not validate_staging(staging_file):
        print("❌ Staging validation failed")
        return False

    # Version management (if not forced)
    if not force:
        new_version, commit_message = prompt_version_update()

        if commit_message:  # User chose to update version
            if update_version_file(new_version):
                commit_version_change(new_version, commit_message)
            else:
                print("❌ Failed to update version - aborting release")
                return False

    # Interactive confirmation unless forced
    if not force:
        current_version = get_current_version()
        print(f"\n🏷️ Release version: {current_version}")
        print("⚠️  This will replace the current production registry.")
        print("📱 All downstream apps will use the new data on their next sync.")
        response = input("\n🤔 Proceed with release? (yes/no): ").strip().lower()

        if response not in ['yes', 'y']:
            print("❌ Release cancelled by user")
            return False

    try:
        # Create backup of current production
        backup_file = backup_production(prod_file)
        if backup_file:
            print(f"💾 Production backup created: {backup_file}")

        # Promote staging to production
        shutil.copy2(staging_file, prod_file)

        # Update production metadata
        with open(prod_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Add release timestamp
        data['released_at'] = datetime.now().strftime('%Y-%m-%dT%H:%M:%S%z')

        with open(prod_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print("✅ Release completed successfully!")
        print(f"📊 Released {data['total_count']} aircraft to production")
        print(f"🕐 Release timestamp: {data['released_at']}")

        # Show next steps
        print("\n💡 Next steps:")
        print("1. Commit changes to git repository")
        print("2. Monitor downstream apps for successful sync")
        print("3. Check logs for any issues")

        return True

    except Exception as e:
        print(f"❌ Release failed: {e}")
        return False

def rollback_production(backup_pattern: str = None) -> bool:
    """Rollback production to previous backup."""
    backups_dir = Path("backups")
    if not backups_dir.exists():
        print("❌ No backups directory found")
        return False

    # Find available backups
    backups = sorted(backups_dir.glob("aircraft_backup_*.json"), reverse=True)
    if not backups:
        print("❌ No backup files found")
        return False

    print("📋 Available backups:")
    for i, backup in enumerate(backups[:5]):  # Show last 5 backups
        print(f"  {i+1}. {backup.name}")

    try:
        choice = input("\n🤔 Select backup to restore (1-5, or 'cancel'): ").strip()
        if choice.lower() == 'cancel':
            print("❌ Rollback cancelled")
            return False

        backup_index = int(choice) - 1
        if backup_index < 0 or backup_index >= len(backups[:5]):
            print("❌ Invalid selection")
            return False

        selected_backup = backups[backup_index]

        # Confirm rollback
        print(f"⚠️  This will replace production with: {selected_backup.name}")
        confirm = input("🤔 Confirm rollback? (yes/no): ").strip().lower()

        if confirm not in ['yes', 'y']:
            print("❌ Rollback cancelled")
            return False

        # Perform rollback
        shutil.copy2(selected_backup, 'aircraft.json')
        print(f"✅ Rolled back to {selected_backup.name}")
        return True

    except (ValueError, IndexError):
        print("❌ Invalid input")
        return False
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_production()
    elif len(sys.argv) > 1 and sys.argv[1] == "--force":
        release_to_production(force=True)
    else:
        release_to_production()
