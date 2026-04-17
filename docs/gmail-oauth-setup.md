# Gmail and Calendar OAuth setup

This repo defaults to mock data so it is runnable immediately. If you want to replace the mocks with real Gmail and Calendar access later, use this checklist:

1. Create a Google Cloud project.
2. Enable Gmail API and Google Calendar API.
3. Configure an OAuth consent screen for testing.
4. Add these scopes:
   - `https://www.googleapis.com/auth/gmail.readonly`
   - `https://www.googleapis.com/auth/gmail.send`
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/calendar.readonly`
   - `https://www.googleapis.com/auth/calendar.events`
5. Create a desktop OAuth client.
6. Save the downloaded file as `agent/credentials.json`.
7. Generate `agent/token.json` locally during the first auth flow.

The current `agent/gmail_client.py` and `agent/calendar_client.py` are intentionally mock-first scaffolds. They are the right place to add the real OAuth-backed implementations.
