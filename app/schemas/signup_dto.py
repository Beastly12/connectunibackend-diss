from pydantic import BaseModel, Field, field_validator, model_validator, EmailStr
from datetime import datetime


class SignUpDto(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr = Field(..., max_length=255)
    password: str = Field(..., min_length=8, max_length=255)
    university_name: str = Field(..., min_length=2, max_length=255)
    graduation_year: int
    major: str = Field(..., min_length=2, max_length=255)
    role: str = Field(default='STUDENT')

    @field_validator('full_name')
    @classmethod
    def name_must_be_real(cls, v):
        if not v.replace(' ', '').isalpha():
            raise ValueError('Full name must only contain letters')
        return v.strip()

    @field_validator('role')
    @classmethod
    def valid_role(cls, v):
        allowed = {'STUDENT', 'MENTOR', 'ALUMNI', 'PROFESSIONAL'}
        if v.upper() not in allowed:
            raise ValueError(f'Role must be one of {allowed}')
        return v.upper()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v):
        if not any(c.isupper() for c in v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.isdigit() for c in v):
            raise ValueError('Password must contain at least one number')
        return v

    @model_validator(mode='after')
    def valid_graduation_year(self):
        current_year = datetime.now().year
        role = self.role.upper() if self.role else 'STUDENT'
        year = self.graduation_year

        if role in ('STUDENT', 'MENTOR'):
            if year < current_year or year > current_year + 6:
                raise ValueError(f'Graduation year must be between {current_year} and {current_year + 6}')
        elif role == 'ALUMNI':
            if year >= current_year:
                raise ValueError(f'Alumni graduation year must be before {current_year}')
        # PROFESSIONAL: any reasonable year accepted

        return self