from enum import Enum

class UserRole(str, Enum):
    STUDENT = "STUDENT"
    ALUMNI = "ALUMNI"
    MENTOR = "MENTOR"
    STAFF = "STAFF"
    ADMIN = "ADMIN"
    PROFESSIONAL = "PROFESSIONAL"
