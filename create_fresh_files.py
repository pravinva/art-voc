#!/usr/bin/env python3
"""Create files with new unique names to bypass Auto Loader checkpoint"""
import configparser
import json
from pathlib import Path
from databricks.sdk import WorkspaceClient
from databricks.sdk.service import files as dbfs
from io import BytesIO
from datetime import datetime, timedelta
import random
import uuid

# Read config
config = configparser.ConfigParser()
config.read(Path.home() / ".databrickscfg")

workspace_url = config['DEFAULT']['host'].rstrip('/')
token = config['DEFAULT']['token']

# Initialize client
w = WorkspaceClient(host=workspace_url, token=token)

# Volume path
volume_path = "/Volumes/art_voc/bronze/bronze_landing/incoming"

print("=" * 70)
print(" CREATING FILES WITH UNIQUE NAMES (BYPASS AUTO LOADER CHECKPOINT)")
print("=" * 70)

# First, delete all existing files
print("\n[1/3] Cleaning up existing files...")
try:
    files_list = list(w.files.list_directory_contents(volume_path))
    for file in files_list:
        if file.name.endswith('.json'):
            try:
                w.files.delete(f"{volume_path}/{file.name}")
            except:
                pass
    print(f"  ✓ Cleaned up old files")
except Exception as e:
    print(f"  ⚠ Error during cleanup: {e}")

# Sample data templates
channels = ["email", "chat"]  # Only use channels that Silver expects
source_systems = ["CRM", "Contact_Center", "Digital_Banking", "Branch_System"]

positive_texts = [
    "I'm very happy with your service and the support team was excellent",
    "Great experience with my retirement planning advisor",
    "The mobile app is easy to use and very helpful",
    "Thank you for the quick response to my query",
    "Excellent service and professional staff"
]

neutral_texts = [
    "I called to check my balance and got the information I needed",
    "Requested account statement via email",
    "Updated my contact details through the mobile app",
    "Asked about contribution rates and received standard information",
    "Routine inquiry about my retirement account"
]

negative_texts = [
    "I'm very disappointed with the long wait times on the phone",
    "Having issues accessing my account online for the past week",
    "Not satisfied with the response time to my email inquiry",
    "The fees seem too high compared to other providers",
    "Considering switching to another retirement fund due to poor service"
]

print("\n[2/3] Generating 50 files with unique timestamp-based names...")

files_created = 0
base_time = datetime(2025, 11, 1, 9, 0, 0)
unique_id = datetime.now().strftime("%Y%m%d%H%M%S")

for i in range(1, 51):
    # Distribute sentiment: 40% positive, 30% neutral, 30% negative
    if i <= 20:
        texts = positive_texts
    elif i <= 35:
        texts = neutral_texts
    else:
        texts = negative_texts

    # Generate interaction data - use EXACT same format as test file
    timestamp_dt = base_time + timedelta(hours=i*2, minutes=random.randint(0, 59))
    interaction_data = {
        "interaction_id": f"INT-{i:05d}",
        "member_id": f"MEM-{100000 + i}",
        "interaction_text": random.choice(texts),
        "channel": random.choice(channels),
        "timestamp": timestamp_dt.isoformat() + "Z",  # ISO format with Z suffix
        "source_system": random.choice(source_systems)
    }

    # Convert to single-line JSON (like test file)
    json_content = json.dumps(interaction_data)

    # Use timestamp-based unique filename
    file_path = f"{volume_path}/interaction_{unique_id}_{i:04d}.json"

    try:
        content_bytes = BytesIO(json_content.encode('utf-8'))
        w.files.upload(
            file_path=file_path,
            contents=content_bytes,
            overwrite=True
        )
        files_created += 1
        if i % 10 == 0:
            print(f"  ✓ Created {i} files...")
    except Exception as e:
        print(f"  ✗ Error creating file {i}: {e}")

print(f"\n  ✓ Successfully created {files_created}/50 files")
print(f"  Filename pattern: interaction_{unique_id}_XXXX.json")

print("\n[3/3] Verifying files in volume...")
try:
    files_list = list(w.files.list_directory_contents(volume_path))
    json_files = [f for f in files_list if f.name.endswith('.json')]
    print(f"  ✓ Total JSON files in volume: {len(json_files)}")
    print(f"\n  Sample filenames:")
    for f in list(json_files)[:3]:
        print(f"    - {f.name}")
except Exception as e:
    print(f"  ✗ Error listing files: {e}")

print("\n  Next: Drop tables and restart pipeline")
print("  Run: python3 drop_tables_and_rerun.py")

print("\n" + "=" * 70)
