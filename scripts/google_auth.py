#!/usr/bin/env python3
"""
Super Tobi — Google Auth Setup
Authenticates with Google APIs (Calendar, Gmail, YouTube, Photos)
and saves the token for future use.
"""

import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "config", "google_credentials.json")
TOKEN_FILE = os.path.join(BASE_DIR, "config", "google_token.json")

# Scopes for Calendar, Gmail, YouTube, and Photos
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/photoslibrary.readonly",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


def authenticate():
    creds = None

    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # Refresh or get new token
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("Refreshing expired token...")
                creds.refresh(Request())
            except Exception as e:
                print(f"Refresh failed ({e}), re-authenticating via browser...")
                creds = None
        if not creds or not creds.valid:
            print("Opening browser for Google authentication...")
            print("Log in with your Google account and grant access.\n")
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8090)

        # Save token
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())
        print(f"\nToken saved to {TOKEN_FILE}")

    print("Google authentication successful!")
    return creds


if __name__ == "__main__":
    authenticate()
