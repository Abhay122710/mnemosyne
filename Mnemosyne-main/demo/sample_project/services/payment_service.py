import requests

class PaymentService:
    def __init__(self, gateway_url: str):
        self.gateway_url = gateway_url

    def process_payment(self, transaction_id: str, amount: float) -> dict:
        """
        Processes payment via payment gateway API.
        """
        response = requests.post(
            f"{self.gateway_url}/charge",
            json={"tx_id": transaction_id, "amount": amount}
        )
        # Unchecked external response payload!
        data = response.json()
        return data["receipt"]["status"]
