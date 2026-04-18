# ConnectUni API Reference

Base URL: `http://localhost:8000`
Interactive docs: `http://localhost:8000/docs`

---

## Authentication

All protected endpoints require a Bearer token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

Access tokens expire in **15 minutes**. Use the refresh token to obtain a new one without re-logging in.

---

## 1. Auth `/auth`

### Register
```
POST /auth/register
```
**Body (JSON)**
| Field | Type | Rules |
|---|---|---|
| `full_name` | string | Letters only, 2–255 chars |
| `email` | string | Valid email, unique |
| `password` | string | 8–255 chars, ≥1 uppercase, ≥1 digit |
| `university_name` | string | 2–255 chars |
| `graduation_year` | integer | Future year for STUDENT/MENTOR; past year for ALUMNI |
| `major` | string | 2–255 chars |
| `role` | string | `STUDENT` (default) \| `MENTOR` \| `ALUMNI` |

**Response `201`**
```json
{ "id": 1, "email": "alice@uni.ac.uk" }
```
A verification email is sent automatically. The account cannot log in until the email is verified.

---

### Verify Email
```
GET /auth/verify-email?token=<verification_token>
```
No auth required. The link is delivered by email.

**Response `200`**
```json
{ "message": "Email verified successfully. You can now log in." }
```

---

### Login
```
POST /auth/login
Content-Type: application/x-www-form-urlencoded
```
**Body (form)**
| Field | Value |
|---|---|
| `username` | Email address |
| `password` | Password |

