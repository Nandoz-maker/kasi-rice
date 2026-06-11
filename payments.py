import uuid
import logging

# Configure logger output formatting
logging.basicConfig(level=logging.INFO)

class YoUgandaProvider:
    def __init__(self, username=None, password=None, sandbox_mode=True):
        self.username = username
        self.password = password
        self.sandbox_mode = sandbox_mode

    def initiate_mobile_money_pull(self, phone_number, amount, order_id):
        """
        Simulates an API request to Yo! Payments for an Instant Mobile Money Pull (STK Push).
        """
        # Clean phone formatting (Yo! expects 2567xxxxxxxx standard)
        cleaned_phone = phone_number.replace("+", "").strip()
        if cleaned_phone.startswith("0"):
            cleaned_phone = "256" + cleaned_phone[1:]
            
        logging.info(f"[YO! PAYMENTS AUTOMATION] Pull request executed for Order #{order_id} targeting {cleaned_phone} - UGX {amount}")
        
        # --- MOCK AUTOMATION RESPONSE MATRIX ---
        # In live integration, you parse Yo's XML wrapper responses here
        if "700000000" in cleaned_phone:  # Simulating a mock test failure case
            return {
                "status": "error",
                "transaction_reference": None,
                "message": "Transaction declined by subscriber or insufficient wallet funds."
            }
            
        return {
            "status": "success",
            "transaction_reference": f"YO-REF-{uuid.uuid4().hex[:12].upper()}",
            "message": "Instant payment request push initialization accepted successfully."
        }

    def process_visa_charge(self, card_name, card_number, card_expiry, card_cvv, amount, order_id):
        """
        Simulates background cryptographic payload transit to a payment gateway endpoint.
        """
        # Mask the card safely for log files (PCI Compliance)
        masked_card = f"•••• •••• •••• {card_number[-4:] if len(card_number) >= 4 else 'XXXX'}"
        logging.info(f"[VISA SECURE GATEWAY] Direct Charge Payload sent for Order #{order_id} | Name: {card_name} | Card: {masked_card} - UGX {amount}")
        
        # --- MOCK AUTOMATION CARD RESPONSE MATRIX ---
        if card_cvv == "000":  # Simulating a failed authorization rule
            return {
                "status": "error",
                "transaction_reference": None,
                "message": "Card authorization failed: Invalid security verification code (CVV)."
            }
            
        return {
            "status": "success",
            "transaction_reference": f"VS-REF-{uuid.uuid4().hex[:12].upper()}",
            "message": "Visa account validation cleared and funds captured successfully."
        }