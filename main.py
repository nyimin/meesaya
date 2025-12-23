from fastapi import FastAPI, Request, HTTPException, BackgroundTasks
from chat_logic import process_ai_message
from database import save_chat_log
import os
import uvicorn

app = FastAPI()

VERIFY_TOKEN = os.environ.get("FACEBOOK_VERIFY_TOKEN")

@app.get("/")
def home():
    return {"status": "Myanmar Solar Bot Active"}

@app.get("/webhook")
async def verify_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    raise HTTPException(status_code=403, detail="Verification failed")

@app.post("/webhook")
async def handle_messages(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    entry = data.get("entry", [])
    
    if entry:
        messaging_events = entry[0].get("messaging", [])
        for event in messaging_events:
            sender_id = event.get("sender", {}).get("id")
            message = event.get("message", {})
            
            if "text" in message and not message.get("is_echo"):
                user_text = message["text"]
                save_chat_log(sender_id, "user", user_text)
                
                # Critical: Run logic in background to prevent FB Timeout
                background_tasks.add_task(process_ai_message, sender_id, user_text)
                
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))