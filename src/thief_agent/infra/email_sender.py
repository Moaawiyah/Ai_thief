"""Gmail API result delivery with send-only OAuth and safe local draft mode."""

import base64
import json
from email.message import EmailMessage
from pathlib import Path

from thief_agent.exceptions import ProviderCliError
from thief_agent.shared.config import ConfigManager
from thief_agent.shared.gatekeeper import ApiGatekeeper

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

__all__ = ["EmailSender"]


class EmailSender:
    """Create a local draft or send a JSON attachment through Gmail."""

    def __init__(self, config: ConfigManager):
        self._config = config
        self._gatekeeper = ApiGatekeeper(config, service="email")

    def send_report(self, report: dict, subject: str) -> dict:
        """Deliver one report according to ``email.mode``; disabled is the default."""
        if not self._config.get("email.enabled", False):
            return {"sent": False, "reason": "disabled"}
        try:
            message = self._message(report, subject)
            mode = self._config.get("email.mode", "draft")
            if mode in {"draft", "dry-run"}:
                path = self._write_local_draft(message, report)
                return {"sent": False, "mode": mode, "draft_path": str(path)}
            if mode != "send":
                raise ProviderCliError(f"unsupported email mode: {mode}")
            response = self._gatekeeper.execute(self._send_gmail, message)
            return {"sent": True, "mode": "send", "message_id": response.get("id", "")}
        except ProviderCliError as exc:
            return {"sent": False, "reason": str(exc)}

    def _message(self, report: dict, subject: str) -> EmailMessage:
        message = EmailMessage()
        message["To"] = self._config.get("email.recipient")
        message["Subject"] = subject
        message.set_content("Attached is this peer's independently generated match report.")
        payload = json.dumps(report, ensure_ascii=False, indent=2).encode()
        game_id = report.get("game_id", "match")
        message.add_attachment(
            payload,
            maintype="application",
            subtype="json",
            filename=f"result_{game_id}.json",
        )
        return message

    def _write_local_draft(self, message: EmailMessage, report: dict) -> Path:
        outbox = Path(self._config.get("email.outbox_dir", "artifacts/reports"))
        outbox.mkdir(parents=True, exist_ok=True)
        path = outbox / f"result_{report.get('game_id', 'match')}.eml"
        path.write_bytes(message.as_bytes())
        return path

    def _send_gmail(self, message: EmailMessage) -> dict:
        try:
            service = self._build_service()
            raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
            return service.users().messages().send(userId="me", body={"raw": raw}).execute()
        except Exception as exc:
            raise ProviderCliError(f"Gmail API delivery failed: {exc}") from exc

    def _build_service(self):
        """Authorize lazily so normal game startup never touches OAuth files."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build

        credentials_path = Path(self._config.get("email.credentials_file", "credentials.json"))
        token_path = Path(self._config.get("email.token_file", "token.json"))
        credentials = None
        if token_path.exists():
            credentials = Credentials.from_authorized_user_file(token_path, SCOPES)
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        elif not credentials or not credentials.valid:
            if not credentials_path.exists():
                raise ProviderCliError(f"OAuth credentials file not found: {credentials_path}")
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            credentials = flow.run_local_server(port=0)
        token_path.write_text(credentials.to_json(), encoding="utf-8")
        return build("gmail", "v1", credentials=credentials, cache_discovery=False)
