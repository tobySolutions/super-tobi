#!/usr/bin/env python3
"""
Super Tobi — Add Birthdays to Google Calendar
Creates recurring annual birthday events for all people in the birthdays database.
"""

import os
import json
from datetime import datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOKEN_FILE = os.path.join(BASE_DIR, "config", "google_token.json")
BIRTHDAYS_FILE = os.path.join(BASE_DIR, "data", "relationships", "birthdays.json")

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    return build("calendar", "v3", credentials=creds)


def create_birthday_event(service, person):
    name = person["name"]
    date = person["date"]  # MM-DD format
    relationship = person.get("relationship", "")
    notes = person.get("notes", "")
    year_of_birth = person.get("year_of_birth")

    month, day = date.split("-")

    # Use 2026 as the base year for the first occurrence
    start_date = f"2026-{month}-{day}"

    summary = f"🎂 {name}'s Birthday"
    if relationship == "self":
        summary = f"🎂 Happy Birthday Tobiloba!"

    description = f"Birthday reminder for {name}"
    if relationship:
        description += f"\nRelationship: {relationship}"
    if year_of_birth:
        description += f"\nBorn: {year_of_birth}"
    if notes:
        description += f"\nNotes: {notes}"
    description += "\n\n— Super Tobi 🤖"

    event = {
        "summary": summary,
        "description": description,
        "start": {
            "date": start_date,
        },
        "end": {
            "date": start_date,
        },
        "recurrence": [
            "RRULE:FREQ=YEARLY"
        ],
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": 1440},   # 1 day before
                {"method": "popup", "minutes": 10080},   # 1 week before
            ],
        },
    }

    result = service.events().insert(calendarId="primary", body=event).execute()
    return result


def main():
    print("Super Tobi — Birthday Calendar Setup")
    print("=" * 40)

    if not os.path.exists(TOKEN_FILE):
        print("Error: No Google token found. Run google_auth.py first.")
        return

    with open(BIRTHDAYS_FILE) as f:
        birthdays = json.load(f)

    service = get_calendar_service()

    for person in birthdays:
        if person["date"] == "FILL-IN":
            print(f"⏭️  Skipping {person['name']} — no date set")
            continue

        try:
            result = create_birthday_event(service, person)
            print(f"✅ Added {person['name']}'s birthday ({person['date']}) — {result.get('htmlLink', '')}")
        except Exception as e:
            print(f"❌ Failed for {person['name']}: {e}")

    print("\n🎉 All birthdays added to Google Calendar!")
    print("You'll get reminders 1 week and 1 day before each birthday.")


if __name__ == "__main__":
    main()
