"""Script intended to be used only in dev mode to generate ID and refresh token for the end-user."""

import sys
import requests

class NotEnoughCommandLineArgumentsProvided(Exception):
    def __init__(self) -> None:
        super().__init__("AT LEAST TWO arguments required: [email] [password]\n")


# real API key does not required if Firebase emulators suit used
API_KEY = "mock-api-key"

# Firebase route for "Sign up with email / password" (returns ID and access tokens):
BASE_URL = "http://127.0.0.1:9099"
URL = BASE_URL + "/identitytoolkit.googleapis.com/v1/accounts:signUp"


def main():
    # 0. prepare mock user credentials (CLA)
    if len(sys.argv) < 3:
        raise NotEnoughCommandLineArgumentsProvided()
    
    # e.g. apitesty@gmail.com test12345
    email, password = sys.argv[1], sys.argv[2]
    
    # 1. send request | "returnSecureToken" - option which indicates whether or not to return an ID and refresh token
    r = requests.post(
        URL,
        params={"key": API_KEY},
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=10,
    )
    
    # 2. check if request was succsessful (error raised if not)
    r.raise_for_status()

    # 3. print results in console
    print(f"RESPONSE: {r.json()}\n")
    print(f"ID_TOKEN: {r.json()["idToken"]}\n")
    
if __name__ == "__main__":
    main()