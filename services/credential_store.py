"""安全凭据存储 - API Key 加密持久化"""
import json
from pathlib import Path
from services.encryption import AesEncryptionService
from config import CREDENTIALS_PATH


class SecureCredentialStore:
    """安全凭据存储实现"""

    def __init__(self, encryption_service: AesEncryptionService | None = None):
        self._encryption = encryption_service or AesEncryptionService()

    def save_api_key(self, api_key: str):
        """加密并保存 API Key"""
        if not api_key or not api_key.strip():
            raise ValueError("API Key 不能为空")

        encrypted = self._encryption.encrypt(api_key)
        self._save_credentials({"encrypted_api_key": encrypted})

    def get_api_key(self) -> str | None:
        """读取并解密 API Key"""
        creds = self._load_credentials()
        encrypted = creds.get("encrypted_api_key")
        if not encrypted:
            return None
        return self._encryption.try_decrypt(encrypted)

    def clear_api_key(self):
        """清除已存储的 API Key"""
        creds = self._load_credentials()
        creds.pop("encrypted_api_key", None)
        self._save_credentials(creds)

    @property
    def has_api_key(self) -> bool:
        """检查是否已配置 API Key"""
        creds = self._load_credentials()
        encrypted = creds.get("encrypted_api_key")
        if not encrypted:
            return False
        return self._encryption.can_decrypt(encrypted)

    def _load_credentials(self) -> dict:
        if not CREDENTIALS_PATH.exists():
            return {}
        try:
            return json.loads(CREDENTIALS_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}

    def _save_credentials(self, data: dict):
        CREDENTIALS_PATH.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
