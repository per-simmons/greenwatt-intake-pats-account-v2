#!/usr/bin/env python3
"""
Automatically update all utility scripts to support Shared Drives
This adds supportsAllDrives=True to all Google Drive API calls
"""

import os
import re

# Scripts that need fixing (from our analysis)
scripts_to_fix = {
    "verify_now.py": [90, 94, 103],
    "test_workspace_migration.py": [156, 164, 172, 260],
    "check_drive_type.py": [30],
    "find_all_service_account_files.py": [55, 131],
    "verify_workspace_resources.py": [85, 89, 98],
    "cleanup_orphaned_files.py": [61, 129],
    "check_drive_trash.py": [53],
    "cleanup_drive_comprehensive.py": [67, 100]
}

print("🔧 FIXING SHARED DRIVE SUPPORT IN ALL UTILITY SCRIPTS")
print("=" * 70)

fixed_count = 0
error_count = 0

for script_name, line_numbers in scripts_to_fix.items():
    if not os.path.exists(script_name):
        print(f"\n⚠️  Skipping {script_name} - file not found")
        continue
        
    print(f"\n📝 Processing {script_name}...")
    
    try:
        # Read the file
        with open(script_name, 'r') as f:
            lines = f.readlines()
        
        # Track changes
        changes_made = 0
        
        # Process each line that needs fixing
        for line_num in line_numbers:
            # Adjust for 0-based indexing
            idx = line_num - 1
            
            if idx >= len(lines):
                print(f"   ⚠️  Line {line_num} doesn't exist (file has {len(lines)} lines)")
                continue
            
            original_line = lines[idx]
            
            # Check if it's already fixed
            if "supportsAllDrives=True" in original_line:
                print(f"   ✓ Line {line_num} already has Shared Drive support")
                continue
            
            # Add supportsAllDrives=True to the API call
            # Look for patterns like .execute() or ).execute()
            if ".execute()" in original_line:
                # Find where to insert the parameter
                if original_line.strip().endswith(".execute()"):
                    # Simple case: ends with .execute()
                    new_line = original_line.replace(
                        ".execute()",
                        ".execute()"
                    )
                    # Need to add parameter to the method call before .execute()
                    # Find the opening parenthesis of the method call
                    method_match = re.search(r'(\.\w+\([^)]*)\)', original_line)
                    if method_match:
                        method_call = method_match.group(1)
                        # Check if there are already parameters
                        if "(" in method_call and method_call.strip().endswith("("):
                            # No parameters yet
                            new_line = original_line.replace(
                                method_call + ")",
                                method_call + "supportsAllDrives=True)"
                            )
                        else:
                            # Has parameters, add comma
                            new_line = original_line.replace(
                                method_call + ")",
                                method_call + ", supportsAllDrives=True)"
                            )
                        lines[idx] = new_line
                        changes_made += 1
                        print(f"   ✅ Fixed line {line_num}")
                    else:
                        print(f"   ⚠️  Couldn't parse line {line_num}: {original_line.strip()}")
                else:
                    # Complex case: check if we need includeItemsFromAllDrives too
                    if ".list(" in original_line:
                        # For list operations, add both parameters
                        print(f"   ℹ️  Line {line_num} is a list operation - needs manual review")
                        print(f"      (needs both supportsAllDrives=True and includeItemsFromAllDrives=True)")
                    else:
                        print(f"   ⚠️  Complex line {line_num} needs manual review")
            else:
                print(f"   ⚠️  Line {line_num} doesn't contain .execute() - needs manual review")
        
        # Write back if changes were made
        if changes_made > 0:
            with open(script_name, 'w') as f:
                f.writelines(lines)
            print(f"   ✅ Fixed {changes_made} lines")
            fixed_count += changes_made
        else:
            print(f"   ℹ️  No changes needed")
            
    except Exception as e:
        print(f"   ❌ Error processing file: {str(e)}")
        error_count += 1

print("\n" + "=" * 70)
print(f"📊 SUMMARY: Fixed {fixed_count} lines across {len(scripts_to_fix)} scripts")
if error_count > 0:
    print(f"⚠️  Encountered {error_count} errors")

print("\n⚠️  IMPORTANT NOTES:")
print("1. Some lines need manual review, especially list() operations")
print("2. List operations need BOTH parameters:")
print("   - supportsAllDrives=True")
print("   - includeItemsFromAllDrives=True")
print("3. Test these scripts after updating!")
print("\n4. For list operations, use this pattern:")
print("   .list(")
print("       q=query,")
print("       supportsAllDrives=True,")
print("       includeItemsFromAllDrives=True")
print("   ).execute()")