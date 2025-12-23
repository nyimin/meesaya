import os
import json
import requests
from openai import OpenAI
from calculator import calculate_system
from database import get_db_connection, save_chat_log, get_recent_history

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_FB_ID") 

def send_to_facebook(recipient_id, text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

def handle_admin_command(sender_id, text):
    if sender_id != ADMIN_ID:
        return "⛔ Authorization Failed."

    # Simple logic to add a package dynamically
    # Syntax: /addpackage [Name] [Watts] [kWh] [Price]
    try:
        parts = text.split(" ", 4)
        name = parts[1]
        watts = int(parts[2])
        kwh = float(parts[3])
        price = int(parts[4])
        
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO market_packages (name, inverter_watts, battery_kwh, system_voltage, total_price_mmk, includes_panels, description) 
                    VALUES (%s, %s, %s, 48, %s, FALSE, 'Admin Added Package')
                """, (name, watts, kwh, price))
                conn.commit()
        return f"✅ Package '{name}' added at {price} MMK"
    except Exception as e:
        return f"❌ Error: {e}"

tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_system",
            "description": "Calculate solar system specs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "watts": {"type": "integer"},
                    "hours": {"type": "integer"}
                },
                "required": ["watts", "hours"]
            }
        }
    }
]

SYSTEM_PROMPT = """
You are a friendly Myanmar Solar Consultant.
1. Use `calculate_system` if user gives Watts and Hours.
2. If the tool says "MARKET_SET", announce it happily: "Great news! We have a promo set..."
3. If "CUSTOM_BUILD", explain the breakdown clearly.
4. Explain "Installation/Accessories" covers cables, breakers, and safety gear.
5. Be concise. Prices in MMK (Lakhs).
"""

def process_ai_message(sender_id, user_message):
    # 1. Admin Check
    if user_message.startswith("/addpackage"):
        reply = handle_admin_command(sender_id, user_message)
        send_to_facebook(sender_id, reply)
        return

    # 2. Build Context
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = get_recent_history(sender_id, limit=4)
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        # 3. AI Call
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=messages,
            tools=tools,
        )

        msg = response.choices[0].message

        # 4. Tool Execution
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            args = json.loads(tool_call.function.arguments)
            
            result_data = calculate_system(args["watts"], args["hours"])
            
            messages.append(msg)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result_data)
            })
            
            final_res = client.chat.completions.create(
                model="google/gemini-2.5-flash",
                messages=messages
            )
            bot_reply = final_res.choices[0].message.content
        else:
            bot_reply = msg.content

        # 5. Send & Log
        send_to_facebook(sender_id, bot_reply)
        save_chat_log(sender_id, "bot", bot_reply)

    except Exception as e:
        print(f"AI Error: {e}")
        send_to_facebook(sender_id, "Sorry, I am offline briefly.")