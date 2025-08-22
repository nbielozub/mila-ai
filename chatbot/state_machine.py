from typing import TypedDict, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from chat_tools import search_eventbrite, search_ticketmaster


# Define the state for the graph
class AgentState(TypedDict):
    messages: List
    user_profile: dict
    openai_api_key: str

def initialize_llm(openai_api_key: str) -> ChatOpenAI:
    """Initialize the OpenAI chat model"""
    return ChatOpenAI(
        model="gpt-4o-mini",
        api_key=openai_api_key,
        temperature=0.7
    )

def get_conversation_history(messages: List) -> str:
    """Get conversation history for context"""
    if not messages:
        return "No conversation history yet."
    
    history = []
    for msg in messages:
        if isinstance(msg, HumanMessage):
            history.append(f"User: {msg.content}")
        elif isinstance(msg, AIMessage):
            history.append(f"Assistant: {msg.content}")
    
    return "\n".join(history)


def profile_building_node(state: AgentState) -> AgentState:
    """Collect survey info and save as profile"""
    user_profile = {
        
    }
    state["user_profile"] = user_profile
    return state

def event_discovery_node(state: AgentState) -> AgentState:
    """Node for event discovery after profile completion"""
    
    # Get user profile
    user_profile = state.get("user_profile", {})
    
    # Create system prompt for event discovery
    system_prompt = f"""
You are a helpful event discovery assistant. The user's profile shows they're interested in {', '.join(user_profile.get('interests', []))} and prefer {user_profile.get('location_preference', 'indoor')} events with a {user_profile.get('budget_range', 'medium')} budget.

Help them discover events. Be conversational, enthusiastic, and provide specific recommendations when possible.

Use Eventbrite and Ticketmaster tools when needed. Eventbrite is great for local events, while Ticketmaster has big concerts and sports.
"""
    
    # Get the latest user message
    latest_message = None
    for msg in reversed(state["messages"]):
        if isinstance(msg, HumanMessage):
            latest_message = msg.content
            break
    
    if not latest_message:
        return state
    
    try:
        # Create conversation context with prompt template
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="messages"),
        ])
        
        # Get response from LLM with tool binding
        llm = initialize_llm(state["openai_api_key"])
        
        llm_with_tools = llm.bind_tools([search_eventbrite, search_ticketmaster])
        
        # Create chain with prompt template and LLM with tools
        chain = prompt_template | llm_with_tools
        
        # Get response using the chain
        response = chain.invoke({
            "messages": state["messages"]
        })

        if getattr(response, "tool_calls", None):
            for call in response.tool_calls:
                tool_name, args = call["name"], call["args"]
                if tool_name == "search_eventbrite":
                    result = search_eventbrite.invoke(args)
                elif tool_name == "search_ticketmaster":
                    result = search_ticketmaster.invoke(args)
                else:
                    result = f"Unknown tool: {tool_name}"
                state["messages"].append(AIMessage(content=f"{tool_name} → {result}"))
        else:
            # Normal response: string or AIMessage
            if isinstance(response, str):
                state["messages"].append(AIMessage(content=response))
            elif isinstance(response, AIMessage):
                state["messages"].append(response)
            else:
                state["messages"].append(AIMessage(content=str(response)))
        
    except Exception as e:
        print(f"Error in event discovery: {str(e)}")
        # Fallback response
        fallback_response = "I'm sorry, I encountered an error. Please try again."
        state["messages"].append(AIMessage(content=fallback_response))
    
    return state

# Build the state graph
builder = StateGraph(AgentState)

# Add nodes
builder.add_node("profile_building", profile_building_node)
builder.add_node("event_discovery", event_discovery_node)

# Set entry point
builder.set_entry_point("profile_building")

# Add edges
builder.add_edge("profile_building", "event_discovery")
builder.add_edge("event_discovery", END)

# Compile the graph
app = builder.compile()

# Initialize memory for conversation persistence
memory = MemorySaver()
app = app.with_config(checkpointer=memory) 