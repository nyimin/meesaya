import os
import json
import requests
from database import save_chat_log, get_recent_history
from calculator import calculate_system

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
ADMIN_FB_ID = os.environ.get("ADMIN_FB_ID")
FB_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")

def send_fb_message(recipient_id, text):
    """Sends a message back to Facebook Messenger."""
    params = {"access_token": FB_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    r = requests.post("https://graph.facebook.com/v19.0/me/messages", params=params, headers=headers, json=data)
    if r.status_code != 200:
        print(f"Error sending FB message: {r.text}")

def process_ai_message(sender_id, user_text):
    """
    1. Retrieve History
    2. Check for Tool Use (Calculator)
    3. Call LLM
    4. Save Response
    5. Reply to User
    """
    
    # 1. Get Context
    history = get_recent_history(sender_id, limit=6)
    
    # System Persona
    system_prompt = {
        "role": "system", 
        "content": """You are MeeSaya, a Myanmar Energy Engineer. 
        You speak in a mix of English and Myanmar (Burmese).
        You help people calculate solar/battery needs.
        
        If the user gives Watts and Hours (e.g. "500W for 4 hours"), output a JSON strictly in this format:
        {"tool": "calculate", "watts": 500, "hours": 4, "no_solar": false}
        
        Otherwise, reply conversationally. Be helpful, humble, and realistic about the grid."""
    }
    
    messages = [system_prompt] + history + [{"role": "user", "content": user_text}]

    # 2. Call LLM (OpenRouter/OpenAI)
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"},
            json={
                "model": "openai/gpt-3.5-turbo", # Or gemini-pro
                "messages": messages
            }
        )
        result = response.json()
        ai_content = result['choices'][0]['message']['content']
        
        # 3. Check for JSON/Tool usage
        reply_text = ai_content
        
        if "{" in ai_content and "calculate" in ai_content:
            try:
                # Extract JSON if mixed with text
                start = ai_content.find("{")
                end = ai_content.rfind("}") + 1
                json_str = ai_content[start:end]
                data = json.loads(json_str)
                
                if data.get("tool") == "calculate":
                    calc_result = calculate_system(data['watts'], data['hours'], data.get('no_solar', False))
                    
                    # Formulate Engineer's Reply
                    specs = calc_result['system_specs']
                    ests = calc_result['estimates']
                    
                    reply_text = (
                        f"Based on your load, here is my engineering recommendation:\n\n"
                        f"🔌 System: {specs['system_voltage']}V Architecture\n"
                        f"⚡ Inverter: {specs['inverter']} ({specs['inverter_size_kw']}kW)\n"
                        f"🔋 Battery: {specs['battery_qty']}x {specs['battery_model']} (Total {specs['total_storage_kwh']}kWh)\n"
                        f"☀️ Solar: {specs['solar_panels_count']} Panels\n\n"
                        f"💰 Estimated Total: {ests['total_estimated']:,} MMK\n"
                        f"(Includes installation & accessories)"
                    )
            except Exception as e:
                print(f"Tool parse error: {e}")
                # Fallback to raw message if parsing fails
        
        # 4. SAVE AI RESPONSE (Crucial for Memory)
        save_chat_log(sender_id, "assistant", reply_text)
        
        # 5. Send to FB
        send_fb_message(sender_id, reply_text)

    except Exception as e:
        print(f"AI Error: {e}")
        send_fb_message(sender_id, "Sorry, my calculator is overheating. Please try again.")