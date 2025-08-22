from langchain_core.messages import HumanMessage
from state_machine import app 
import os
from dotenv import load_dotenv
load_dotenv()
def run_test():
    # Define initial state (survey result + API keys) Replace later with actual survey data
    state = {
        "messages": [],
        "user_profile": {
            "name": "Alice",
            "interests": ["music", "tech"],
            "location_preference": "indoor",
            "budget_range": "medium"
        },
        "openai_api_key": os.getenv("OPENAI_API_KEY"),
        
        
    }

    # Add a user message
    state["messages"].append(HumanMessage(content="Find me concerts in New York"))

    # Run the graph
    final_state = app.invoke(state)

    # Print conversation
    print("\n--- Conversation ---")
    for msg in final_state["messages"]:
        role = "User" if isinstance(msg, HumanMessage) else "Assistant"
        print(f"{role}: {msg.content}")

if __name__ == "__main__":
    run_test()