from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    message: str = "Login successful"


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}
