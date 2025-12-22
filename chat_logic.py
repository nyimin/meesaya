import os
import json
from openai import OpenAI
from calculator import calculate_system
from database import get_db_connection

# Configure OpenRouter (Gemini)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

# Admin Command Logic to update prices via chat
def handle_admin_command(text):
    # Syntax: /update [battery/inverter] [size] [price]
    # Example: /update battery 100 3200000
    try:
        parts = text.split(" ")
        category = parts[1].lower()
        size = int(parts[2])
        price = int(parts[3])
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        if category == "battery":
            # Assume 51.2V LiFePO4 for quick updates
            kwh = (51.2 * size) / 1000
            cur.execute("INSERT INTO market_batteries (tech_type, voltage, capacity_ah, energy_kwh, price_mmk, quality_tier) VALUES ('LiFePO4', 51.2, %s, %s, %s, 'Premium')", (size, kwh, price))
        elif category == "inverter":
            # Assume 48V Hybrid
            cur.execute("INSERT INTO market_inverters (tech_type, wattage, system_voltage, price_mmk, quality_tier) VALUES ('Hybrid', %s, 48, %s, 'Standard')", (size, price))
            
        conn.commit()
        conn.close()
        return "✅ Admin Update: Database updated successfully."
    except Exception as e:
        return f"❌ Update Failed: {str(e)}"

# Define the Tool for the AI
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_system",
            "description": "Calculate solar system specs and estimated market price.",
            "parameters": {
                "type": "object",
                "properties": {
                    "watts": {"type": "integer", "description": "Total watts of appliances"},
                    "hours": {"type": "integer", "description": "Hours of backup needed"}
                },
                "required": ["watts", "hours"]
            }
        }
    }
]

SYSTEM_PROMPT = """
You are a friendly, helpful Myanmar Solar Consultant.
1. **Goal:** Help users size their solar/backup system.
2. **Behavior:** Be polite. If the user doesn't provide Watts and Hours, ask nicely. 
3. **Tool:** When you have the numbers, call the `calculate_system` tool.
4. **Output:** Present the results clearly. Mention that prices are "Market Estimates" (Lakhs).
5. **Language:** Reply in the same language as the user (Burmese or English).
6. **Brand Safety:** Do not recommend specific brands. Recommend "Lithium" or "Tubular" types.
"""

def get_ai_reply(user_message):
    # Check for Admin Command
    if user_message.startswith("/update"):
        return handle_admin_command(user_message)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message}
    ]

    # Call Gemini via OpenRouter
    response = client.chat.completions.create(
        model="google/gemini-2.5-flash", # Very fast and cheap
        messages=messages,
        tools=tools,
    )
    
    msg = response.choices[0].message

    # Handle Tool Call
    if msg.tool_calls:
        tool_call = msg.tool_calls[0]
        args = json.loads(tool_call.function.arguments)
        
        # Execute Python Logic
        result_data = calculate_system(args["watts"], args["hours"])
        
        # Feed result back to AI
        messages.append(msg)
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call.id,
            "content": json.dumps(result_data)
        })
        
        # Get Final Summary
        final_res = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=messages
        )
        return final_res.choices[0].message.content

    return msg.content