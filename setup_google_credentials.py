#!/usr/bin/env python3
"""
Google API Credentials Setup for Jarvis Assistant.

This script helps users set up Google Calendar and Gmail API credentials
for OAuth2 authentication. It guides through the process of:

1. Creating Google Cloud Project
2. Enabling Calendar and Gmail APIs
3. Creating OAuth2 credentials
4. Downloading and placing credential files
"""

import os
import json
import sys
from pathlib import Path


def main():
    print("=" * 60)
    print("Google API Credentials Setup for Jarvis Assistant")
    print("=" * 60)
    print()
    
    # Check if credentials directory exists
    credentials_dir = Path("credentials")
    credentials_dir.mkdir(exist_ok=True)
    
    print("This setup will guide you through configuring Google API access for:")
    print("  • Google Calendar integration")
    print("  • Gmail integration")
    print()
    
    print("STEP 1: Google Cloud Console Setup")
    print("-" * 35)
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Create a new project or select existing one")
    print("3. Enable the following APIs:")
    print("   - Google Calendar API")
    print("   - Gmail API")
    print("4. Go to 'Credentials' in the sidebar")
    print("5. Click '+ CREATE CREDENTIALS' → 'OAuth client ID'")
    print("6. Choose 'Desktop application'")
    print("7. Download the JSON file")
    print()
    
    # Get credential file paths
    calendar_creds = credentials_dir / "google_credentials.json"
    gmail_creds = credentials_dir / "gmail_credentials.json"
    
    print("STEP 2: Place Credential Files")
    print("-" * 30)
    print("Copy your downloaded credential files to:")
    print(f"  • Calendar: {calendar_creds.absolute()}")
    print(f"  • Gmail:    {gmail_creds.absolute()}")
    print()
    print("Note: You can use the same credential file for both services")
    print("      Just copy it to both locations.")
    print()
    
    # Check if files exist
    calendar_exists = calendar_creds.exists()
    gmail_exists = gmail_creds.exists()
    
    print("STEP 3: Verify Setup")
    print("-" * 19)
    print(f"Calendar credentials: {'✓ Found' if calendar_exists else '✗ Missing'}")
    print(f"Gmail credentials:    {'✓ Found' if gmail_exists else '✗ Missing'}")
    print()
    
    if calendar_exists and gmail_exists:
        print("✅ All credential files are in place!")
        print()
        print("STEP 4: Test Authentication")
        print("-" * 28)
        print("Start your Jarvis MCP server and try a Google API action:")
        print("  python start_mcp_server.py")
        print()
        print("The first time you use Google APIs, you'll be prompted to:")
        print("1. Open a browser window")
        print("2. Sign in to your Google account")
        print("3. Grant permissions to Jarvis")
        print()
        print("After authentication, tokens will be saved for future use.")
        
    else:
        print("❌ Missing credential files!")
        print()
        print("Please complete the setup by placing the credential files")
        print("in the locations shown above, then run this script again.")
        
        if not calendar_exists:
            print(f"Missing: {calendar_creds}")
        if not gmail_exists:
            print(f"Missing: {gmail_creds}")
        
        return 1
    
    print()
    print("STEP 5: OAuth Scopes")
    print("-" * 18)
    print("When prompted, Jarvis will request these permissions:")
    print("  • Read/write access to your Google Calendar")
    print("  • Read/write access to your Gmail")
    print()
    print("These are necessary for Jarvis to:")
    print("  • Create and manage calendar events")
    print("  • Read and send emails")
    print("  • Provide intelligent scheduling assistance")
    print("  • Extract action items from emails")
    print()
    
    print("STEP 6: Environment Variables (Optional)")
    print("-" * 39)
    print("You may want to set these environment variables in your .env file:")
    print("  # Google API rate limiting")
    print("  GOOGLE_API_RATE_LIMIT=30  # requests per minute")
    print()
    
    print("Setup complete! 🎉")
    print()
    print("For troubleshooting:")
    print("  • Check Google Cloud Console quota limits")
    print("  • Verify APIs are enabled for your project")
    print("  • Ensure OAuth consent screen is configured")
    print("  • Check Jarvis logs for detailed error messages")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())