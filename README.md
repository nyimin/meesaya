# MeeSaya (မီးဆရာ) - Myanmar Energy Consultant Bot 🇲🇲

**MeeSaya** is an intelligent Facebook Messenger chatbot designed to help Myanmar households and businesses navigate the energy crisis of Q4 2025.

Unlike generic solar calculators, MeeSaya is built on **Hyper-Local Market Intelligence**. It understands that the power grid is unpredictable, that "Yangon Apartments" cannot install solar panels, and that the market has standardized on specific hardware (e.g., 6kW Inverters + 314Ah LiFePO4 Batteries).

## 🚀 Key Features

### 1. Market-Aware Engineering ("Snap-to-Market")
*   **No Theoretical Math:** If the physics says you need a 4.2kW inverter, the bot won't recommend a phantom product. It "snaps" to the nearest **real market standard** (e.g., a 5kW Felicity or 6kW Growatt) found in the database.
*   **Price Accuracy:** Quotes estimates based on real Q1 2025 street prices in Myanmar (in Lakhs).

### 2. "Yangon Apartment" Mode
*   **Fast Charging Logic:** If a user lives in a condo (No Solar), the bot prioritizes **AC Charging Speed** (Amps) over inverter output. It calculates if the system can refill batteries during a short 3-4 hour grid window.
*   **Safety First:** Only recommends LiFePO4 cabinets safe for indoor use.

### 3. Diesel ROI Calculator ("The Diesel Killer")
*   For businesses, the bot calculates the financial burn of running a diesel generator vs. buying a battery system.
*   **Input:** Liters of diesel per day.
*   **Output:** Payback period in months (usually <6 months).

### 4. Distinct Persona
*   **Identity:** Male Myanmar engineer ("Saya").
*   **Tone:** Empathetic to power outages, humble about brands (never claims to know everything), and mirrors user sarcasm playfully.
*   **Brand Awareness:** Knows specific local vendors (Yoon, MZO, Aether, etc.) and categories (Cash & Carry vs. Engineering).

---

## 🛠 Tech Stack

*   **Language:** Python 3.10+
*   **Framework:** FastAPI (High-performance Async API)
*   **Database:** PostgreSQL (via `psycopg2`)
*   **AI Engine:** OpenAI / Google Gemini (via OpenRouter API)
*   **Platform:** Facebook Graph API (Messenger Webhook)

---

## 📂 Project Structure

```text
├── main.py              # FastAPI entry point & Webhook handler
├── chat_logic.py        # The Brain: Persona, Tool Orchestration, LLM interaction
├── calculator.py        # The Engineer: Physics, Market Snapping, Voltage Logic
├── database.py          # DB Connection Pooling & Chat History methods
├── init_db.py           # Seeding Script: Loads Q1 2025 Market Survey Data
├── requirements.txt     # Python dependencies
├── Procfile             # Deployment command (Railway/Heroku)
└── .env                 # Environment variables (API Keys, DB URL)
```

---

## ⚙️ Installation & Setup

### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/meesaya.git
cd meesaya
```

### 2. Set Up Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory:
```env
OPENROUTER_API_KEY=your_key_here
FACEBOOK_PAGE_ACCESS_TOKEN=your_fb_token
FACEBOOK_VERIFY_TOKEN=my_secret_verify_token
DATABASE_URL=postgresql://user:pass@localhost:5432/meesaya_db
ADMIN_FB_ID=1234567890
PORT=8000
```

### 5. Initialize the Database
**Crucial Step:** This script drops old tables and hydrates the DB with the comprehensive Q1 2025 market survey (314Ah batteries, High Voltage Stacks, specific Vendor lists).
```bash
python init_db.py
```
*Output should confirm: `✅ Database Fully Hydrated with Comprehensive Survey Data.`*

### 6. Run the Server
```bash
uvicorn main:app --reload
```
The server will start at `http://localhost:8000`.

---

## 🧠 Logic Deep Dive

### The "Unpredictable Grid" Algorithm (`calculator.py`)
Standard calculators size solar panels to cover daily usage. MeeSaya assumes the grid might fail for 20 hours.
*   **Formula:** `Total_Need / 4 Hours Sun`
*   **Result:** It aggressively oversizes the solar array to ensure the battery charges fully in the short "Rapid Recovery" window.

### The "Snap-to-Market" Logic
1.  **Calculate Raw Need:** e.g., 3800 Watts.
2.  **Database Query:** Find `products_inverters` where `watts >= 3800` ORDER BY `price`.
3.  **Result:** Returns a specific **5000W** model.
4.  **User Output:** "I recommend the Felicity 5kW because it is the standard market size."

---

## 💬 Usage Examples

**User:** "I have one aircon and a fridge. Lights go out for 4 hours."
**MeeSaya:** Detects Aircon -> Defaults to **48V System**. Checks database for "Standard 6kW Package". Recommends 6kW Inverter + 15kWh Battery.

**User:** "I live in a Condo in Sanchaung."
**MeeSaya:** Sets `no_solar=True`. Calculates load. Checks `max_ac_charge_amps` in DB. Recommends a high-amp inverter cabinet that charges in 2 hours.

**User:** "My generator uses 5 gallons a day."
**MeeSaya:** Runs `calculate_diesel_savings`. Tells user they are burning ~20 Lakhs/month and suggests a system with a 4-month ROI.

---

## 🤝 Contributing

1.  Fork the repo.
2.  Update `init_db.py` if market prices change (e.g., Exchange rate fluctuation).
3.  Submit a Pull Request.

---

## 📜 License

MIT License. Copyright © 2025.