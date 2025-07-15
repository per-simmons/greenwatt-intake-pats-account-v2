#!/usr/bin/env python3
"""Quick verification of Google resources"""

import os
import json

# New resource IDs to verify
print("\n🔍 Google Workspace Resource IDs to Verify:")
print("=" * 50)
print("📊 Main Sheet ID: 1sx7oULKh41KMPH47LolCF9lv7h7-kDwscAoZoVfhDw0")
print("👥 Agent Sheet ID: 1iwDPUL58BMtrHL0wQXgu9kcscriTNGYcqP8ATo8Oo-I")
print("📁 Parent Folder ID: 1upNlAEg1rf7NXjx7edfZN1xHRUxOCgCc")
print("📄 Templates Folder ID: 1zex9SAIqo_xn75w-5ZjbGIWMRiwGtwi0")

print("\n📋 Expected Template Files:")
print("=" * 50)
templates = [
    'Meadow-National-Grid-Commercial-UCB-Agreement.pdf',
    'Meadow-NYSEG-Commercial-UCB-Agreement.pdf',
    'Meadow-RGE-Commercial-UCB-Agreement.pdf',
    'Form-Subscription-Agreement-Mass Market UCB-Meadow-January 2023-002.pdf',
    'Solar-Simplified-National-Grid-Commercial-UCB-Agreement.pdf',
    'Solar-Simplified-NYSEG-Commercial-UCB-Agreement.pdf',
    'Solar-Simplified-RGE-Commercial-UCB-Agreement.pdf',
    'Form-Subscription-Agreement-Mass Market UCB-Solar-Simplified-January 2023-002.pdf'
]

for i, template in enumerate(templates, 1):
    print(f"{i}. {template}")

print("\n✅ Resource IDs have been documented.")
print("To verify access, the application will need to be updated with these new IDs.")

# Check if we have service account credentials
SERVICE_ACCOUNT_JSON = os.getenv('GOOGLE_SERVICE_ACCOUNT_JSON')
if SERVICE_ACCOUNT_JSON:
    print("\n✅ Service account credentials found in environment.")
else:
    if os.path.exists('upwork-greenwatt-drive-sheets-3be108764560.json'):
        print("\n✅ Service account credentials file found locally.")
    else:
        print("\n❌ No service account credentials found!")