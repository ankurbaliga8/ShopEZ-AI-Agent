import os
import json
import asyncio
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, SecretStr
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from amazon_agent import run_amazon_agent
from walmart_agent import run_walmart_agent

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# LLM API Key (GPT-4o)
api_key = os.getenv("OPENAI_API_KEY")
llm = ChatOpenAI(model="gpt-4o", api_key=SecretStr(api_key))

# Store user shopping lists & conversation history
user_orders = {}  
conversation_history = {}  
running_agents = {}  # Tracks running agent tasks


class ChatRequest(BaseModel):
    message: str
    user_id: str  


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """Handles incoming chat messages and updates the shopping list accordingly."""
    
    global user_orders, conversation_history

    user_id = request.user_id
    user_message = request.message.strip().lower()

    # Initialize user session if new
    if user_id not in user_orders:
        user_orders[user_id] = {"amazon_items": [], "grocery_items": []}
        conversation_history[user_id] = []

    conversation_history[user_id].append({"role": "user", "message": user_message})

    # ✅ Handle "Proceed" command (Starts agents)
    if user_message == "proceed":
        return await process_order(user_id)

    # ✅ Handle "Remove item"
    if user_message.startswith("remove "):
        item_name = user_message.replace("remove ", "").strip()
        user_orders[user_id]["amazon_items"] = [
            item for item in user_orders[user_id]["amazon_items"] if item["name"] != item_name
        ]
        user_orders[user_id]["grocery_items"] = [
            item for item in user_orders[user_id]["grocery_items"] if item["name"] != item_name
        ]
        return JSONResponse(content={"response": f"✅ '{item_name}' has been removed from your list. Type 'Proceed' to confirm order."})

    # ✅ Handle "Show Shopping List"
    if "show whole list" in user_message or "show me the list" in user_message:
        order = user_orders[user_id]
        amazon_items = ", ".join(
            [f"{item['name']} ({item['quantity']})" for item in order["amazon_items"]]
        ) or "none"
        grocery_items = ", ".join(
            [f"{item['name']} ({item['quantity']})" for item in order["grocery_items"]]
        ) or "none"
        return JSONResponse(
            content={"response": f"🛒 **Your Shopping List:**\n- **Amazon:** {amazon_items}\n- **Groceries:** {grocery_items}\n\nType 'Proceed' to confirm."}
        )

    # ✅ Handle Edge Cases (Invalid Inputs)
    if not re.search(r"[a-zA-Z0-9]", user_message) or len(user_message) < 3:
        return JSONResponse(content={"response": "⚠️ I didn't understand that. Please enter valid shopping items. 🛒"})

    # ✅ Construct Full Prompt with Past Conversations
    full_prompt = f"""
    You are an AI shopping assistant managing a user's shopping list.

    **Current Shopping List**
    Amazon: {user_orders[user_id]["amazon_items"]}
    Grocery: {user_orders[user_id]["grocery_items"]}

    **User Request:** "{user_message}"

    - If an item exists, update its quantity.
    - If an item does not exist, add it.
    - If the user says "remove X", remove that item.
    - If the user says "make X Y", set X's quantity to Y.
    
    **Return a JSON response in this format:**
    ```json
    {{
      "amazon_items": [
        {{"name": "item_name", "quantity": number}}
      ],
      "grocery_items": [
        {{"name": "item_name", "quantity": number}}
      ],
      "response": "Natural language summary of the shopping list update."
    }}
    ```
    """

    try:
        response_obj = await llm.ainvoke(full_prompt)
        conversation_response = response_obj.content
        json_match = re.search(r"```json\n(.*?)\n```", conversation_response, re.DOTALL)
        if not json_match:
            raise ValueError("Invalid JSON response from LLM.")

        parsed = json.loads(json_match.group(1).strip())

        # ✅ Fix: Directly Replace Backend List with Updated JSON
        user_orders[user_id] = {
            "amazon_items": parsed["amazon_items"],
            "grocery_items": parsed["grocery_items"]
        }

        conversation_history[user_id].append({"role": "assistant", "message": parsed["response"]})

        return JSONResponse(content={"response": parsed["response"] + " Type 'Proceed' to confirm order."})

    except ValueError as ve:
        return JSONResponse(content={"response": f"⚠️ Unable to process request: {str(ve)}"})

    except Exception as e:
        return JSONResponse(content={"response": "⚠️ Something went wrong. Please try again. 🛒"})


async def process_order(user_id):
    """Starts the ordering process by executing the agent with the most items first."""
    
    global running_agents

    amazon_items = user_orders[user_id]["amazon_items"]
    grocery_items = user_orders[user_id]["grocery_items"]

    # ✅ Check if there are no items to process
    if not amazon_items and not grocery_items:
        return JSONResponse(content={"response": "⚠️ No items in your order. Please add items before proceeding."})

    # ✅ Determine which agent should run first based on item count
    if len(amazon_items) >= len(grocery_items):
        primary_agent, primary_items, primary_name = run_amazon_agent, amazon_items, "Amazon"
        secondary_agent, secondary_items, secondary_name = run_walmart_agent, grocery_items, "Walmart"
    else:
        primary_agent, primary_items, primary_name = run_walmart_agent, grocery_items, "Walmart"
        secondary_agent, secondary_items, secondary_name = run_amazon_agent, amazon_items, "Amazon"

    async def execute_agents():
        """Executes agents in sequence, first the primary, then the secondary."""
        if primary_items:
            await primary_agent(primary_items)
            print(f"✅ {primary_name} agent completed.")

        if secondary_items:
            await secondary_agent(secondary_items)
            print(f"✅ {secondary_name} agent completed.")

    running_agents[user_id] = asyncio.create_task(execute_agents())

    return JSONResponse(content={"response": f"🚀 Order is being processed for {primary_name}. {secondary_name} will follow next if applicable. Type 'Abort' to cancel."})


@app.post("/abort")
async def abort():
    """Stops all running agents and resets memory."""
    
    global user_orders, conversation_history, running_agents

    # ✅ Cancel running tasks properly
    tasks_to_cancel = list(running_agents.values())
    running_agents.clear()

    for task in tasks_to_cancel:
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print("✅ Agent successfully aborted.")

    # ✅ Reset all stored data
    user_orders.clear()
    conversation_history.clear()

    return JSONResponse(content={"response": "🚨 Order aborted. Welcome back! 🛍️"})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
