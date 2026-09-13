"""
SharedNet Public Cloud Tunnel Gateway Launcher
Manages live public ingress tunnels (localtunnel, ngrok, cloudflared) for AgentScout.
"""

import sys
import os
import shutil
import subprocess
import time


def check_tool(name: str) -> bool:
    return shutil.which(name) is not None


def launch_gateway(port: int = 8000, preferred: str = "auto"):
    print("=" * 80)
    print("[*] AGENTSCOUT PUBLIC CLOUD TUNNEL GATEWAY")
    print("=" * 80)
    print(f"[+] Target Local Port : {port}")
    print(f"[+] Purpose String    : Independent multi-source factual verification for AI agents.")

    # 1. Check for ngrok
    if (preferred in {"auto", "ngrok"}) and check_tool("ngrok"):
        print("[+] Found 'ngrok' binary. Launching tunnel on port 8000...")
        try:
            proc = subprocess.Popen(["ngrok", "http", str(port)])
            print("[✓] ngrok tunnel launched successfully!")
            print("[+] Open http://127.0.0.1:4040 to view the public URL and live traffic inspection.")
            proc.wait()
            return
        except Exception as e:
            print(f"[!] ngrok launch error: {e}")

    # 2. Check for localtunnel / npx localtunnel
    if (preferred in {"auto", "localtunnel", "lt"}):
        if check_tool("lt"):
            print("[+] Found 'lt' (localtunnel). Launching tunnel...")
            try:
                subprocess.run(["lt", "--port", str(port)])
                return
            except Exception as e:
                print(f"[!] lt launch error: {e}")
        elif check_tool("npx"):
            print("[+] Found 'npx'. Launching localtunnel via npx...")
            try:
                subprocess.run(["npx", "--yes", "localtunnel", "--port", str(port)])
                return
            except Exception as e:
                print(f"[!] npx localtunnel launch error: {e}")

    # 3. Check for cloudflared
    if (preferred in {"auto", "cloudflared"}) and check_tool("cloudflared"):
        print("[+] Found 'cloudflared'. Launching quick tunnel...")
        try:
            subprocess.run(["cloudflared", "tunnel", "--url", f"http://localhost:{port}"])
            return
        except Exception as e:
            print(f"[!] cloudflared launch error: {e}")

    # Fallback instructions if no external tunnel binary is installed
    print("\n[!] No external tunnel binary detected on PATH (ngrok, lt, npx, cloudflared).")
    print("[+] Quick Install Options:")
    print("    - Option 1 (Zero-install with npm): npx localtunnel --port 8000")
    print("    - Option 2 (ngrok): ngrok http 8000")
    print("    - Option 3 (cloudflared): cloudflared tunnel --url http://localhost:8000")
    print("\n[+] Local A2A Gateway active at: http://localhost:8000")
    print("=" * 80)


if __name__ == "__main__":
    port_arg = int(sys.argv[1]) if len(sys.argv) > 1 and sys.argv[1].isdigit() else 8000
    launch_gateway(port=port_arg)
