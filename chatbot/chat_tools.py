from langchain_core.tools import tool
from dotenv import load_dotenv
import os, requests
load_dotenv()

EVENTBRITE_TOKEN = os.getenv("EVENTBRITE_API_KEY")
TICKETMASTER_TOKEN = os.getenv("TICKETMASTER_API_KEY")

@tool
def search_eventbrite(query: str, location: str = None) -> str:
    """Search for events on Eventbrite by keyword and optional location."""
    url = "https://www.eventbriteapi.com/v3/events/search/"
    headers = {"Authorization": f"Bearer {EVENTBRITE_TOKEN}"}
    params = {"q": query, "expand": "venue", "sort_by": "date"}
    if location:
        params["location.address"] = location

    resp = requests.get(url, headers=headers, params=params)
    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"

    data = resp.json()
    results = []
    for e in data.get("events", [])[:5]:
        results.append(
            f"{e['name']['text']} on {e['start']['local']} at "
            f"{e['venue']['address']['localized_address_display']} ({e['url']})"
        )
    return "\n".join(results) if results else "No events found."

@tool
def search_ticketmaster(query: str, location: str = None) -> str:
    """Search for events on Ticketmaster by keyword and optional location."""
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {"apikey": TICKETMASTER_TOKEN, "keyword": query, "size": 5}
    if location:
        params["city"] = location

    resp = requests.get(url, params=params)
    if resp.status_code != 200:
        return f"Error {resp.status_code}: {resp.text}"

    data = resp.json()
    results = []
    for e in data.get("_embedded", {}).get("events", []):
        venue = e["_embedded"]["venues"][0]["name"]
        results.append(
            f"{e['name']} on {e['dates']['start']['localDate']} at {venue} ({e['url']})"
        )
    return "\n".join(results) if results else "No events found."