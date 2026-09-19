import requests

class UserService:
    def __init__(self, api_url: str):
        self.api_url = api_url

    def fetch_user_profile(self, user_id: str) -> dict:
        """
        [FIXED BUG]
        Previously directly accessed response.json()["data"]["profile"] without
        verifying response status or checking if response.json() had a "data" key.
        Fix applied: Validate HTTP 200 and safe nested get().
        """
        response = requests.get(f"{self.api_url}/users/{user_id}")
        if response.status_code != 200:
            return {}
        
        payload = response.json()
        if not payload or "data" not in payload:
            return {}
            
        return payload.get("data", {}).get("profile", {})
