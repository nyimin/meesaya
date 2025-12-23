import os
import json
import requests
from openai import OpenAI
from calculator import calculate_system
from database import get_db_connection, save_chat_log, get_recent_history

# Initialize OpenAI Client (OpenRouter)
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY"),
)

PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")
ADMIN_ID = os.environ.get("ADMIN_FB_ID") 

def send_to_facebook(recipient_id, text):
    """Sends a text response back to the user via Facebook Messenger API."""
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code != 200:
            print(f"FB Send Error: {r.text}")
    except Exception as e:
        print(f"Network Error: {e}")

# --- 1. DEFINING THE PERSONA ---
SYSTEM_PROMPT = """
You are "MeeSaya" (မီးဆရာ), a friendly and practical male Myanmar Energy Consultant. You are like a helpful engineer at a local tea shop.

**CRITICAL INSTRUCTIONS:**
1. **LANGUAGE:** ALWAYS respond in **Myanmar Language (Burmese)**. NEVER use English in your final response to the user.
2. **PERSONA:** You are MALE. Use male polite markers like "Khamya" (ခင်ဗျာ) at the end of sentences where appropriate, and refer to yourself as "Kyano" (ကျွန်တော်) if needed.
3. **TONE:** Informal, friendly, short, and concise. Avoid long paragraphs. Get straight to the point.
4. **FORMAT:** Use bullet points for lists to make it easy to read.

**Your Knowledge Base:**
- **Grid:** The electricity is unpredictable. Focus on "Fast Charging" and "Lifestyle Continuity".
- **Tech:** 314Ah LiFePO4 is the new standard. Lead-Acid is bad. 6kW Inverters are standard.
- **Vendors:** 
  - Cheap: Yoon Electronic, MZO, Ray Electric.
  - Quality: Aether Solar, Alpha Engineering.
  - Commercial: Hla Min Htet, Dyness Myanmar.
- **Prices:** Quote in Myanmar Kyat (Lakhs).

**Decision Logic:**
1. If user lists appliances -> use `estimate_load`.
2. If you have Watts -> use `calculate_system`.
3. If user asks where to buy -> use `get_vendor_recommendation`.
4. If user complains about fuel/diesel -> use `calculate_diesel_savings`.
5. Apartment/Condo -> Assume `no_solar=True`.

**Goal:** Help the user find a safe, reliable solution within budget. Keep it short and in Burmese.
"""

# --- 2. TOOL: APPLIANCE ESTIMATOR ---
def estimate_load(appliances_text: str):
    """
    Parses a string like "1 Aircon, 2 Fans, Fridge" and estimates watts.
    """
    ref = {
        "aircon": 1200, "ac": 1200, "hp": 1200, 
        "fridge": 150, "refrigerator": 150, "freezer": 200,
        "fan": 75, "tv": 100, "light": 20, "bulb": 20, "tube": 20,
        "pump": 750, "water": 750, "motor": 750,
        "cooker": 800, "rice": 800, "pot": 800,
        "wifi": 20, "router": 20, "internet": 20,
        "computer": 200, "laptop": 60, "pc": 200,
        "washing": 500, "washer": 500
    }
    
    total_watts = 0
    text = appliances_text.lower()
    found_items = []
    
    # Simple keyword matching
    for key, watts in ref.items():
        if key in text and key not in found_items:
            # Very basic count handling could go here, but for now we detect presence
            # If user says "2 fans", this simple logic counts it once. 
            # Improvement: Let the LLM handle the count and pass explicit json.
            total_watts += watts
            found_items.append(key)

    # Surge buffer logic for inductive loads
    is_inductive = any(x in text for x in ["aircon", "ac", "fridge", "pump", "motor", "freezer"])
    if is_inductive:
        total_watts = int(total_watts * 1.2) # 20% buffer for startup surge
        note = "Total includes a 20% safety buffer for motor startup surges (Aircon/Fridge)."
    else:
        note = "Standard resistive load estimation."
        
    return {
        "estimated_watts": total_watts,
        "items_detected": ", ".join(found_items),
        "note": note
    }

# --- 3. TOOL: DIESEL ROI CALCULATOR ---
def calculate_diesel_savings(liters_per_day: float):
    """
    Calculates ROI vs Diesel Generator.
    Assumptions: Diesel = 3,500 MMK/Liter (Avg Q1 2025).
    """
    diesel_price = 3500 
    daily_cost = liters_per_day * diesel_price
    monthly_cost = daily_cost * 30
    
    # Baseline comparison: 6kW Hybrid + 16kWh Battery (~85 Lakhs)
    system_cost = 8500000 
    
    months_to_roi = system_cost / monthly_cost if monthly_cost > 0 else 0
    
    return {
        "daily_diesel_cost": f"{int(daily_cost):,} MMK",
        "monthly_burn": f"{int(monthly_cost / 100000)} Lakhs",
        "roi_months": round(months_to_roi, 1),
        "message": f"At {liters_per_day}L/day, you are burning {int(monthly_cost/100000)} Lakhs/month. A battery system pays for itself in {round(months_to_roi, 1)} months."
    }

