import os
import asyncio
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from browser_use import Agent, BrowserConfig, Browser
from pydantic import SecretStr
from dotenv import load_dotenv

load_dotenv()

# Initialize the GPT LLM used for agent tasks (this is separate from Deepseek)
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

# Pre-defined initial actions for Amazon
initial_actions = [
    {'open_tab': {'url': 'https://www.amazon.com'}},
]

async def run_amazon_agent(items: List[Dict[str, Any]]) -> Any:
    """
    Executes the online ordering process on Amazon.com.

    Args:
        items (list): A list of dictionaries where each dictionary contains:
                      - "name" (str): The item name.
                      - "quantity" (int): The desired quantity.

    Returns:
        Execution details or an error message.
    """
    if not items:
        return "Task Complete: No items to process for Amazon."

    # Build structured step instructions for Amazon ordering process
    item_instructions = "\n".join([
        f'- Search for "{item["name"]}" ({item["quantity"]} unit(s)) and add to cart.'
        for item in items
    ])
    
    task_prompt = f"""
### Step 1: Search & Add Items to Cart
On Amazon.com, perform the following actions for each item:
{item_instructions}

### Step 2: Checkout Process
1. Click proceed to checkout.
2. Use the credit card ending with **3585** for payment.
3. Select **free delivery** if available, otherwise choose the cheaper option.
4. **Place order** and confirm completion.
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


