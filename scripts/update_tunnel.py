import sys
import re
import os
import subprocess
from dotenv import load_dotenv

def main():
    if len(sys.argv) != 2:
        print("Usage: python update_tunnel.py <tunnel_url>")
        print("Example: python update_tunnel.py https://example-tunnel.trycloudflare.com")
        sys.exit(1)

    tunnel_url = sys.argv[1].strip().rstrip("/")
    
    # 1. Validate URL
    if not tunnel_url.startswith("https://") or not tunnel_url.endswith(".trycloudflare.com"):
        print("Error: The URL must be an HTTPS trycloudflare.com URL.")
        sys.exit(1)
        
    print(f"[*] Starting update for tunnel: {tunnel_url}")
    
    # 2. Update OpenAPI YAML
    yaml_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "orchestrate", "openapi.yaml")
    if not os.path.exists(yaml_path):
        print(f"Error: Could not find {yaml_path}")
        sys.exit(1)
        
    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Replace the existing url with the new one using regex to preserve the rest of the file
        new_url_string = f"url: {tunnel_url}/api/v1/orchestrate"
        pattern = r"url:\s*https://[a-zA-Z0-9-]+\.trycloudflare\.com/api/v1/orchestrate"
        
        if not re.search(pattern, content):
            print("Error: Could not find the expected trycloudflare.com URL pattern in openapi.yaml")
            sys.exit(1)
            
        new_content = re.sub(pattern, new_url_string, content)
        
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        print("[+] Successfully updated orchestrate/openapi.yaml")
    except Exception as e:
        print(f"Error updating YAML: {e}")
        sys.exit(1)

    # 3. Read API Key
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
    api_key = os.getenv("ORCHESTRATE_API_KEY")
    if not api_key:
        print("Error: ORCHESTRATE_API_KEY not found in .env file.")
        sys.exit(1)
        
    print("[*] Successfully loaded ORCHESTRATE_API_KEY from environment")

    # 4. Run Orchestrate CLI Commands
    def run_cmd(cmd, hide_output=False):
        print(f"[*] Running: {' '.join(cmd) if not hide_output else cmd[0] + ' ***'}")
        try:
            result = subprocess.run(
                cmd,
                check=True,
                cwd=os.path.dirname(os.path.dirname(__file__))
            )
            return result
        except subprocess.CalledProcessError:
            print(f"Error: Command failed!")
            sys.exit(1)

    # Configure connection
    cmd1 = [
        "orchestrate", "connections", "configure", 
        "-a", "helix_health_api", 
        "--env", "draft", 
        "-t", "team", 
        "-k", "bearer", 
        "-u", tunnel_url
    ]
    run_cmd(cmd1)
    
    # Set credentials (hide output so we don't print the token)
    cmd2 = [
        "orchestrate", "connections", "set-credentials", 
        "-a", "helix_health_api", 
        "--env", "draft", 
        "--token", api_key
    ]
    # Pass hide_output=True so we don't print the token to the console
    print("[*] Running: orchestrate connections set-credentials ...")
    try:
        subprocess.run(
            cmd2,
            check=True,
            cwd=os.path.dirname(os.path.dirname(__file__))
        )
    except subprocess.CalledProcessError:
        print("Error: Failed to set credentials!")
        sys.exit(1)
        
    # Import tools
    cmd3 = [
        "orchestrate", "tools", "import", 
        "-k", "openapi", 
        "-f", "orchestrate/openapi.yaml", 
        "-a", "helix_health_api"
    ]
    run_cmd(cmd3)

    print("\n[+] Success! The Helix Health API tunnel and connection have been updated.")

if __name__ == "__main__":
    main()