**Response `200`**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "abc123...",
  "token_type": "bearer"
}
```
Store both tokens. Use `access_token` for every API call. Use `refresh_token` to renew the session.

---

### Refresh Token
```
POST /auth/refresh?refresh_token=<token>
```
Rotates the refresh token — the old one is invalidated immediately.

**Response `200`** — same shape as login response.

---

### Logout
```
POST /auth/logout?refresh_token=<token>
Authorization: Bearer <access_token>
```
Revokes the refresh token server-side.

**Response `200`**
```json
{ "message": "Logged out successfully." }
```

---

### Forgot Password
```
POST /auth/forgot-password?email=<email>
```
Always returns the same message regardless of whether the email exists (prevents enumeration).

**Response `200`**
```json
{ "message": "If that email is registered, you will receive a reset link shortly." }
```

---

### Reset Password
```
POST /auth/reset-password?token=<reset_token>&new_password=<password>
```
Token expires after **30 minutes**.

**Response `200`**
```json
{ "message": "Password reset successfully. You can now log in." }
```

---

## 2. Profiles `/profiles`

### Create Profile
```
POST /profiles
Authorization: Bearer <token>
```
**Body (JSON)** — all fields optional
| Field | Type |
|---|---|
| `headline` | string |
| `bio` | string |
| `university` | string |
| `graduation_year` | integer |
| `major` | string |
| `company` | string |
| `job_title` | string |
| `goals` | string |
| `skills` | array |
| `interests` | array |

**Response `201`** — `ProfileResponse`

---

### Get My Profile
```
GET /profiles/me
Authorization: Bearer <token>
```
**Response `200`** — `ProfileResponse`

```json
{
  "id": 1,
  "user_id": 42,
  "full_name": "Alice Smith",
  "avatar_url": "https://res.cloudinary.com/...",
  "headline": "Software Engineer",
  "bio": "...",
  "university": "UCL",
  "graduation_year": 2026,
  "major": "Computer Science",
  "company": "Acme Ltd",
  "job_title": "Intern",
  "goals": "...",
  "skills": ["Python", "FastAPI"],
  "interests": ["AI", "Open Source"]
}
```

---

### Get Any User's Profile
```
GET /profiles/{user_id}
```
Public — no auth required.

**Response `200`** — `ProfileResponse`

---

### Update Profile
```
PATCH /profiles/me
Authorization: Bearer <token>
```
**Body (JSON)** — all fields optional, send only what changes.

**Response `200`** — `ProfileResponse`

---

### Upload Avatar
```
PUT /profiles/me/avatar
Authorization: Bearer <token>
Content-Type: multipart/form-data
```
| Field | Value |
|---|---|
| `file` | Image file — JPEG, PNG, WebP or GIF, max **5 MB** |

**Response `200`** — `ProfileResponse` with updated `avatar_url`

---

### Profile Completion
```
GET /profiles/me/completion
Authorization: Bearer <token>
```
**Response `200`**
```json
{
  "percentage": 70,
  "missing_fields": ["bio", "goals"],
  "completed_fields": ["headline", "university", "major", "skills", "interests", "company", "job_title"]
}
```

---

### Delete Profile
```
DELETE /profiles/me/completion
Authorization: Bearer <token>
```
**Response `200`** — final completion state before deletion.

---

## 3. Events `/events`

### List Upcoming Events
```
GET /events?event_type=<type>
```
No auth required. Optional `event_type` filter: `academic` | `social` | `career` | `networking`

**Response `200`** — array of `EventResponse`

---

### List Past Events
```
GET /events/past
```
No auth required.

**Response `200`** — array of `EventSummaryResponse` (lighter payload)

---

### Get My RSVPs
```
GET /events/rsvps
Authorization: Bearer <token>
```
**Response `200`** — array of `EventRegistrationResponse`

---

### Get Single Event
```
GET /events/{event_id}
```
No auth required.

**Response `200`** — `EventResponse`
```json
{
  "id": 5,
  "organizer_id": 1,
  "organizer": { "id": 1, "full_name": "Alice Smith" },
  "title": "AI Careers Night",
  "description": "...",
  "location": "Room 101",
  "event_date": "2026-06-01T18:00:00Z",
  "event_type": "career",
  "max_attendees": 100,
  "is_active": true,
  "cover_image_url": "https://...",
  "attendee_count": 42
}
```

---

### Create Event
```
POST /events
Authorization: Bearer <token>
Content-Type: multipart/form-data
```
| Field | Type | Rules |
|---|---|---|
| `title` | string | 3–255 chars |
| `description` | string | min 10 chars |
| `location` | string | 2–500 chars |
| `event_date` | datetime | Must be in the future |
| `event_type` | string | `academic` \| `social` \| `career` \| `networking` |
| `max_attendees` | integer (optional) | min 10 |
| `cover_image` | file (optional) | JPEG/PNG/WebP/GIF, max **10 MB** |

**Response `201`** — `EventResponse`

---

### Update Event
```
PATCH /events/{event_id}
Authorization: Bearer <token>
```
Only the organiser can update. Send only changed fields.

**Body (JSON)** — same fields as create, all optional plus `is_active: boolean`

**Response `200`** — `EventResponse`

---

### Upload Cover Image
```
PUT /events/{event_id}/cover-image
Authorization: Bearer <token>
Content-Type: multipart/form-data
```
| Field | Value |
|---|---|
| `file` | Image file — JPEG, PNG, WebP or GIF, max **10 MB** |

**Response `200`** — `EventResponse`

---

### RSVP to Event
```
POST /events/{event_id}/rsvp
Authorization: Bearer <token>
```
Fails with `409` if already registered, `400` if event is full.
A confirmation email is sent automatically.

**Response `201`**
```json
{
  "id": 10,
  "event_id": 5,
  "user_id": 42,
  "status": "registered",
  "registered_at": "2026-03-26T10:00:00Z"
}
```

---

### Cancel RSVP
```
DELETE /events/{event_id}/rsvp
Authorization: Bearer <token>
```
**Response `204`** No Content

---

## 4. Activity `/activity`

### Get My Recent Activity
```
GET /activity/me?limit=20
Authorization: Bearer <token>
```
`limit` — 1–100, default 20.

**Response `200`**
```json
[
  {
    "id": 1,
    "activity_type": "rsvp_event",
    "reference_id": 5,
    "description": "RSVPd to: AI Careers Night",
    "created_at": "2026-03-26T10:00:00Z"
  }
]
```

**Activity types:** `joined_community` | `left_community` | `created_post` | `rsvp_event` | `cancelled_rsvp` | `connected_with_user` | `started_mentorship` | `sent_message`

---

### Get Activity by Type
```
GET /activity/me/{activity_type}?limit=20
Authorization: Bearer <token>
```
Filter to a single activity type from the list above.

**Response `200`** — same shape as above

---

## 5. Communities `/communities`

### Create Community
```
POST /communities
Authorization: Bearer <token>
```
The creator is automatically added as **Admin**.

**Body (JSON)**
| Field | Type | Rules |
|---|---|---|
| `name` | string | 1–255 chars |
| `description` | string (optional) | — |
| `type` | string | `global` \| `university` |
| `university` | string (optional) | Required when `type = university` |
| `is_private` | boolean | Default `false` |

**Response `201`** — `CommunityResponse`
```json
{
  "id": 1,
  "name": "CS Society",
  "description": "...",
  "type": "university",
  "university": "UCL",
  "is_private": false,
  "is_active": true,
  "cover_image_url": null,
  "creator_id": 42,
  "member_count": 1,
  "created_at": "2026-03-26T10:00:00Z"
}
```

---

### List Communities
```
GET /communities
Authorization: Bearer <token>
```
Returns public communities + private communities the user belongs to.

**Response `200`** — array of `CommunityResponse`

---

### Get Community
```
GET /communities/{community_id}
Authorization: Bearer <token>
```
Private communities return `403` for non-members.

**Response `200`** — `CommunityResponse`

---

### Update Community
```
PATCH /communities/{community_id}
Authorization: Bearer <token>  (Admin only)
```
**Body (JSON)** — all optional
| Field | Type |
|---|---|
| `name` | string |
| `description` | string |
| `is_private` | boolean |

**Response `200`** — `CommunityResponse`

---

### Delete Community
```
DELETE /communities/{community_id}
Authorization: Bearer <token>  (Admin only)
```
Soft-deletes (sets `is_active = false`).

**Response `204`** No Content

---

### Join Community
```
POST /communities/{community_id}/join
Authorization: Bearer <token>
```
Fails with `403` if the community is private (use invite link instead) or if the user's university doesn't match a `university`-type community.
Fails with `409` if already a member.

**Response `201`** — `MemberResponse`
```json
{ "user_id": 42, "full_name": "Alice Smith", "role": "member", "joined_at": "..." }
```

---

### Leave Community
```
DELETE /communities/{community_id}/leave
Authorization: Bearer <token>
```
Fails with `409` if the user is the **last admin** — assign another admin first.

**Response `204`** No Content

---

### List Members
```
GET /communities/{community_id}/members
Authorization: Bearer <token>
```
Private communities: members only.

**Response `200`** — array of `MemberResponse`

---

### Update Member Role
```
PATCH /communities/{community_id}/members/{user_id}/role
Authorization: Bearer <token>  (Admin only)
```
**Body (JSON)**
```json
{ "role": "moderator" }
```
Allowed values: `admin` | `moderator` | `member`
Fails with `409` if attempting to demote the last admin.

**Response `200`** — `MemberResponse`

---

### Remove Member
```
DELETE /communities/{community_id}/members/{user_id}
Authorization: Bearer <token>  (Admin or Moderator)
```
Moderators cannot remove Admins.

**Response `204`** No Content

---

### Generate Invite Link
```
POST /communities/{community_id}/invites
Authorization: Bearer <token>  (Admin or Moderator)
```
**Response `201`**
```json
{
  "id": 1,
  "token": "abc123XYZ...",
  "community_id": 1,
  "created_by": 42,
  "use_count": 0,
  "created_at": "..."
}
```
Share the token with users who should join. Tokens do not expire.

---

### Join via Invite
```
POST /communities/join-via-invite/{token}
Authorization: Bearer <token>
```
Works for private communities. Fails with `404` for invalid tokens, `409` if already a member.
Triggers a `community_added` notification for the joining user.

**Response `201`** — `MemberResponse`

---

### Community Room WebSocket
```
WS /communities/{community_id}/ws?token=<access_token>
```
Authenticate via query parameter (Bearer headers are not supported in browser WebSockets).
The connection is rejected with code `4001` for invalid tokens and `4003` for non-members.

**Received events**
```json
{ "event": "new_message", "data": { ...CommunityMessageResponse } }
{ "event": "reaction_update", "data": { "message_id": 5, "reactions": [...] } }
```

---

## 6. Community Messages `/communities/{community_id}/messages`

### Get Messages
```
GET /communities/{community_id}/messages?page=1&limit=20
Authorization: Bearer <token>
```
Private communities: members only.
Results are ordered newest-first.

`page` — default 1; `limit` — 1–100, default 20.

**Response `200`** — array of `CommunityMessageResponse`
```json
[
  {
    "id": 10,
    "community_id": 1,
    "sender_id": 42,
    "content": "Hello everyone!",
    "reply_to_id": null,
    "reply_to": null,
    "attachments": [],
    "reactions": [
      { "emoji": "👍", "count": 3, "reacted_by_me": true }
    ],
    "created_at": "2026-03-26T10:05:00Z"
  }
]
```

---

### Send Message
```
POST /communities/{community_id}/messages
Authorization: Bearer <token>
Content-Type: multipart/form-data
```
Must be a member. A message must contain **text, files, or both** — an empty message is rejected.
Content is checked against the banned words list (case-insensitive).

| Field | Type | Notes |
|---|---|---|
| `content` | string (optional) | Message text |
| `reply_to_id` | integer (optional) | ID of the message being replied to |
| `files` | file[] (optional) | Images — JPEG/PNG/WebP/GIF, max **10 MB** each |

**Response `201`** — `CommunityMessageResponse`

Triggers:
- `new_message` broadcast to all connected community room WebSocket clients
- `community_message` notification for every community member
- `message_reply` notification for the original message author (if replying)

---

### Toggle Reaction
```
POST /communities/{community_id}/messages/{message_id}/reactions
Authorization: Bearer <token>
```
Adding the same emoji twice **removes** it (toggle).

**Body (JSON)**
```json
{ "emoji": "👍" }
```

**Response `200`** — aggregated reactions for the message
```json
[
  { "emoji": "👍", "count": 2, "reacted_by_me": true },
  { "emoji": "❤️", "count": 1, "reacted_by_me": false }
]
```

Triggers:
- `reaction_update` broadcast to all connected community room WebSocket clients
- `message_reaction` notification for the message author (only when adding, not removing)

---

## 7. Notifications `/notifications`

### Get Notifications
```
GET /notifications?limit=50
Authorization: Bearer <token>
```
`limit` — 1–200, default 50. Ordered newest-first.

**Response `200`**
```json
[
  {
    "id": 1,
    "sender_id": 7,
    "type": "community_message",
    "reference_id": 10,
    "is_read": false,
    "created_at": "2026-03-26T10:05:00Z"
  }
]
```

**Notification types**
| Type | Trigger |
|---|---|
| `message` | Direct message received |
| `connection_request` | Someone sent a connection request |
| `connection_accepted` | Your connection request was accepted |
| `mentorship_request` | Someone requested mentorship |
| `mentorship_accepted` | Mentorship request accepted |
| `mentorship_rejected` | Mentorship request rejected |
| `post_like` | Your post was liked |
| `post_comment` | Someone commented on your post |
| `event_reminder` | Upcoming event reminder |
| `job_application` | Job application received |
| `community_added` | You were added to a community via invite |
| `community_message` | New message in one of your communities |
| `message_reply` | Someone replied to your message |
| `message_reaction` | Someone reacted to your message |

---

### Get Unread Count
```
GET /notifications/unread-count
Authorization: Bearer <token>
```
**Response `200`**
```json
{ "unread_count": 4 }
```

---

### Get Single Notification
```
GET /notifications/{notification_id}
Authorization: Bearer <token>
```
Returns `404` if the notification belongs to a different user.

**Response `200`** — single notification object

---

### Mark One as Read
```
PATCH /notifications/{notification_id}/read
Authorization: Bearer <token>
```
**Response `200`** — notification with `is_read: true`

---

### Mark All as Read
```
PATCH /notifications/read-all
Authorization: Bearer <token>
```
**Response `204`** No Content

---

### Delete All Notifications
```
DELETE /notifications
Authorization: Bearer <token>
```
**Response `204`** No Content

---

### Real-Time Notification WebSocket
```
WS /notifications/ws?token=<access_token>
```
Stays open to receive notifications as they are created. Supports multiple simultaneous connections per user (e.g. multiple browser tabs).

**Received events**
```json
{
  "event": "notification",
  "data": {
    "id": 5,
    "type": "community_message",
    "sender_id": 7,
    "reference_id": 10,
    "is_read": false,
    "created_at": "2026-03-26T10:05:00Z"
  }
}
```

---

## 8. Moderation `/admin/banned-words`

All endpoints require a valid access token. There is no role gate in the current implementation — consider restricting to admin users in production.

### List Banned Words
```
GET /admin/banned-words
Authorization: Bearer <token>
```
**Response `200`** — `["badword", "spam", ...]`

---

### Add Banned Word
```
POST /admin/banned-words
Authorization: Bearer <token>
```
**Body (JSON)**
```json
{ "word": "spam" }
```
Words are stored lowercased. Matching is case-insensitive and substring-based.

**Response `201`**
```json
{ "word": "spam" }
```

---

### Remove Banned Word
```
DELETE /admin/banned-words/{word}
Authorization: Bearer <token>
```
**Response `204`** No Content

---

## 9. Mentorship `/mentorship`

The mentorship system lets users become mentors, discover mentors, send/accept requests, manage ongoing relationships, schedule sessions, and share resources.

---

### Become a Mentor
```
POST /mentorship/become-mentor
Authorization: Bearer <token>
```
Creates a mentor profile for the current user. Returns `409` if a profile already exists.

**Body (JSON)** — all fields optional
| Field | Type | Notes |
|---|---|---|
| `bio` | string | Free-text mentor bio |
| `linkedin_url` | string | LinkedIn profile URL |
| `expertise_areas` | string[] | e.g. `["Python", "Machine Learning"]` |
| `mentorship_goals` | string[] | e.g. `["career change", "interview prep"]` |
| `availability_slots` | `{"day": string, "time": string}`[] | e.g. `[{"day": "Monday", "time": "10:00"}]` |
| `max_mentees` | integer | Default `5`, min `1` |

**Response `201`** — `MentorProfileResponse`
```json
{
  "id": 1,
  "user_id": 42,
  "user": { "id": 42, "full_name": "Alice Smith", "university_name": "UCL" },
  "bio": "I help students break into tech.",
  "linkedin_url": "https://linkedin.com/in/alice",
  "expertise_areas": ["Python", "FastAPI"],
  "mentorship_goals": ["career change", "interview prep"],
  "availability_slots": [{ "day": "Monday", "time": "10:00" }],
  "max_mentees": 5,
  "is_active": true,
  "created_at": "2026-03-31T10:00:00Z",
  "updated_at": "2026-03-31T10:00:00Z"
}
```

---

### Get My Mentor Profile
```
GET /mentorship/mentor-profile/me
Authorization: Bearer <token>
```
Returns `404` if the user has not created a mentor profile yet.

**Response `200`** — `MentorProfileResponse`

---

### Update My Mentor Profile
```
PATCH /mentorship/mentor-profile/me
Authorization: Bearer <token>
```
Partial update — send only the fields to change.

**Body (JSON)** — all optional, same fields as create

**Response `200`** — `MentorProfileResponse`

---

### Deactivate My Mentor Profile
```
DELETE /mentorship/mentor-profile/me
Authorization: Bearer <token>
```
Soft-deletes by setting `is_active = false`. The profile is not removed from the database.

**Response `200`** — `MentorProfileResponse` with `is_active: false`

---

### Browse Mentors
```
GET /mentorship/mentors
Authorization: Bearer <token>
```
Returns only **active** mentor profiles. Excludes the current user and any mentors with whom the current user already has an active relationship.

**Query parameters** — all optional
| Param | Description |
|---|---|
| `skills` | Comma-separated — filter by overlap with `expertise_areas` |
| `goals` | Comma-separated — filter by overlap with `mentorship_goals` |
| `university` | Exact match (case-insensitive) on the mentor's university |

**Response `200`** — array of `MentorProfileResponse`

---

### Get Mentor Profile by User ID
```
GET /mentorship/mentors/{user_id}
Authorization: Bearer <token>
```
Returns `404` if no active mentor profile exists for that user.

**Response `200`** — `MentorProfileResponse`

---

### Send a Mentorship Request
```
POST /mentorship/requests
Authorization: Bearer <token>
```
**Validations:**
- `400` — cannot send a request to yourself
- `400` — mentor is at full capacity (`active relationships ≥ max_mentees`)
- `404` — target user has no active mentor profile
- `409` — a pending request to this mentor already exists
- `409` — an active relationship with this mentor already exists

Fires a `mentorship_request` notification to the mentor.

**Body (JSON)**
| Field | Type | Rules |
|---|---|---|
| `mentor_id` | integer | Target mentor's user ID |
| `goal` | string | 1–500 chars |
| `meeting_frequency` | string | e.g. `"weekly"` — 1–100 chars |
| `session_length_minutes` | integer | min `15` |
| `message` | string | Personalised message, min 1 char |

**Response `201`** — `MentorshipRequestResponse`
```json
{
  "id": 1,
  "mentee_id": 42,
  "mentor_id": 7,
  "mentee": { "id": 42, "full_name": "Bob Jones", "university_name": "UCL" },
  "mentor": { "id": 7, "full_name": "Alice Smith", "university_name": "UCL" },
  "goal": "Land a backend engineering role",
  "meeting_frequency": "weekly",
  "session_length_minutes": 60,
  "message": "Hi Alice, I'd love your guidance on interview prep.",
  "status": "pending",
  "created_at": "2026-03-31T10:00:00Z"
}
```

---

### Get Incoming Requests
```
GET /mentorship/requests/incoming
Authorization: Bearer <token>
```
Returns **pending** requests addressed to the current user as a mentor, ordered newest-first.

**Response `200`** — array of `MentorshipRequestResponse`

---

### Get Outgoing Requests
```
GET /mentorship/requests/outgoing
Authorization: Bearer <token>
```
Returns all requests sent by the current user as a mentee (all statuses), ordered newest-first.

**Response `200`** — array of `MentorshipRequestResponse`

---

### Accept a Request
```
PATCH /mentorship/requests/{request_id}/accept
Authorization: Bearer <token>  (mentor only)
```
- `403` — current user is not the mentor on this request
- `400` — request is not pending

On success: creates an active `MentorshipRelationship` and updates request status to `accepted`.
Fires a `mentorship_accepted` notification to the mentee.

**Response `200`** — `MentorshipRequestResponse` with `status: "accepted"`

---

### Reject a Request
```
PATCH /mentorship/requests/{request_id}/reject
Authorization: Bearer <token>  (mentor only)
```
- `403` — current user is not the mentor on this request
- `400` — request is not pending

Fires a `mentorship_rejected` notification to the mentee.

**Response `200`** — `MentorshipRequestResponse` with `status: "rejected"`

---

### Cancel a Request
```
DELETE /mentorship/requests/{request_id}
Authorization: Bearer <token>  (mentee only)
```
- `403` — current user is not the mentee on this request
- `400` — request is not pending

**Response `204`** No Content

---

### My Mentees
```
GET /mentorship/relationships/my-mentees
Authorization: Bearer <token>
```
Returns active relationships where the current user is the **mentor**.

**Response `200`** — array of `MentorshipRelationshipResponse`
```json
[
  {
    "id": 1,
    "mentor_id": 7,
    "mentee_id": 42,
    "mentor": { "id": 7, "full_name": "Alice Smith", "university_name": "UCL" },
    "mentee": { "id": 42, "full_name": "Bob Jones", "university_name": "UCL" },
    "goal": "Land a backend engineering role",
    "meeting_frequency": "weekly",
    "session_length_minutes": 60,
    "status": "active",
    "started_at": "2026-03-31T10:00:00Z",
    "ended_at": null
  }
]
```

---

### My Mentors
```
GET /mentorship/relationships/my-mentors
Authorization: Bearer <token>
```
Returns active relationships where the current user is the **mentee**.

**Response `200`** — array of `MentorshipRelationshipResponse`

---

### Get Relationship
```
GET /mentorship/relationships/{relationship_id}
Authorization: Bearer <token>
```
- `403` — current user is neither the mentor nor the mentee

**Response `200`** — `MentorshipRelationshipResponse`

---

### End Relationship
```
PATCH /mentorship/relationships/{relationship_id}/end
Authorization: Bearer <token>
```
Either participant can end the relationship.
- `403` — current user is not a participant
- `400` — relationship has already ended

Sets `status = "ended"` and `ended_at = now`.

**Response `200`** — `MentorshipRelationshipResponse` with `status: "ended"`

---

### Create Session
```
POST /mentorship/relationships/{relationship_id}/sessions
Authorization: Bearer <token>
```
- `403` — current user is not a participant
- `400` — relationship is not active
- `422` — `scheduled_at` is not in the future

**Body (JSON)**
| Field | Type | Rules |
|---|---|---|
| `scheduled_at` | datetime (ISO 8601) | Must be in the future |
| `notes` | string (optional) | — |

**Response `201`** — `MentorshipSessionResponse`
```json
{
  "id": 1,
  "relationship_id": 1,
  "scheduled_at": "2026-04-15T14:00:00Z",
  "notes": "Discuss CV and portfolio.",
  "status": "upcoming",
  "created_at": "2026-03-31T10:00:00Z"
}
```

---

### List Sessions
```
GET /mentorship/relationships/{relationship_id}/sessions
Authorization: Bearer <token>
```
- `403` — current user is not a participant

Ordered by `scheduled_at` ascending.

**Response `200`** — array of `MentorshipSessionResponse`

---

### Update Session
```
PATCH /mentorship/relationships/{relationship_id}/sessions/{session_id}
Authorization: Bearer <token>
```
- `403` — current user is not a participant
- `404` — session does not belong to this relationship
- `422` — `scheduled_at` is not in the future (if provided)

**Body (JSON)** — all optional
| Field | Type |
|---|---|
| `scheduled_at` | datetime |
| `notes` | string |
| `status` | `upcoming` \| `completed` \| `cancelled` |

**Response `200`** — `MentorshipSessionResponse`

---

### Share Resource
```
POST /mentorship/relationships/{relationship_id}/resources
Authorization: Bearer <token>
```
- `403` — current user is not a participant
- `422` — `category` is not one of the four allowed values

**Body (JSON)**
| Field | Type | Rules |
|---|---|---|
| `title` | string | 1–500 chars |
| `category` | string | `Article` \| `Video` \| `Career Guide` \| `Interview` |
| `url` | string | 1–2000 chars |
| `note` | string (optional) | — |

**Response `201`** — `MentorshipResourceResponse`
```json
{
  "id": 1,
  "relationship_id": 1,
  "shared_by_id": 7,
  "shared_by": { "id": 7, "full_name": "Alice Smith" },
  "title": "System Design Interview Guide",
  "category": "Career Guide",
  "url": "https://example.com/system-design",
  "note": "Chapters 3–5 are most relevant.",
  "created_at": "2026-03-31T10:00:00Z"
}
```

---

### List Resources
```
GET /mentorship/relationships/{relationship_id}/resources
Authorization: Bearer <token>
```
- `403` — current user is not a participant

Ordered by `created_at` descending (newest first).

**Response `200`** — array of `MentorshipResourceResponse`

---

## Error Reference

| Status | Meaning |
|---|---|
| `400` | Bad request — invalid input or business rule violation |
| `401` | Missing or invalid access token |
| `403` | Authenticated but not allowed (wrong role, private community, etc.) |
| `404` | Resource not found or belongs to another user |
| `409` | Conflict — duplicate membership, last-admin protection, etc. |
| `422` | Validation error — missing required fields, banned word detected |
| `502` | Upstream failure — e.g. Cloudinary upload error |

---

## Image Upload Rules

| Context | Max size | Accepted formats |
|---|---|---|
| Profile avatar | 5 MB | JPEG, PNG, WebP, GIF |
| Event cover image | 10 MB | JPEG, PNG, WebP, GIF |
| Community cover image | 10 MB | JPEG, PNG, WebP, GIF |
| Message attachment | 10 MB | JPEG, PNG, WebP, GIF |

File type is validated by **magic bytes**, not filename extension — renaming a non-image will be rejected.

---

## Quick Start

```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"full_name":"Alice Smith","email":"alice@uni.ac.uk","password":"Secret1","university_name":"UCL","graduation_year":2027,"major":"CS","role":"STUDENT"}'

# 2. Verify email (click link from email or use token directly in dev)
curl "http://localhost:8000/auth/verify-email?token=<token>"

# 3. Login
curl -X POST http://localhost:8000/auth/login \
  -d "username=alice@uni.ac.uk&password=Secret1"

# 4. Use the access token
curl http://localhost:8000/communities \
  -H "Authorization: Bearer <access_token>"

# 5. Connect to real-time notifications
# ws://localhost:8000/notifications/ws?token=<access_token>

# 6. Connect to a community room
# ws://localhost:8000/communities/1/ws?token=<access_token>
```
