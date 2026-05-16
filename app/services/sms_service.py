"""SMS service using Africa''s Talking"""
import africastalking
from app.config import settings

# Initialize
africastalking.initialize(settings.AT_USERNAME, settings.AT_API_KEY)
sms = africastalking.SMS

def send_sms(phone_numbers: list[str], message: str, sender_id: str = None):
    """Send SMS to list of phone numbers. Returns dict with results."""
    try:
        # Normalize phone numbers to international format
        normalized = []
        for p in phone_numbers:
            p = p.strip().replace(" ", "").replace("-", "")
            if p.startswith("0"):
                p = "+254" + p[1:]
            elif p.startswith("254"):
                p = "+" + p
            elif not p.startswith("+"):
                p = "+254" + p
            normalized.append(p)
        
        sender = sender_id or settings.AT_SENDER_ID
        response = sms.send(message, normalized, sender_id=sender)
        return {"success": True, "response": response}
    except Exception as e:
        return {"success": False, "error": str(e)}
