#!/usr/bin/env python3
"""
Helper script to obtain a Google Ads API refresh token via OAuth2.

Prerequisites:
  1. Create OAuth2 credentials (Desktop app) in Google Cloud Console
  2. Enable the Google Ads API for your project
  3. Have your Developer Token from the Google Ads API Center

Usage:
  python scripts/get_google_refresh_token.py

The script will:
  1. Ask for your client_id and client_secret
  2. Open a browser for Google login + consent
  3. Print the refresh_token to paste into .env

Reference:
  https://developers.google.com/google-ads/api/docs/oauth/cloud-project
"""
from __future__ import annotations

import sys
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlencode, urlparse, parse_qs

# Google OAuth2 endpoints
AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

# Scope required for Google Ads API
SCOPES = "https://www.googleapis.com/auth/adwords"

# Local redirect server
REDIRECT_PORT = 8089
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}"


def main() -> None:
    print()
    print("=" * 60)
    print("  Google Ads API — Refresh Token Generator")
    print("=" * 60)
    print()
    print("You need OAuth2 Desktop credentials from Google Cloud Console.")
    print("See: https://developers.google.com/google-ads/api/docs/oauth/cloud-project")
    print()

    client_id = input("Client ID: ").strip()
    if not client_id:
        print("Error: client_id is required")
        sys.exit(1)

    client_secret = input("Client Secret: ").strip()
    if not client_secret:
        print("Error: client_secret is required")
        sys.exit(1)

    # Build authorization URL
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent",
    }
    auth_url = f"{AUTH_URL}?{urlencode(params)}"

    print()
    print("Opening browser for Google login...")
    print(f"If it doesn't open, visit: {auth_url}")
    print()

    webbrowser.open(auth_url)

    # Start local server to capture the redirect
    auth_code = _wait_for_auth_code()
    if not auth_code:
        print("Error: no authorization code received")
        sys.exit(1)

    # Exchange auth code for tokens
    refresh_token = _exchange_code(client_id, client_secret, auth_code)

    print()
    print("=" * 60)
    print("  SUCCESS — Add these to your .env file:")
    print("=" * 60)
    print()
    print(f"GOOGLE_ADS_CLIENT_ID={client_id}")
    print(f"GOOGLE_ADS_CLIENT_SECRET={client_secret}")
    print(f"GOOGLE_ADS_REFRESH_TOKEN={refresh_token}")
    print()


def _wait_for_auth_code() -> str | None:
    """Run a temporary HTTP server to capture the OAuth redirect."""
    captured_code: list[str] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            query = parse_qs(urlparse(self.path).query)
            code = query.get("code", [None])[0]
            if code:
                captured_code.append(code)
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    b"<html><body><h2>Authorization successful!</h2>"
                    b"<p>You can close this tab and return to the terminal.</p>"
                    b"</body></html>"
                )
            else:
                error = query.get("error", ["unknown"])[0]
                self.send_response(400)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(
                    f"<html><body><h2>Error: {error}</h2></body></html>".encode()
                )

        def log_message(self, format: str, *args) -> None:
            pass  # Suppress request logs

    server = HTTPServer(("localhost", REDIRECT_PORT), Handler)
    print(f"Waiting for OAuth callback on port {REDIRECT_PORT}...")
    server.handle_request()  # Handle a single request
    server.server_close()

    return captured_code[0] if captured_code else None


def _exchange_code(client_id: str, client_secret: str, code: str) -> str:
    """Exchange authorization code for refresh token."""
    import urllib.request
    import json

    data = urlencode({
        "code": code,
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code",
    }).encode()

    req = urllib.request.Request(
        TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req) as resp:
            tokens = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"Error exchanging code: {e.code} {body}")
        sys.exit(1)

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        print("Error: no refresh_token in response. Did you use access_type=offline?")
        print(f"Response: {json.dumps(tokens, indent=2)}")
        sys.exit(1)

    return refresh_token


if __name__ == "__main__":
    main()
