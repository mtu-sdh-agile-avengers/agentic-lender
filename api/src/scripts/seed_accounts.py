"""Script allowing create user account in Firebase Auth AND profile in Cloud Firestore.

NOTE: could be used locally; depending on the .env file RUN_MODE variable value.
"""

import argparse
import asyncio
import json
import requests

from firebase_admin import auth

from src.firebase.connection import init_firebase
from src.auth.enums import Role
from src.config import RunMode, get_config

class NotEnoughCommandLineArgumentsProvided(Exception):
    def __init__(self) -> None:
        super().__init__("AT LEAST TWO arguments required: [email] [password]\n")


# real API key does not required if Firebase emulators suit used
MOCK_API_KEY = "mock-api-key"

# base URLs for Firebase API
LOCAL_BASE_URL = "http://127.0.0.1:9099/identitytoolkit.googleapis.com"
CLOUD_BASE_URL = "https://identitytoolkit.googleapis.com"

# Firebase routes for "Sign up/in with email / password":
ACCOUNT_SIGN_UP_URL = "/v1/accounts:signUp"
ACCOUNT_SIGN_IN_URL = "/v1/accounts:signInWithPassword"

def parse_args() -> argparse.Namespace:  
    p = argparse.ArgumentParser()
    
    p.add_argument("email")
    p.add_argument("password")
    p.add_argument("--role", type=Role, choices=list(Role), default=Role.BORROWER)
    p.add_argument("--api-key", help="Firebase app API KEY, required for \"cloud\"", default=MOCK_API_KEY)
    p.add_argument("--only-sign-in", action="store_true", default=False)
    p.add_argument("--no-firestore-profile", action="store_true", default=False)
    p.add_argument("--full-name")
    p.add_argument("--phone-number")
    p.add_argument("--email-verified", action="store_true", default=False)
    
    args = p.parse_args()
    
    if args.only_sign_in and args.no_firestore_profile:
        p.error("--only-sign-in and --no-firestore-profile can't be used together")
    
    if get_config().run_mode == RunMode.PROD and args.api_key == MOCK_API_KEY:
            p.error("for prod mode --api-key arg (from one of the apps) is required")
    
    return args
    
    
async def create_account(args: argparse.Namespace) -> str:
    from src.auth.gateway import FirebaseAuthGateway
    from src.users.repository import UserProfileFirestoreRepository
    from src.firebase.connection import get_firestore
    from src.users.models import UserProfileModel
    
    # 1. create user ACCOUNT record in Firebase Auth
    user_record = auth.create_user(
        email=args.email,
        password=args.password,
        display_name=args.full_name,
        phone_number=args.phone_number,
        email_verified=args.email_verified,
    )
    
    if not args.no_firestore_profile:
        # 2. set user role custom claim
        await FirebaseAuthGateway().set_user_role(user_record.uid, args.role)
        
        # 3. create user PROFILE record in Firestore
        repo = UserProfileFirestoreRepository(get_firestore())
        await repo.add_user_profile(UserProfileModel(
            uid=user_record.uid,
            email=user_record.email,
            phone=args.phone_number,
            full_name=args.full_name,
            role=args.role,
        ))
    
    return user_record.uid


def sign_in_and_get_token(base_url: str, api_key: str, email: str, password: str) -> dict:
    r = requests.post(
        f"{base_url}{ACCOUNT_SIGN_IN_URL}",
        params={"key": api_key},
        json={"email": email, "password": password, "returnSecureToken": True},
        timeout=10
    )
    
    r.raise_for_status()
    
    return r.json()


def main():
    args = parse_args()
    if not args.only_sign_in:
        init_firebase()
        asyncio.run(create_account(args)) 
    
    base_url = CLOUD_BASE_URL if get_config().run_mode == RunMode.PROD else LOCAL_BASE_URL
    token = sign_in_and_get_token(base_url, args.api_key, args.email, args.password)
    
    print(f"\n{json.dumps(token, indent=4)}")
    
    
if __name__ == "__main__":
    main()