#!/usr/bin/env python3
"""Quick fix: update Tobiloba's birthday from May 20 to May 28 on Google Calendar."""

import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "config", "google_token.json")

creds = Credentials.from_authorized_user_file(TOKEN_FILE)
service = build("calendar", "v3", credentials=creds)

# Find the birthday event
events = service.events().list(
    calendarId="primary",
    q="Happy Birthday Tobiloba",
    maxResults=5,
).execute()

for event in events.get("items", []):
    print(f"Found: {event['summary']} on {event['start'].get('date', 'N/A')}")
    # Update to May 28
    event["start"]["date"] = "2026-05-28"
    event["end"]["date"] = "2026-05-28"
    service.events().update(calendarId="primary", eventId=event["id"], body=event).execute()
    print(f"Updated to May 28!")
    break
else:
    print("Birthday event not found")
