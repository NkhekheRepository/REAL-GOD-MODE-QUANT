import os
import requests
import sys

def test_telegram():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    if not token or not chat_id:
        print("ERROR: Missing Telegram credentials")
        return False
        
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': '<b>God Mode Quant Trading Orchestrator</b> test notification',
        'parse_mode': 'HTML'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        result = response.json()
        if result.get('ok'):
            print("SUCCESS: Telegram notification sent")
            return True
        else:
            print(f"ERROR: Telegram API returned: {result}")
            return False
    except Exception as e:
        print(f"ERROR: Failed to send Telegram notification: {e}")
        return False

if __name__ == "__main__":
    success = test_telegram()
    sys.exit(0 if success else 1)
