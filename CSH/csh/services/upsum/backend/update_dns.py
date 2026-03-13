import requests
import os

# Netlify API endpoint for DNS records
NETLIFY_API = "https://api.netlify.com/api/v1/dns_zones/{zone_id}/dns_records"
NETLIFY_TOKEN = os.getenv("NETLIFY_TOKEN")  # Store your Netlify personal access token in an environment variable
ZONE_ID = os.getenv("NETLIFY_ZONE_ID")      # Store your Netlify DNS zone ID in an environment variable
RECORD_NAME = "upsum.oscyra.solutions"      # The DNS record to update

# Get public IP
def get_public_ip():
    return requests.get("https://api.ipify.org").text

# Update Netlify DNS record
def update_dns_record(ip):
    headers = {
        "Authorization": f"Bearer {NETLIFY_TOKEN}",
        "Content-Type": "application/json"
    }
    # Find existing A record
    resp = requests.get(NETLIFY_API.format(zone_id=ZONE_ID), headers=headers)
    resp.raise_for_status()
    records = resp.json()
    a_record = next((r for r in records if r["type"] == "A" and r["hostname"] == RECORD_NAME), None)
    if a_record:
        # Update existing record
        record_id = a_record["id"]
        update_url = f"{NETLIFY_API.format(zone_id=ZONE_ID)}/{record_id}"
        data = {"value": ip}
        resp = requests.put(update_url, headers=headers, json=data)
        resp.raise_for_status()
        print(f"Updated A record for {RECORD_NAME} to {ip}")
    else:
        # Create new record
        data = {"type": "A", "hostname": RECORD_NAME, "value": ip}
        resp = requests.post(NETLIFY_API.format(zone_id=ZONE_ID), headers=headers, json=data)
        resp.raise_for_status()
        print(f"Created A record for {RECORD_NAME} with {ip}")

if __name__ == "__main__":
    ip = get_public_ip()
    update_dns_record(ip)
