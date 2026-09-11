"""Centralized ServiceNow connection resolver.

Both task execution and dynamic-choice handlers use this to build a
ServiceNowConnectionHandler from either an InputFields instance or a raw
dynamic-choice fields dict.
"""

import logging
from typing import Union

from utility.connection_servicenow import ServiceNowConnectionHandler

logger = logging.getLogger("UNV")


def resolve_sn_connection(
    url: str,
    credential: Union[dict, object],
) -> ServiceNowConnectionHandler:
    """Create a ServiceNowConnectionHandler from a URL and credential.

    Args:
        url: ServiceNow instance base URL (must start with https://)
        credential: Dict with 'user'/'password' keys, or a Credential dataclass instance

    Returns:
        Authenticated ServiceNowConnectionHandler

    Raises:
        ValueError: With actionable message naming the missing field/key
    """
    if not url or not str(url).strip():
        raise ValueError("ServiceNow Instance URL is required")
    url = str(url).strip().rstrip("/")
    if not url.startswith("https://"):
        raise ValueError("ServiceNow Instance URL must start with https://")

    if isinstance(credential, dict):
        user = (credential.get("user") or "").strip()
        password = (credential.get("password") or "").strip()
        cred_keys = list(credential.keys())
    elif hasattr(credential, "user"):
        user = (credential.user or "").strip()
        password = (credential.password or "").strip()
        cred_keys = [k for k in ("user", "password", "token") if getattr(credential, k, None)]
    else:
        raise ValueError("ServiceNow Credential must be a resolved Credential object")

    if not user:
        raise ValueError("ServiceNow Credential is missing Runtime User")
    if not password:
        raise ValueError("ServiceNow Credential is missing Runtime Password")

    host = url.split("//")[-1].split("/")[0]
    logger.debug("Resolving SN connection: host=%s, credential_keys=%s", host, cred_keys)

    return ServiceNowConnectionHandler(url, user, password)


def resolve_sn_connection_from_fields(fields: dict) -> ServiceNowConnectionHandler:
    """Create a ServiceNowConnectionHandler from a raw dynamic-choice fields dict.

    The credential may arrive as a nested dict (UAC delivers Credential fields
    as dicts to dynamic-choice handlers) or as flattened dotted keys.

    Args:
        fields: Raw fields dict from UAC dynamic-choice call

    Returns:
        Authenticated ServiceNowConnectionHandler

    Raises:
        ValueError: With actionable message naming the missing field/key
    """
    sn_url = fields.get("servicenow_instance_url")
    if isinstance(sn_url, list) and sn_url:
        sn_url = sn_url[0]

    cred = fields.get("servicenow_credential")
    if isinstance(cred, dict):
        credential = cred
    elif cred is not None and hasattr(cred, "user"):
        credential = cred
    else:
        # Fallback: read flattened dotted keys
        user = fields.get("servicenow_credential.user") or ""
        password = fields.get("servicenow_credential.password") or ""
        credential = {"user": user, "password": password}

    return resolve_sn_connection(sn_url, credential)
