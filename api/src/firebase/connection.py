from src.config import config # or dotenv with os could be used

import firebase_admin
from firebase_admin import credentials, firestore
from firebase_admin.exceptions import FirebaseError
from google.cloud.firestore import Client

from loguru import logger


async def init_firebase() -> firebase_admin.App:
    """Initializes Firebase Admin SDK by using private service account key
    (i.e., fetching Google Application Default Credentials from os.environ => app config).
    
    Returns:
        None: void function

    Raises:
        FileNotFoundError: if private service account key .JSON file was not found.
    """
    try:
        cred = credentials.Certificate(config.google_application_credentials)
        app = firebase_admin.initialize_app(cred)
        logger.success("Firebase initialized successfully!")
    except FileNotFoundError:
        logger.error("Service account key .JSON file not found")
        raise
    return app

async def get_firestore(app: firebase_admin.App) -> Client:
    """Returns a Firestore object allowing to interact with with Google Cloud Firestore 

    Args:
        app (firebase_admin.App): Firebase Admin SDK app

    Returns:
        Client: Firestore client object 
    """
    return firestore.client(app)
