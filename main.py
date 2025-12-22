from fastapi import FastAPI, Request, HTTPException
from chat_logic import get_ai_reply
import os
import requests
import uvicorn

app = FastAPI()

# Load env vars
VERIFY_TOKEN = os.environ.get("FACEBOOK_VERIFY_TOKEN")
PAGE_ACCESS_TOKEN = os.environ.get("FACEBOOK_PAGE_ACCESS_TOKEN")

@app.get("/")
def home():
    return {"status": "Myanmar Solar Bot is Active"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Facebook Verification Handshake
    """
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_messages(request: Request):
    """
    Receive messages from Facebook
    """
    data = await request.json()
    
    # Facebook events often come in batches
    entry = data.get("entry", [])
    if entry:
        messaging_events = entry[0].get("messaging", [])
        for event in messaging_events:
            sender_id = event.get("sender", {}).get("id")
            message = event.get("message", {})
            
            if "text" in message:
                user_text = message["text"]
                
                # Get response from AI
                try:
                    bot_response = get_ai_reply(user_text)
                    send_to_facebook(sender_id, bot_response)
                except Exception as e:
                    print(f"Error processing message: {e}")
                    
    return {"status": "ok"}

def send_to_facebook(recipient_id, text):
    """
    Send HTTP POST to Facebook Graph API
    """
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, json=payload)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))