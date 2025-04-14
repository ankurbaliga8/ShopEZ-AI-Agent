import os
import json
import asyncio
import re
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, SecretStr
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from amazon_agent import run_amazon_agent, browser as amazon_browser
from walmart_agent import run_walmart_agent, browser as walmart_browser

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Global variables
running_agents = {}
browser_instances = {}

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
        try:
            if primary_items:
                # Store browser reference for this user
                if primary_name.lower() == "amazon":
                    browser_instances[user_id] = amazon_browser
                else:
                    browser_instances[user_id] = walmart_browser
                    
                await primary_agent(primary_items)
                print(f"✅ {primary_name} agent completed.")

            if secondary_items:
                # Update browser reference for secondary agent
                if secondary_name.lower() == "amazon":
                    browser_instances[user_id] = amazon_browser
                else:
                    browser_instances[user_id] = walmart_browser
                    
                await secondary_agent(secondary_items)
                print(f"✅ {secondary_name} agent completed.")
        except asyncio.CancelledError:
            print(f"🛑 Task for user {user_id} was cancelled.")
            raise
        finally:
            # Clean up when done
            if user_id in browser_instances:
                try:
                    # Close the browser
                    await browser_instances[user_id].close()
                    print(f"✅ Browser for user {user_id} closed automatically after completion.")
                    
                    # Force close Chrome as a backup measure
                    import subprocess
                    import platform
                    
                    system = platform.system()
                    if system == "Darwin":  # macOS
                        subprocess.run(["pkill", "-f", "Google Chrome"], check=False)
                    elif system == "Windows":
                        subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], check=False)
                    elif system == "Linux":
                        subprocess.run(["pkill", "-f", "chrome"], check=False)
                        
                    print(f"🔥 Forcefully terminated Chrome browser processes.")
                except Exception as e:
                    print(f"Error closing browser after completion: {e}")
                finally:
                    del browser_instances[user_id]

    running_agents[user_id] = asyncio.create_task(execute_agents())

    return JSONResponse(content={"response": f"🚀 Order is being processed for {primary_name}. {secondary_name} will follow next if applicable. Type 'Abort' to cancel."})


@app.post("/abort")
async def abort(request: dict = Body(...)):
    """Stops running agent for a specific user and resets their memory."""
    
    global user_orders, conversation_history, running_agents
    user_id = request.get("user_id", "")
    
    # Check if there's a running agent for this user
    if user_id in running_agents:
        # Get the task for this specific user
        task = running_agents[user_id]
        
        # Remove from running_agents dictionary
        del running_agents[user_id]
        
        # Try to close the browser first if it exists
        if user_id in browser_instances:
            try:
                # Close the browser
                browser = browser_instances[user_id]
                await browser.close()
                print(f"✅ Browser for user {user_id} closed successfully.")
                
                # Force close Chrome as a backup measure
                import subprocess
                import platform
                
                system = platform.system()
                if system == "Darwin":  # macOS
                    subprocess.run(["pkill", "-f", "Google Chrome"], check=False)
                elif system == "Windows":
                    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], check=False)
                elif system == "Linux":
                    subprocess.run(["pkill", "-f", "chrome"], check=False)
                    
                print(f"🔥 Forcefully terminated Chrome browser processes.")
                
                del browser_instances[user_id]
            except Exception as e:
                print(f"Error closing browser: {e}")
        
        # Cancel the task if it's not done
        if not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                print(f"✅ Agent for user {user_id} successfully aborted.")
            except Exception as e:
                print(f"Error while aborting agent: {e}")
        
        # Clear user specific data
        if user_id in user_orders:
            del user_orders[user_id]
        if user_id in conversation_history:
            del conversation_history[user_id]
            
        return JSONResponse(content={"response": "🚨 Order aborted. Welcome back! 🛍️"})
    else:
        return JSONResponse(content={"response": "No active orders to abort."})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
