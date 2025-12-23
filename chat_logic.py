import os
import json
import requests
from database import save_chat_log, get_recent_history
from calculator import calculate_system

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ADMIN_FB_ID = os.environ.get("ADMIN_FB_ID")
FB_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")

# --- YOUR PERSONA DEFINITION ---
PERSONA_DEFINITION = """
You are "MeeSaya" (မီးဆရာ), a wise, practical, and friendly male Myanmar Energy Consultant. Think of yourself as the knowledgeable engineer at a local tea shop – experienced, honest, and a little bit of a personality.

**Your Personality & Tone:**
- **Male Persona:** Use natural male-gendered phrasing (e.g., "My friend," "I've seen this," "Let me tell you", "Khinya").
- **Empathetic:** Acknowledge the frustration of the current unpredictable outages (Mee Pyat).
- **Sarcasm Mirroring:** If the user uses light sarcasm, mirror it back playfully.
- **Brand Humility:** When suggesting brands (Growatt, Deye, Shark Topsun, Jinko), always frame it as "one of the better options" or "popular choice." Never claim to know everything.

**Your Knowledge Base (Q1 2025 Market Survey):**
- **Grid Reality:** The grid is UNPREDICTABLE. Prioritize "Fast Charging" (High Amps) and "Lifestyle Continuity."
- **Technology:** 
  - **314Ah LiFePO4** is the new standard for homes (replaces 280Ah).
  - **Lead-Acid** is obsolete and a waste of money.
  - **6kW Inverters** are standard because they charge batteries fast (100A+).
- **Vendors:** 
  - "Cheap/Cash & Carry": Yoon Electronic, MZO, Ray Electric.
  - "Quality/Installation": Aether Solar, Alpha Engineering.
  - "Commercial/Factory": Hla Min Htet, Dyness Myanmar.
- **Prices:** Quote in Myanmar Kyat (Lakhs).

**Decision Logic:**
1. **System Sizing:** If the user gives appliances/watts, output the JSON tool.
2. **Apartments:** If user is in a Condo/Apartment, assume `no_solar=True` and focus on "Fast Grid Charging".
"""

# --- INSTRUCTIONS TO FORCE BURMESE & TOOL USE ---
SYSTEM_INSTRUCTIONS = """
**CRITICAL OUTPUT RULES:**
1. **LANGUAGE:** You must reply in **Myanmar Language (Burmese)**. You may use English for technical specs (e.g., kW, Inverter, Volt).
2. **CONCISENESS:** Keep answers short, direct, and helpful.
3. **TOOL USAGE:** 
   If the user describes a load (e.g., "1 fridge, 2 lights" or "500W"), DO NOT calculate it yourself.
   Output a JSON object strictly in this format:
   {"tool": "calculate", "watts": 500, "hours": 4, "no_solar": false}
   
   *Note: If the user mentions "Condo", "Apartment", or "Room", set "no_solar": true.*
"""

FINAL_SYSTEM_PROMPT = PERSONA_DEFINITION + "\n" + SYSTEM_INSTRUCTIONS

def send_fb_message(recipient_id, text):
    """Sends a message back to Facebook Messenger."""
    params = {"access_token": FB_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    try:
        r = requests.post("https://graph.facebook.com/v19.0/me/messages", params=params, headers=headers, json=data)
        if r.status_code != 200:
            print(f"Error sending FB message: {r.text}")
    except Exception as e:
        print(f"Connection error sending FB message: {e}")

def process_ai_message(sender_id, user_text):
    """
    1. Retrieve History
    2. Call LLM with Persona
    3. Check for Tool Use (Calculator)
    4. Save & Reply
    """
    
    # 1. Get Context
    history = get_recent_history(sender_id, limit=6)
    
    system_message = {"role": "system", "content": FINAL_SYSTEM_PROMPT}
    messages = [system_message] + history + [{"role": "user", "content": user_text}]

    # 2. Call LLM
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "HTTP-Referer": "https://meesaya.com", 
            },
            json={
                "model": "openai/gpt-3.5-turbo", # Cost effective, good at following persona
                "messages": messages,
                "temperature": 0.7 
            }
        )
        result = response.json()
        
        if 'choices' not in result:
            print(f"LLM Error: {result}")
            raise ValueError("Invalid LLM Response")

        ai_content = result['choices'][0]['message']['content']
        reply_text = ai_content 
        
        # 3. Check for Tool Trigger
        if "{" in ai_content and "calculate" in ai_content:
            try:
                # Extract JSON cleanly
                start = ai_content.find("{")
                end = ai_content.rfind("}") + 1
                json_str = ai_content[start:end]
                data = json.loads(json_str)
                
                if data.get("tool") == "calculate":
                    # --- EXECUTE PYTHON CALCULATION ---
                    calc_result = calculate_system(data['watts'], data['hours'], data.get('no_solar', False))
                    
                    specs = calc_result['system_specs']
                    ests = calc_result['estimates']
                    
                    # --- ENGINEER'S QUOTE (IN BURMESE) ---
                    reply_text = (
                        f"မီးဆရာရဲ့ တွက်ချက်မှုအရ အစ်ကို့အတွက် အသင့်တော်ဆုံး System ကတော့ -\n\n"
                        f"🔌 System: {specs['system_voltage']}V Architecture\n"
                        f"⚡ Inverter: {specs['inverter']} ({specs['inverter_size_kw']}kW)\n"
                        f"🔋 Battery: {specs['battery_qty']} လုံး x {specs['battery_model']} (စုစုပေါင်း {specs['total_storage_kwh']}kWh)\n"
                    )
                    
                    if specs['solar_panels_count'] > 0:
                        reply_text += f"☀️ Solar: {specs['solar_panels_count']} ချပ်\n"
                    
                    reply_text += (
                        f"\n💰 ခန့်မှန်းကုန်ကျစရိတ်: {ests['total_estimated']:,} ကျပ်\n"
                        f"(စက်ပစ္စည်း၊ လက်ခ၊ ကြိုး၊ မီးပုံး အပြီးအစီး ခန့်မှန်းဈေးဖြစ်ပါတယ်ခင်ဗျ)"
                    )
                    
            except Exception as e:
                print(f"Tool parse error: {e}")
                reply_text = "မီးသုံးစွဲမှု တွက်ချက်ရာမှာ Error ဖြစ်သွားလို့ ပမာဏအတိအကျ (Watts) နဲ့ ပြန်ပြောပေးပါခင်ဗျာ။"
        
        # 4. Save AI Response (Memory)
        save_chat_log(sender_id, "assistant", reply_text)
        
        # 5. Send Final Reply
        send_fb_message(sender_id, reply_text)

    except Exception as e:
        print(f"Critical AI Error: {e}")
        error_msg = "System error ဖြစ်နေလို့ ခဏနေမှ ပြန်မေးပေးပါခင်ဗျာ။ 🙏"
        send_fb_message(sender_id, error_msg)