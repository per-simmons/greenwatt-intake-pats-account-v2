# Google Workspace Migration Plan - January 15, 2025

## Migration Overview
Migrating from personal Gmail account (`greenwatt.intake@gmail.com`) to Google Workspace account (`intake@greenwattusa.com`) to resolve service account storage quota issues.

---

## 🚨 CURRENT STATUS (Last Updated: January 15, 2025 @ 4:45 PM)

### ✅ COMPLETED:
1. **Google Workspace Account Created**: `intake@greenwattusa.com`
2. **Shared Drive Created**: "GreenWatt Intake System" (in Google Workspace)
3. **Folders Created in Shared Drive**:
   - GreenWatt_Signed_Docs: `12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj`
   - GreenWatt_Templates: `1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS`
4. **Google Sheets Created**:
   - Main Intake Sheet: `1R1bZuDhToHg1bIQtZUWCXQHaCJq8jsXeuKuSFBHdhpw`
   - Agent Sheet: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I` (kept existing)
5. **Service Account Added to Shared Drive**: 
   - `greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com` as Content Manager
6. **Setup Script Run**: Successfully populated sheets with required structure
7. **Documentation Updated**: CLAUDE.md, setup scripts updated with new IDs
8. **Code Fixed**: GoogleDriveService updated to support Shared Drives (added `supportsAllDrives=True`)

### ❌ PENDING:
1. **Push Code Changes to GitHub** - Need to commit and push the GoogleDriveService fix
2. **Render Deployment** - Will auto-deploy once changes are pushed
3. **Test Form Submission** - Verify everything works with new Shared Drive resources

### 🔥 CURRENT ISSUE:
- **Error**: "File not found: 12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj"
- **Root Cause**: Service accounts require special API parameters to access Shared Drives
- **Fix Applied**: Updated `services/google_drive_service.py` to add `supportsAllDrives=True` to all API calls
- **Status**: Fix ready but needs to be deployed

---

## What You Need To Do On Your End

### 1. **Create New Google Resources** (Under intake@greenwattusa.com) ✅ DONE

#### A. Create New Google Sheets (Empty) ✅ DONE
1. **Main Intake Log Sheet** ✅
   - Created and structured with setup script
   - ID: `1R1bZuDhToHg1bIQtZUWCXQHaCJq8jsXeuKuSFBHdhpw`

2. **Agent ID Sheet** ✅
   - Using existing sheet
   - ID: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I`

#### B. Create Shared Drive and Folders ✅ DONE
1. **CRITICAL: Create a Shared Drive (Team Drive)** ✅
   - Created "GreenWatt Intake System" Shared Drive
   - This is NOT the same as a regular shared folder!
   
2. **Create folders INSIDE the Shared Drive**: ✅
   - **GreenWatt_Signed_Docs** ID: `12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj`
   - **GreenWatt_Templates** ID: `1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS`
   
3. **Add Service Account to Shared Drive**: ✅
   - Added greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com
   - Role: Content Manager (confirmed in screenshot)

### 2. **Service Account Configuration** ✅ DONE

#### Option A: Use Same Service Account (Recommended) ✅ CHOSEN
- Using: `greenwatt-intake-service@greenwatt-intake-form.iam.gserviceaccount.com`
- All resources shared with proper permissions

### 3. **Grant Permissions** ✅ DONE
For EACH new resource, shared with service account:
- ✅ New Main Intake Sheet - Editor access
- ✅ Agent ID Sheet - Editor access (existing)
- ✅ Shared Drive - Content Manager role
- ✅ All folders inherit Shared Drive permissions

### 4. **Collect New Resource IDs** ✅ DONE
- New Main Sheet ID: `1R1bZuDhToHg1bIQtZUWCXQHaCJq8jsXeuKuSFBHdhpw`
- New Agent Sheet ID: `1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I` (keeping existing)
- New Parent Folder ID: `12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj` (Shared Drive folder)
- New Templates Folder ID: `1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS` (Shared Drive folder)

---

## What I Did On My End

### 1. **Updated Environment Variables in Render.com** ✅ DONE
```bash
GOOGLE_SHEETS_ID="1R1bZuDhToHg1bIQtZUWCXQHaCJq8jsXeuKuSFBHdhpw"
GOOGLE_AGENT_SHEETS_ID="1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I"
GOOGLE_DRIVE_PARENT_FOLDER_ID="12lCtTAUVxgLuwjW9X81P4-hFr1FC3uJj"
GOOGLE_DRIVE_TEMPLATES_FOLDER_ID="1-XPW8PVhXAPUsn2eIsBA_4p7ckm150lS"
```

### 2. **Update Code References** ✅ DONE
- Updated documentation with new IDs
- Fixed GoogleDriveService to support Shared Drives
- Added `supportsAllDrives=True` to all Drive API calls

### 3. **Test Everything** ⏳ PENDING (waiting for deployment)
- Form submission flow
- OCR processing
- PDF generation
- Google Sheets logging
- Email notifications

---

## Important Discovery: Shared Drives Required!

### 🚨 **Critical Learning**

1. **Service Account Limitation**
   - Service accounts have 0-byte quota in ALL regular folders (even in Workspace)
   - Service accounts can ONLY create files in Shared Drives (Team Drives)
   - Regular "shared folders" are NOT the same as Shared Drives

2. **API Requirements for Shared Drives**
   - All Drive API calls must include `supportsAllDrives=True`
   - List operations need `includeItemsFromAllDrives=True`
   - Without these parameters, you get "File not found" errors

3. **Current Fix Status**
   - Code has been updated in `services/google_drive_service.py`
   - Changes need to be pushed to GitHub
   - Render will auto-deploy once pushed

---

## Next Steps (For New Agent)

### 1. **Deploy the Fix** 🚨 URGENT
```bash
# In the GreenWatt_Clean_Repo directory:
git add services/google_drive_service.py CLAUDE.md Google-Workspace-Migration-7-15-25.md setup_workspace_resources_auto.py
git commit -m "Fix Google Drive Shared Drive access - add supportsAllDrives parameter"
git push origin main
```

### 2. **Monitor Deployment**
- Watch https://dashboard.render.com/web/srv-d18vfefdiees73abnkv0
- Service has auto-deploy enabled, will deploy on push

### 3. **Test After Deployment**
- Run test form submission
- Verify files are created in Shared Drive
- Check Google Sheets for new entries

### 4. **If Issues Persist**
- Verify service account is Content Manager (not just Viewer)
- Check that folders are actually in Shared Drive (has different icon)
- Ensure all template files are uploaded to Templates folder

---

## Key Files Modified

1. **services/google_drive_service.py** - Added Shared Drive support
2. **CLAUDE.md** - Updated with new IDs and Shared Drive requirement
3. **Google-Workspace-Migration-7-15-25.md** - This file, with current status
4. **setup_workspace_resources_auto.py** - Updated with new IDs

---

## Summary for New Agent

**The migration is 90% complete!** The main remaining task is:

1. **Push the code changes to GitHub** to trigger deployment
2. **Test the system** once deployed

The critical fix was discovering that service accounts need:
- Shared Drives (not regular folders)
- Special API parameters (`supportsAllDrives=True`)

All resources are created and configured correctly. Just need to deploy the code fix!