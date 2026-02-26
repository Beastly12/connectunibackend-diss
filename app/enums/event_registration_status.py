import enum


class EventRegistrationStatus(str, enum.Enum):
    REGISTERED = "registered"
    ATTENDED = "attended"
    CANCELLED = "cancelled"