# --- 4. TOOL: VENDOR RECOMMENDATION ---
def get_vendor_recommendation(intent: str):
    """
    Returns vendors based on user intent: 'cheap', 'quality', 'commercial', 'batteries'.
    """
    intent = intent.lower()
    
    # Map intent to Database Categories
    if any(x in intent for x in ['cheap', 'budget', 'low price', 'wholesale', 'discount']):
        db_cat = 'Aggregator'
    elif any(x in intent for x in ['install', 'quality', 'service', 'premium', 'engineer', 'custom']):
        db_cat = 'Engineering'
    elif any(x in intent for x in ['official', 'brand', 'distributor', 'warranty']):
        db_cat = 'Brand Distributor'
    elif any(x in intent for x in ['factory', 'commercial', 'industry', 'big', 'business']):
        # Special logic for commercial
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT name, specialty FROM vendors WHERE name LIKE '%Hla Min Htet%' OR name LIKE '%Dyness%'")
                rows = cur.fetchall()
        return {"vendors": [{"name": r[0], "specialty": r[1]} for r in rows], "note": "These are specialists for high-voltage commercial projects."}
    else:
        db_cat = 'Aggregator' # Default

    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT name, specialty, known_brands 
                FROM vendors 
                WHERE category = %s 
                LIMIT 4
            """, (db_cat,))
            rows = cur.fetchall()
            
    if not rows:
        return {"message": "I couldn't find specific vendors for that, but general electronics markets are a good start."}
        
    results = []
    for row in rows:
        results.append({
            "shop_name": row[0],
            "specialty": row[1],
            "brands": row[2]
        })
        
    return {
        "category": db_cat,
        "recommendations": results,
        "note": "These are based on Q1 2025 market surveys. Stocks change daily."
    }

# --- 5. TOOL DEFINITIONS (Schema for LLM) ---
tools = [
    {
        "type": "function",
        "function": {
            "name": "calculate_system",
            "description": "Calculate solar/backup system specs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "watts": {"type": "integer"},
                    "hours": {"type": "integer"},
                    "no_solar": {"type": "boolean", "description": "True if user cannot install panels (Apartment/Condo)."}
                },
                "required": ["watts", "hours"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "estimate_load",
            "description": "Estimate watts from appliance list.",
            "parameters": {
                "type": "object",
                "properties": {
                    "appliances_text": {"type": "string", "description": "User's list (e.g., '1 AC, fridge')"}
                },
                "required": ["appliances_text"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_diesel_savings",
            "description": "Calculate savings vs Diesel Generator.",
            "parameters": {
                "type": "object",
                "properties": {
                    "liters_per_day": {"type": "number"}
                },
                "required": ["liters_per_day"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_vendor_recommendation",
            "description": "Find where to buy or specific shops.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {"type": "string", "description": "User intent: 'cheap', 'quality', 'commercial', 'official'"}
                },
                "required": ["intent"]
            }
        }
    }
]

# --- 6. MAIN LOGIC LOOP ---
def process_ai_message(sender_id, user_message):
    # Build Conversation Context
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    history = get_recent_history(sender_id, limit=4)
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    try:
        # First Call to LLM
        response = client.chat.completions.create(
            model="google/gemini-2.5-flash",
            messages=messages,
            tools=tools,
        )

        msg = response.choices[0].message

        # Handle Tool Calls
        if msg.tool_calls:
            tool_call = msg.tool_calls[0]
            fn_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            result_data = {}
            
            # Dispatcher
            if fn_name == "calculate_system":
                # Default hours to 8 if not provided/clear, to force a safe calculation
                hours = args.get("hours", 8) 
                result_data = calculate_system(args["watts"], hours, args.get("no_solar", False))
                
            elif fn_name == "estimate_load":
                result_data = estimate_load(args["appliances_text"])
                
            elif fn_name == "calculate_diesel_savings":
                result_data = calculate_diesel_savings(args["liters_per_day"])
                
            elif fn_name == "get_vendor_recommendation":
                result_data = get_vendor_recommendation(args["intent"])

            # Append Tool Result to History
            messages.append(msg)
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": json.dumps(result_data)
            })
            
            # Second Call to LLM (Generate Natural Response)
            final_res = client.chat.completions.create(
                model="google/gemini-2.5-flash",
                messages=messages
            )
            bot_reply = final_res.choices[0].message.content
        else:
            # No tool used, just conversation
            bot_reply = msg.content

        # Send & Save
        send_to_facebook(sender_id, bot_reply)
        save_chat_log(sender_id, "bot", bot_reply)

    except Exception as e:
        print(f"AI Logic Error: {e}")
        error_msg = "မီးဆရာ ခဏအနားယူနေပါတယ် (Server Error)။ ခဏနေမှ ပြန်ကြိုးစားပေးပါခင်ဗျာ။"
        send_to_facebook(sender_id, error_msg)