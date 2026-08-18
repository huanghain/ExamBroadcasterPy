"""
AES-256-CBC 加密服务

与 .NET 版本使用完全相同的算法：
- AES-256-CBC + PKCS7 填充
- PBKDF2-SHA256 密钥派生 (600,000 次迭代)
- 输出格式: Base64(Salt[16B] + IV[16B] + CipherText)
- 密钥与机器特征绑定（Windows: MachineName+UserName, 其他: hostname+username）
"""
import os
import platform
import hashlib
import base64
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding as sym_padding
from cryptography.hazmat.backends import default_backend

from config import FIXED_SEED, PBKDF2_ITERATIONS, SALT_SIZE, IV_SIZE, KEY_SIZE


class AesEncryptionService:
    """AES-256-CBC 加密/解密服务"""

    @staticmethod
    def _get_machine_entropy() -> bytes:
        """获取机器特征熵"""
        try:
            username = os.getlogin()
        except OSError:
            # 某些环境（如容器/SSH）getlogin() 会失败，使用环境变量兜底
            username = os.environ.get("USER") or os.environ.get("USERNAME") or "unknown"
        machine_info = f"{platform.node()}|{username}|ExamBroadcaster"
        return machine_info.encode("utf-8")

    @staticmethod
    def _derive_salt() -> bytes:
        """派生 Salt（混合机器特征 + 固定种子）"""
        machine_entropy = AesEncryptionService._get_machine_entropy()
        combined = machine_entropy + FIXED_SEED
        return hashlib.sha256(combined).digest()

    @staticmethod
    def _derive_key(salt: bytes) -> bytes:
        """使用 PBKDF2-SHA256 派生 AES 密钥"""
        return hashlib.pbkdf2_hmac(
            "sha256",
            FIXED_SEED,
            salt,
            PBKDF2_ITERATIONS,
            dklen=KEY_SIZE,
        )

    def encrypt(self, plain_text: str) -> str:
        """
        AES-256-CBC 加密

        Args:
            plain_text: 待加密明文

        Returns:
            Base64 编码的密文 (Salt + IV + CipherText)
        """
        if not plain_text or not plain_text.strip():
            raise ValueError("明文不能为空")

        # 1. 生成随机 Salt 和 IV
        salt = os.urandom(SALT_SIZE)
        iv = os.urandom(IV_SIZE)

        # 2. 派生密钥
        key = self._derive_key(salt)

        # 3. PKCS7 填充
        padder = sym_padding.PKCS7(128).padder()
        padded = padder.update(plain_text.encode("utf-8")) + padder.finalize()

        # 4. AES-256-CBC 加密
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        encryptor = cipher.encryptor()
        ciphertext = encryptor.update(padded) + encryptor.finalize()

        # 5. 组装: Salt + IV + CipherText → Base64
        result = salt + iv + ciphertext
        return base64.b64encode(result).decode("utf-8")

    def decrypt(self, encrypted_base64: str) -> str:
        """
        AES-256-CBC 解密

        Args:
            encrypted_base64: Base64 编码的密文

        Returns:
            解密后的明文

        Raises:
            ValueError: 数据格式无效
            RuntimeError: 解密失败（密钥不匹配或数据损坏）
        """
        if not encrypted_base64 or not encrypted_base64.strip():
            raise ValueError("密文不能为空")

        try:
            full_bytes = base64.b64decode(encrypted_base64)
        except Exception as e:
            raise ValueError(f"加密数据格式无效（非 Base64 编码）: {e}")

        min_size = SALT_SIZE + IV_SIZE + 16
        if len(full_bytes) < min_size:
            raise ValueError(
                f"加密数据长度不足（期望 >= {min_size} 字节，实际 {len(full_bytes)} 字节）"
            )

        # 1. 提取 Salt, IV, CipherText
        salt = full_bytes[:SALT_SIZE]
        iv = full_bytes[SALT_SIZE : SALT_SIZE + IV_SIZE]
        ciphertext = full_bytes[SALT_SIZE + IV_SIZE :]

        # 2. 派生密钥
        key = self._derive_key(salt)

        # 3. AES-256-CBC 解密
        try:
            cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
            decryptor = cipher.decryptor()
            padded_plain = decryptor.update(ciphertext) + decryptor.finalize()

            # 4. PKCS7 去填充
            unpadder = sym_padding.PKCS7(128).unpadder()
            plain_bytes = unpadder.update(padded_plain) + unpadder.finalize()

            return plain_bytes.decode("utf-8")
        except Exception as e:
            raise RuntimeError(
                f"解密失败：数据可能已损坏，或当前机器/用户与加密时不同。原始错误: {e}"
            )

    def try_decrypt(self, encrypted_base64: str) -> str | None:
        """尝试解密，失败返回 None"""
        try:
            return self.decrypt(encrypted_base64)
        except Exception:
            return None

    def can_decrypt(self, encrypted_base64: str) -> bool:
        """检查是否能成功解密"""
        return self.try_decrypt(encrypted_base64) is not None
