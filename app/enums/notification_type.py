import enum


class NotificationType(str, enum.Enum):
    MESSAGE = "message"
    MENTORSHIP_REQUEST = "mentorship_request"
    MENTORSHIP_ACCEPTED = "mentorship_accepted"
    MENTORSHIP_REJECTED = "mentorship_rejected"
    CONNECTION_REQUEST = "connection_request"
    CONNECTION_ACCEPTED = "connection_accepted"
    EVENT_REMINDER = "event_reminder"
    POST_LIKE = "post_like"
    POST_COMMENT = "post_comment"
    JOB_APPLICATION = "job_application"
