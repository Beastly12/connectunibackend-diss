import enum

class MentorshipStatus(str, enum.Enum):
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    REJECTED = "rejected"
