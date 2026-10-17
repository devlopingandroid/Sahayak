"""Optional terminal control of the same laptop audio service used by the dashboard."""
import getpass
import requests

SERVER_URL = "http://localhost:5000"

def run_assistant():
    client = requests.Session()
    state = client.get(SERVER_URL + "/api/auth", timeout=5).json()
    if not state["configured"]:
        print("Open http://localhost:5000 to create your caretaker password first.")
        return
    response = client.post(SERVER_URL + "/api/auth", json={"password": getpass.getpass("Caretaker password: ")}, timeout=10)
    response.raise_for_status()
    while input("Enter to listen using the laptop, or q to quit: ").strip().lower() != "q":
        result = client.post(SERVER_URL + "/api/audio/listen", json={}, timeout=40)
        value = result.json()
        if not result.ok:
            print(value.get("error", "Audio request failed"))
            continue
        print("You:", value["text"])
        print("SAHAYAK:", value["response"])
        client.post(SERVER_URL + "/api/audio/speak", json={"text": value["response"]}, timeout=5).raise_for_status()

if __name__ == "__main__":
    try:
        run_assistant()
    except requests.RequestException as error:
        print("Start the SAHAYAK server first. Connection or sign-in failed.")
