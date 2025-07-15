# Google Workspace Resource Verification Report

## 📋 Resource ID Update Summary

### Old IDs (Previous Deployment)
- **Main Sheet ID**: `11hjZE80n0zE9qfRtlTyg4n3QMm1p1WIkqp9Be8Zgi6o`
- **Agent Sheet ID**: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I` (same as new)
- **Parent Folder ID**: `1i1SAHRnrgA-eWKgaZaShwF3zzOqewO3W`
- **Templates Folder ID**: `1YPUFTwKP5uzOMTKp1OZcWuwCeZA2nFqE`

### New IDs (Client's Workspace)
- **Main Sheet ID**: `1sx7oULKh41KMPH47LolCF9lv7h7-kDwscAoZoVfhDw0`
- **Agent Sheet ID**: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I` (unchanged)
- **Parent Folder ID**: `1upNlAEg1rf7NXjx7edfZN1xHRUxOCgCc`
- **Templates Folder ID**: `1zex9SAIqo_xn75w-5ZjbGIWMRiwGtwi0`

## 📄 Expected Agreement Templates

Based on the Developer_Mapping configuration, the following 8 templates should be in the Templates folder:

### Meadow Energy Templates (4 files)
1. `Meadow-National-Grid-Commercial-UCB-Agreement.pdf`
2. `Meadow-NYSEG-Commercial-UCB-Agreement.pdf`
3. `Meadow-RGE-Commercial-UCB-Agreement.pdf`
4. `Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf` (Residential)

### Solar Simplified Templates (4 files)
5. `Solar-Simplified-National-Grid-Commercial-UCB-Agreement.pdf`
6. `Solar-Simplified-NYSEG-Commercial-UCB-Agreement.pdf`
7. `Solar-Simplified-RGE-Commercial-UCB-Agreement.pdf`
8. `Form-Subscription-Agreement-Mass Market UCB-Solar-Simplified-January 2023-002.pdf` (Residential)

## 🔧 Files That Need Updating

### 1. **app.py** (lines 56, 60-62)
```python
# Current (old IDs)
drive_service = GoogleDriveService(parent_folder_id=os.getenv('GOOGLE_DRIVE_PARENT_FOLDER_ID'))
sheets_service = GoogleSheetsService(
    spreadsheet_id=os.getenv('GOOGLE_SHEETS_ID'),
    agent_spreadsheet_id=os.getenv('GOOGLE_AGENT_SHEETS_ID'),
    dynamic_spreadsheet_id=os.getenv('DYNAMIC_GOOGLE_SHEETS_ID')
)
```

### 2. **greenwatt_render_deployment_guide.md** (lines 27-30)
```bash
# Needs updating to:
GOOGLE_SHEETS_ID=1sx7oULKh41KMPH47LolCF9lv7h7-kDwscAoZoVfhDw0
GOOGLE_AGENT_SHEETS_ID=1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I
GOOGLE_DRIVE_PARENT_FOLDER_ID=1upNlAEg1rf7NXjx7edfZN1xHRUxOCgCc
GOOGLE_DRIVE_TEMPLATES_FOLDER_ID=1zex9SAIqo_xn75w-5ZjbGIWMRiwGtwi0
```

### 3. **README.md** (lines 40-43)
```bash
# Needs updating to match new IDs
```

### 4. **CLAUDE.md** (lines 135-138)
```bash
# Update example environment variables with actual IDs
```

## 🚀 Action Items

1. **Verify Template Files**: Need to confirm all 8 expected templates are present in the new Templates folder
2. **Update Environment Variables**: Update all references to the old IDs in documentation
3. **Test Access**: Run the verification script to confirm service account has proper access
4. **Update .env.example**: Make sure example file has correct format (not actual IDs)

## 🔐 Service Account Access

The service account email `greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com` needs:
- **Editor** access to both Google Sheets
- **Editor** access to the Drive folders
- Already confirmed by client that access has been granted

## 📝 Notes

- The Agent Sheet ID remains the same, which suggests it may be shared between environments
- All other resources have new IDs in the client's workspace
- The verification script (`verify_workspace_resources.py`) is ready to run once environment is properly configured