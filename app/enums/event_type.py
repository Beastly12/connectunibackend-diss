import enum


class EventType(str, enum.Enum):
    ACADEMIC = "academic"
    SOCIAL = "social"
    CAREER = "career"
    NETWORKING = "networking"