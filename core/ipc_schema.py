from pydantic import BaseModel, Field
from typing import Optional, Literal


class HashRequest(BaseModel):
    cmd: Literal["hash"] = "hash"
    data: str = Field(..., description="Hex-encoded bytes")
    algorithm: str = "sha256"


class EncryptRequest(BaseModel):
    cmd: Literal["encrypt"] = "encrypt"
    data: str = Field(..., description="Hex-encoded bytes")
    key: str = Field(..., description="Base64-encoded key")
    algorithm: str = "aes-256-gcm"


class IPCResponse(BaseModel):
    result: Optional[str] = None
    error: Optional[str] = None
