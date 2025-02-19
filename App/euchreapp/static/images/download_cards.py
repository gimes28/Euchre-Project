import os
import requests

# Base API URL
API_URL = "https://deckofcardsapi.com/static/img"

# Card suits and ranks for Euchre (9, 10, J, Q, K, A)
suits = ["H", "D", "C", "S"]  # Hearts, Diamonds, Clubs, Spades
ranks = ["9", "10", "J", "Q", "K", "A"]

# Django Static Images Folder (Change if needed)
SAVE_PATH = "static/images/cards"

# Ensure directory exists
os.makedirs(SAVE_PATH, exist_ok=True)

# Download each card image
for suit in suits:
    for rank in ranks:
        card_code = f"{rank}{suit}"  # Example: "9H", "JD", "AC"
        image_url = f"{API_URL}/{card_code}.png"
        save_location = os.path.join(SAVE_PATH, f"{rank}_of_{suit}.png")

        try:
            response = requests.get(image_url, stream=True)
            if response.status_code == 200:
                with open(save_location, "wb") as file:
                    for chunk in response.iter_content(1024):
                        file.write(chunk)
                print(f"✅ Saved: {save_location}")
            else:
                print(f"❌ Failed: {image_url} (Status: {response.status_code})")
        except requests.RequestException as e:
            print(f"🚨 Error downloading {image_url}: {e}")

# Download a card back image
card_back_url = "https://deckofcardsapi.com/static/img/back.png"
card_back_path = os.path.join(SAVE_PATH, "back.png")

try:
    response = requests.get(card_back_url, stream=True)
    if response.status_code == 200:
        with open(card_back_path, "wb") as file:
            for chunk in response.iter_content(1024):
                file.write(chunk)
        print(f"✅ Saved: {card_back_path}")
    else:
        print(f"❌ Failed: {card_back_url} (Status: {response.status_code})")
except requests.RequestException as e:
    print(f"🚨 Error downloading {card_back_url}: {e}")
