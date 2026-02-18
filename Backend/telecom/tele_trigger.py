import requests

# --- CONFIGURATION ---
ACCOUNT_SID = "babyenterprisesandco1"
API_KEY = "4076534d7ccc5f712bbe451f070c1c66e06ac5cb963119f7"       # Copy from Screenshot 2
API_TOKEN = "c24322e8e32076c654f107846002001c867bea736714b3b8"   # Copy from Screenshot 2

YOUR_PHONE = "08754279679"     # Your Personal Mobile
EXOPHONE = "04448134863"       # Your Exotel Number
APP_ID = "1168313"             # From Screenshot 2

# --- MAKE THE CALL ---
url = f"https://api.exotel.com/v1/Accounts/{ACCOUNT_SID}/Calls/connect.json"

payload = {
    'From': YOUR_PHONE,
    'CallerId': EXOPHONE,
    'Url': f"http://my.exotel.com/{ACCOUNT_SID}/exoml/start_voice/{APP_ID}",
    'CallType': "trans"
}

print(f"Dialing {YOUR_PHONE}...")
response = requests.post(url, auth=(API_KEY, API_TOKEN), data=payload)
print(response.text)