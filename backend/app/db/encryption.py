"""
暗号化・復号化ユーティリティ
"""
from cryptography.fernet import Fernet
import os

class EncryptionManager:
    """パスワード暗号化管理"""
    
    # TODO: 本番環境では環境変数から取得
    KEY_FILE = os.path.join(os.path.dirname(__file__), '.crypto_key')
    
    @classmethod
    def _get_key(cls) -> bytes:
        """暗号化キーを取得"""
        if os.path.exists(cls.KEY_FILE):
            with open(cls.KEY_FILE, 'rb') as f:
                return f.read()
        else:
            # キーを生成して保存
            key = Fernet.generate_key()
            os.makedirs(os.path.dirname(cls.KEY_FILE), exist_ok=True)
            with open(cls.KEY_FILE, 'wb') as f:
                f.write(key)
            return key
    
    @classmethod
    def encrypt(cls, plain_text: str) -> str:
        """テキスト暗号化"""
        key = cls._get_key()
        cipher = Fernet(key)
        encrypted = cipher.encrypt(plain_text.encode())
        return encrypted.decode()
    
    @classmethod
    def decrypt(cls, encrypted_text: str) -> str:
        """テキスト復号化"""
        key = cls._get_key()
        cipher = Fernet(key)
        decrypted = cipher.decrypt(encrypted_text.encode())
        return decrypted.decode()
