from pydantic import BaseModel, EmailStr, Field, field_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    age: int = Field(ge=1, le=120)
    gender: str
    phone: str = Field(min_length=10, max_length=15)

    @field_validator("gender")
    @classmethod
    def _gender(cls, v: str) -> str:
        allowed = {"female", "male", "other"}
        if v.strip().lower() not in allowed:
            raise ValueError("gender must be female, male, or other")
        return v.strip().lower()

    @field_validator("phone")
    @classmethod
    def _phone(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("phone must be digits only")
        return v


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: int
    email: str
    is_admin: bool
