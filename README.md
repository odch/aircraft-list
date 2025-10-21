# Aircraft Registry

A comprehensive registry of all aircraft registered in Switzerland. This serves as a single source of truth for multiple projects requiring aircraft data.

## Overview

This registry contains essential information for each aircraft:
- **Registration**: Swiss aircraft registration code (e.g., HB-1234)
- **ICAO Aircraft Type**: ICAO aircraft type designator
- **Aircraft Type**: Aircraft type description 
- **MTOM**: Maximum Take-Off Mass in kg

## Data Format

The registry uses JSON format for maximum compatibility and ease of integration:

```json
{
  "version": "1.0.0",
  "last_updated": "2025-10-21T17:31:59+02:00",
  "total_count": 4,
  "aircraft": [
    {
      "registration": "HB-1000",
      "icao_aircraft_type": "GLID",
      "aircraft_type": "Glider",
      "mtom": 340
    }
  ]
}
```

## Files

- `aircraft.json` - Main registry file containing all aircraft data
- `schema.json` - JSON Schema for data validation
- `README.md` - This documentation file

## Usage

### For Nightly Database Imports

```bash
curl -s https://raw.githubusercontent.com/odch/aircraft-list/main/aircraft.json | jq '.aircraft'
```

### Data Validation

Validate your aircraft data against our schema:

```bash
pip install jsonschema
python3 -c "import json, jsonschema; jsonschema.validate(json.load(open('aircraft.json')), json.load(open('schema.json')))"
```

## Data Sources

### Primary Data Sources

**Swiss Federal Office of Civil Aviation (BAZL)**
- License: Public data
- Usage: Aircraft registrations, types, and technical specifications
- API: `https://app02.bazl.admin.ch/web/bazl-backend/lfr/csv`

### Data Processing

- Aircraft data is sourced from the BAZL aircraft registry
- Only active aircraft (Registered, Reserved, Reservation Expired, Registration in Progress) are included
- Data is filtered to include only essential fields: Registration, ICAO Type, Aircraft Type, and MTOM
- Custom overrides can be applied for additional aircraft or corrections

## Maintenance

### Automated Workflow

This registry uses a GitOps workflow with automated data synchronization and manual review/release process.

#### 🤖 Automated Sync Process

Every Monday at 6:00 AM UTC (or manually triggered), GitHub Actions automatically:

1. Downloads fresh data from BAZL API
2. Processes data using `sync_aircraft.py` 
3. Creates `aircraft-staging.json` with latest information
4. Compares staging vs production data
5. If changes detected:
   - Commits staging file to repository
   - Generates detailed change summary
   - Creates GitHub Issue for manual review

#### 👤 Review & Release Process

When automation detects changes, you receive a GitHub Issue with:
- Detailed change summary and statistics
- Instructions for next steps
- Automatic labels for easy tracking

**🤖 Automated Release (Recommended)**

Simply comment on the GitHub Issue with one of these commands:

**To approve and release:**
- `!release patch` - For data updates, new aircraft, corrections
- `!release minor` - For new fields, backward-compatible changes
- `!release major` - For breaking changes, schema updates
- `!release patch Fixed aircraft data` - Add optional description

**To reject:**
- `!reject` or `!reject Reason for rejection`

What happens automatically:
1. ✅ Validates staging data
2. ✅ Creates production backup
3. ✅ Bumps version (patch/minor/major)
4. ✅ Releases to production
5. ✅ Commits & creates Git tag
6. ✅ Closes issue with summary

**🖥️ Manual Release (Legacy)**

For local development or when automation fails:
- **Review:** Run `python3 review_changes.py` to see detailed changes
- **Approve:** Run `python3 release.py` to promote staging → production
- **Reject:** Do nothing, changes remain in staging only

#### 📁 Key Files

- `aircraft.json` - 🟢 **PRODUCTION** (what applications consume)
- `aircraft-staging.json` - 🟡 **STAGING** (automated updates)
- `sync_aircraft.py` - Downloads and processes source data
- `review_changes.py` - Shows differences between staging and production
- `release.py` - Promotes staging to production with backups

#### 🔒 Safety Features

- **Production never touched by automation** - Always requires manual approval
- **Automatic backups** created before each release
- **Rollback capability** if issues arise
- **Data validation** before promotion using JSON schema
- **Clear audit trail** through Git commits and Issues

#### ⚙️ GitHub Workflows

The project includes two main workflows:

- **Sync Workflow** (`.github/workflows/sync.yml`) - Daily automated data sync (6:00 AM UTC)
- **Release Workflow** (`.github/workflows/release.yml`) - Issue-based release management with `!release` and `!reject` commands

### Custom Overrides

You can add custom aircraft or override existing data using `aircraft-overrides.json`:

```json
{
  "HB-CUST": {
    "icao_aircraft_type": "B738",
    "aircraft_type": "Aeroplane",
    "mtom": 79000
  }
}
```

To use custom overrides:

```bash
python3 sync_aircraft.py --overrides aircraft-overrides.json
```

### Manual Maintenance

#### Adding Individual Aircraft (Not Recommended)

For emergency additions only. Prefer the automated sync process for data quality.

1. Ensure the aircraft has a valid registration code
2. Add entry to the `aircraft` array in `aircraft.json`
3. Update `total_count` field  
4. Update `last_updated` timestamp
5. Validate against schema
6. Commit changes

### Semantic Versioning

- **Patch (x.x.X)**: Data updates, corrections, new aircraft
- **Minor (x.X.x)**: New fields, backward-compatible schema changes
- **Major (X.x.x)**: Breaking changes, incompatible schema updates

## Setup

### Requirements

```bash
pip install -r requirements.txt
```

### Initial Sync

```bash
# Sync data from BAZL
python3 sync_aircraft.py

# Review what changed
python3 review_changes.py

# Release to production  
python3 release.py
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with schema validation
5. Submit a pull request

## License

### Registry Software & Code

This project (excluding data) is licensed under the MIT License.

### Data Licensing & Attribution

The aircraft data is sourced from:
- **Swiss Federal Office of Civil Aviation (BAZL)**: Public data

### Usage Compliance

When using this registry:
- Verify data freshness for critical applications
- Understand that aircraft registration data can change frequently
- Consider the data processing pipeline when interpreting results

### Disclaimer

This registry is provided "as is" without warranty. While we strive for accuracy, always verify critical information with official sources.

## Support

- **Issues**: Report bugs and request features via GitHub Issues
- **Documentation**: This README and inline code documentation
- **Community**: Contribute via Pull Requests

---

## About

**Aircraft Registry** - Comprehensive Swiss aircraft database

- **License**: MIT (code), Public Domain (data attribution to BAZL)
- **Maintainer**: ODCH (Online Drone Control Hub)
- **Data Source**: Swiss Federal Office of Civil Aviation (BAZL)
