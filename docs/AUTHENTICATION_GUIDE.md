# Authentication Guide

## Overview

This service implements **JWT-based authentication with refresh token rotation** using FastAPI.

It includes:

- **Argon2** for secure password hashing  
- **JWT access tokens (short-lived)**  
- **Opaque refresh tokens (stored hashed in the database)**  
- **Refresh token rotation & revocation**  
- **FastAPI dependency-based route protection**

Authentication is:
- **Stateless for access tokens**
- **Stateful for refresh tokens (stored in DB)**

---

# Base URL

```
/auth
```

---

# Public Endpoints (No Authentication Required)

---

## 1. Register

```http
POST /auth/register
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

### What Happens Internally

1. Password is hashed using Argon2.
2. A new user record is created in the database.
3. `is_active` is set to `true`.
4. `is_verified` can later be used if email verification is implemented.

### Response

```json
{
  "id": 1,
  "email": "john@example.com"
}
```

---

## 2. Login

```http
POST /auth/login
Content-Type: application/json

{
  "email": "john@example.com",
  "password": "securepassword123"
}
```

### What Happens Internally

1. User is retrieved by email.
2. Password is verified against the stored Argon2 hash.
3. A short-lived JWT access token is created.
4. A random refresh token is generated.
5. The refresh token is hashed and stored in the database.
6. Both tokens are returned to the client.

### Response

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "Jf82hF8skL0sJ9sdnKf82hsd...",
  "token_type": "bearer"
}
```

---

## 3. Refresh Access Token

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "Jf82hF8skL0sJ9sdnKf82hsd..."
}
```

### What Happens Internally

1. The refresh token is hashed.
2. The database is queried for a matching token.
3. The system checks:
   - Token exists
   - Not revoked
   - Not expired
4. The old refresh token is revoked (rotation).
5. A new access token and refresh token are issued.
6. The new refresh token is stored (hashed) in DB.

### Response

```json
{
  "access_token": "new.jwt.token...",
  "refresh_token": "newRefreshToken...",
  "token_type": "bearer"
}
```

---

## 4. Logout

```http
POST /auth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "current_refresh_token"
}
```

### What Happens Internally

1. Access token is validated.
2. Provided refresh token is hashed.
3. Matching token is marked as revoked in the database.

### Response

```json
{
  "ok": true
}
```

---

# Protected Endpoints (Require Authentication)

---

## 5. Get Current User

```http
GET /auth/me
Authorization: Bearer <access_token>
```

### Response

```json
{
  "id": 1,
  "email": "john@example.com",
  "is_active": true,
  "is_verified": false
}
```

---

# How to Protect Routes

Use the `get_current_user` dependency.

### Example

```python
from fastapi import APIRouter, Depends
from app.api.deps import get_current_user
from app.models import User

router = APIRouter()

@router.get("/profile")
async def profile(current_user: User = Depends(get_current_user)):
    return {
        "message": f"Hello {current_user.email}",
        "user_id": current_user.id
    }

@router.post("/posts")
async def create_post(
    title: str,
    content: str,
    current_user: User = Depends(get_current_user)
):
    return {
        "title": title,
        "content": content,
        "author_id": current_user.id
    }
```

---

# Authentication Flow

1. **User registers** → Password is hashed and stored  
2. **User logs in** → Access token + refresh token returned  
3. **Client stores tokens securely**  
4. **Client calls protected routes** → Sends `Authorization: Bearer <access_token>`  
5. **Access token expires** → Client calls `/auth/refresh`  
6. **Logout** → Refresh token revoked  

---

# Token Details

## Access Token

- Type: JWT  
- Signed using `JWT_SECRET`  
- Contains:
  - `uid` (user ID)
  - `sub` (email)
  - `type = access`
  - `exp` (expiration)
- Short-lived (default: 15 minutes)

---

## Refresh Token

- Random opaque string (not JWT)
- Stored hashed in the database
- Long-lived (default: 14 days)
- Rotated after each use
- Can be revoked
- Enables logout and session invalidation

---

# Error Responses

---

## 401 Unauthorized

```json
{
  "detail": "Invalid authentication credentials"
}
```

Possible Reasons:

- No token provided
- Invalid JWT
- Expired JWT
- Invalid refresh token
- Revoked refresh token
- User inactive

---

## 400 Bad Request

```json
{
  "detail": "Email already registered"
}
```

Reason:

- Attempting to register with an existing email

---

# Token Expiration

Configured via environment variables:

```env
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=14
```

After expiration:

- Access token → must be refreshed  
- Refresh token → user must log in again  

---

# Security Best Practices

1. Always use HTTPS in production  
2. Never commit `.env` to version control  
3. Use a strong, randomly generated `JWT_SECRET`  
4. Store tokens securely:
   - Web: httpOnly cookies (recommended)
   - Mobile: Secure storage (Keychain/Keystore)
5. Implement login rate limiting  
6. Consider adding:
   - Email verification
   - Account lockout after repeated failures
   - Two-factor authentication (2FA)

---

# Environment Variables

```env
POSTGRES_HOST=db
POSTGRES_PORT=5432
POSTGRES_DB=authdb
POSTGRES_USER=authuser
POSTGRES_PASSWORD=authpass

JWT_SECRET=<secure-random-string>
JWT_ALG=HS256
ACCESS_TOKEN_MINUTES=15
REFRESH_TOKEN_DAYS=14
```


# Summary

This authentication system provides:

- Secure password hashing with Argon2  
- Short-lived stateless JWT access tokens  
- Database-backed refresh token rotation  
- Token revocation and logout support  
- Clean FastAPI dependency-based route protection  
- Docker-ready deployment  

Designed for scalability, maintainability, and production readiness.
