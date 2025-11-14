import os
import json
from typing import Optional

_cached = {
    'client': None,
    'error': None,
}

def get_firestore_client() -> Optional["firestore.Client"]:
    """Return a cached Firestore client or None if not configured.
    Reads service account JSON from FIREBASE_CRED_JSON and optional
    FIREBASE_PROJECT_ID. Does not raise on failure; records error for debugging.
    """
    if _cached['client'] is not None:
        return _cached['client']
    if _cached['error'] is not None:
        return None

    raw = os.environ.get('FIREBASE_CRED_JSON')
    if not raw:
        _cached['error'] = 'FIREBASE_CRED_JSON not set'
        return None

    try:
        from google.oauth2 import service_account
        from google.cloud import firestore  # type: ignore
    except Exception as exc:  # pragma: no cover
        _cached['error'] = f'google-cloud-firestore not available: {exc}'
        return None

    try:
        info = json.loads(raw)
        creds = service_account.Credentials.from_service_account_info(info)
        project_id = os.environ.get('FIREBASE_PROJECT_ID') or info.get('project_id')
        if not project_id:
            _cached['error'] = 'FIREBASE_PROJECT_ID not provided and missing in service account JSON'
            return None
        client = firestore.Client(project=project_id, credentials=creds)
        _cached['client'] = client
        return client
    except Exception as exc:  # pragma: no cover
        _cached['error'] = f'Failed to init Firestore: {exc}'
        return None


def firebase_enabled() -> bool:
    return os.environ.get('FIREBASE_ENABLED', 'false').lower() in ('1', 'true', 'yes')
