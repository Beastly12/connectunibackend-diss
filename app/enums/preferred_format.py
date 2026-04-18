import enum


class PreferredFormat(str, enum.Enum):
    CHAT = "chat"
    VIDEO = "video"
    IN_PERSON = "in_person"
