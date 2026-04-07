#!/usr/bin/env python3
"""
Super Tobi — Push Markdown to Google Docs
Creates a Google Doc from a markdown file using the existing auth token.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google_auth import authenticate
from googleapiclient.discovery import build


def markdown_to_docs_requests(markdown_text):
    """Convert markdown text into Google Docs API insert requests."""
    requests = []
    lines = markdown_text.split("\n")
    idx = 1  # Docs index starts at 1

    for line in lines:
        # Determine heading level
        heading_level = 0
        text = line
        if line.startswith("######"):
            heading_level = 6
            text = line[6:].strip()
        elif line.startswith("#####"):
            heading_level = 5
            text = line[5:].strip()
        elif line.startswith("####"):
            heading_level = 4
            text = line[4:].strip()
        elif line.startswith("###"):
            heading_level = 3
            text = line[3:].strip()
        elif line.startswith("##"):
            heading_level = 2
            text = line[2:].strip()
        elif line.startswith("#"):
            heading_level = 1
            text = line[1:].strip()

        # Skip horizontal rules
        if line.strip() in ("---", "***", "___"):
            text = "\n"
            requests.append({
                "insertText": {"location": {"index": idx}, "text": text}
            })
            idx += len(text)
            continue

        # Strip bold markdown markers for display
        clean_text = text.replace("**", "").replace("__", "")

        insert_text = clean_text + "\n"
        requests.append({
            "insertText": {"location": {"index": idx}, "text": insert_text}
        })

        # Apply heading style
        if heading_level > 0 and clean_text.strip():
            heading_map = {
                1: "HEADING_1",
                2: "HEADING_2",
                3: "HEADING_3",
                4: "HEADING_4",
                5: "HEADING_5",
                6: "HEADING_6",
            }
            requests.append({
                "updateParagraphStyle": {
                    "range": {"startIndex": idx, "endIndex": idx + len(insert_text)},
                    "paragraphStyle": {"namedStyleType": heading_map[heading_level]},
                    "fields": "namedStyleType",
                }
            })

        # Bold detection: find **text** segments in the original line
        import re
        bold_segments = list(re.finditer(r"\*\*(.+?)\*\*", text))
        # Calculate offset for bold in clean_text
        offset = 0
        for match in bold_segments:
            # Find the bold text in clean_text
            bold_text = match.group(1)
            pos = clean_text.find(bold_text, offset)
            if pos >= 0:
                requests.append({
                    "updateTextStyle": {
                        "range": {
                            "startIndex": idx + pos,
                            "endIndex": idx + pos + len(bold_text),
                        },
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                })
                offset = pos + len(bold_text)

        idx += len(insert_text)

    return requests


def push_to_gdocs(filepath, title=None):
    """Create a Google Doc from a markdown file."""
    with open(filepath, "r") as f:
        content = f.read()

    if not title:
        # Extract title from first heading
        for line in content.split("\n"):
            if line.startswith("#"):
                title = line.lstrip("#").strip()
                break
        if not title:
            title = os.path.basename(filepath).replace(".md", "")

    print(f"  Authenticating with Google...")
    creds = authenticate()

    docs_service = build("docs", "v1", credentials=creds)

    print(f"  Creating Google Doc: {title}")
    doc = docs_service.documents().create(body={"title": title}).execute()
    doc_id = doc["documentId"]
    doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
    print(f"  Document created: {doc_url}")

    print(f"  Inserting content...")
    requests = markdown_to_docs_requests(content)

    if requests:
        docs_service.documents().batchUpdate(
            documentId=doc_id, body={"requests": requests}
        ).execute()

    print(f"\n  Done! Google Doc URL:")
    print(f"  {doc_url}")
    return doc_url


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: push_to_gdocs.py <markdown_file> [title]")
        sys.exit(1)

    filepath = sys.argv[1]
    title = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else None
    push_to_gdocs(filepath, title)
