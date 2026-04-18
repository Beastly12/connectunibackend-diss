import enum


class VerificationStatus(str, enum.Enum):
    VERIFIED = "verified"
    PENDING = "pending"
    UNVERIFIED = "unverified"
    SELF_DECLARED = "self_declared"
