from pydantic import BaseModel


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: str
    university: str
    grad_year: int
    major: str
    user_role: str

    class Config:
        from_attribute = True

# also fixed typo: was 'from_attribute'