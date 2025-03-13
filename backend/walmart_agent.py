import os
import asyncio
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser
from pydantic import SecretStr
from dotenv import load_dotenv

load_dotenv()

# Initialize the GPT LLM used for agent tasks
gpt_llm = ChatOpenAI(
    model="gpt-4o",
    temperature=0.0,
)

# Define Chrome binary path
chrome_binary_path = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# Configure browser settings
config = BrowserConfig(
    headless=False,          # Keeps UI visible for debugging
    disable_security=True,   # Use cautiously: disables some security features
    chrome_instance_path=chrome_binary_path
)

# Create browser instance
browser = Browser(config=config)

# Pre-defined initial actions for Walmart/Instacart
initial_actions = [
    {'open_tab': {'url': 'https://www.instacart.com/walmart'}},
]

async def run_walmart_agent(items: List[Dict[str, Any]]) -> Any:
    """
    Executes the online grocery ordering process on Instacart/Walmart.com.

    Args:
        items (list): A list of dictionaries where each dictionary contains:
                      - "name" (str): The item name.
                      - "quantity" (int): The desired quantity.

    Returns:
        The result of the agent execution or an appropriate message if no items are provided.
    """
    if not items:
        return "Task Complete: No items to process for Walmart."

    # Build structured instructions for Walmart ordering
    item_instructions = "\n".join([
        f'- Search for "{item["name"]}" ({item["quantity"]} unit(s)) and add to cart.'
        for item in items
    ])
    
    task_prompt = f"""
    ### Step 1: Search & Add Items to Cart
    On Instacart/Walmart.com, perform the following actions for each item:
    {item_instructions}

    #### *Extra Instructions*:
    - If an item card opens, use the quantity dropdown to select the required amount.
    - If an item card opens, click the back button (←) in the top-left corner to return to the search results.

    ### Step 2: Checkout Process
    1. Click the checkout menu at the top-right corner (index 10) and select the green "Checkout" button at the bottom-right.
    2. In the Address section, select the first available radio button (index 3) and confirm it.
    3. Choose the first delivery option: **"Priority"**.
    4. Select the saved credit card for payment and finalize the order.
    """

    # Initialize and run the agent
    agent = Agent(
        task=task_prompt,
        llm=gpt_llm,
        browser=browser,
        initial_actions=initial_actions,
        use_vision=False,  # No need for vision-based automation
    )
    result = await agent.run()
    return result


