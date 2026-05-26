from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class ModelConfigCryptoError(ValueError):
    """Raised when model API key encryption cannot be performed safely."""


class ModelConfigCrypto:
    """Encrypt and decrypt model provider API keys with a service-owned secret."""

    def __init__(self, key: str | bytes | None) -> None:
        if isinstance(key, str):
            key = key.strip().encode("utf-8")
        if not key:
            raise ModelConfigCryptoError("MODEL_CONFIG_ENCRYPTION_KEY is required")
        try:
            self._fernet = Fernet(key)
        except (TypeError, ValueError) as exc:
            raise ModelConfigCryptoError("MODEL_CONFIG_ENCRYPTION_KEY is invalid") from exc

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def encrypt(self, plaintext: str) -> str:
        if not plaintext:
            raise ModelConfigCryptoError("model API key must not be empty")
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, encrypted: str) -> str:
        if not encrypted:
            raise ModelConfigCryptoError("encrypted model API key is empty")
        try:
            return self._fernet.decrypt(encrypted.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ModelConfigCryptoError("encrypted model API key cannot be decrypted") from exc
