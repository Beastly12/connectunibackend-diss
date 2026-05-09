import enum


class NotificationType(str, enum.Enum):
    MESSAGE = "message"
    MENTORSHIP_REQUEST = "mentorship_request"
    MENTORSHIP_ACCEPTED = "mentorship_accepted"
    MENTORSHIP_REJECTED = "mentorship_rejected"
    CONNECTION_REQUEST = "connection_request"
    CONNECTION_ACCEPTED = "connection_accepted"
    EVENT_REMINDER = "event_reminder"
    EVENT_RSVP = "event_rsvp"
    POST_LIKE = "post_like"
    POST_COMMENT = "post_comment"
    JOB_APPLICATION = "job_application"
    COMMUNITY_ADDED = "community_added"
    COMMUNITY_MESSAGE = "community_message"
    MESSAGE_REPLY = "message_reply"
    MESSAGE_REACTION = "message_reaction"
    # Mentorship extended notifications
    MILESTONE_COMPLETED = "milestone_completed"
    SESSION_CANCELLED = "session_cancelled"
    SESSION_REMINDER = "session_reminder"
    RESOURCE_SHARED = "resource_shared"
    RELATIONSHIP_ENDED = "relationship_ended"
    MENTEE_CANCELLED_REQUEST = "mentee_cancelled_request"
