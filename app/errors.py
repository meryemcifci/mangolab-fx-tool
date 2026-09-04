# API'nin kontrollü hata response modelini tanımladığımız dosya

from fastapi import HTTPException


class FXError(HTTPException):
    def __init__(self, status_code: int, error: str, message: str):
        self.error = error
        self.message = message

        super().__init__(status_code=status_code)