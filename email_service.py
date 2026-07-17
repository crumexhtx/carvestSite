import html
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def send_report_ready_email(
    *,
    recipient: Optional[str],
    vehicle_name: str,
    report_url: str,
) -> bool:
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    sender = os.environ.get("REPORT_EMAIL_FROM", "Carvest <reports@carvest.example>").strip()
    if not api_key or not recipient:
        return False

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": sender,
                "to": [recipient],
                "subject": f"Your Carvest report for {vehicle_name}",
                "html": (
                    "<h1>Your buyer report is ready</h1>"
                    f"<p>Review the reliability, recalls, market price, and negotiation plan for "
                    f"<strong>{html.escape(vehicle_name)}</strong>.</p>"
                    f'<p><a href="{html.escape(report_url)}">Open your Carvest report</a></p>'
                ),
            },
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.warning("Failed to send report-ready email: %s", exc)
        return False

    if not response.ok:
        logger.warning(
            "Report-ready email provider returned %s: %s",
            response.status_code,
            response.text[:300],
        )
    return response.ok
