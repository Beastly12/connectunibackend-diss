# ConnectUni Backend

Backend API powering ConnectUni — a full-stack university networking platform connecting students, alumni, and industry professionals through mentorship, communities, events, and professional networking.

![FastAPI](https://img.shields.io/badge/FastAPI-Backend-009688)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Database-4169E1)
![Docker](https://img.shields.io/badge/Docker-Containerized-2496ED)
![AWS](https://img.shields.io/badge/AWS-Deployed-FF9900)

## 🚀 Live System

| Service | URL |
|----------|------|
| Web Application | https://d1hl36km7a0922.cloudfront.net |
| Production API | https://connectuni-api.ddns.net |
| API Documentation | https://connectuni-api.ddns.net/docs |

---

## 📖 Overview

ConnectUni is a university-focused networking platform designed to connect students, alumni, and industry professionals through mentorship, communities, events, and professional networking.

This repository contains the FastAPI backend that powers the entire ConnectUni ecosystem, serving both the React web application and Flutter mobile application from a unified API.

### Responsibilities

- Authentication & Authorization
- User Profile Management
- Mentorship Workflows
- Community Management
- Event Management
- Notifications
- Real-Time Communication
- Media Storage Integration
- API Documentation

---

## ✨ Key Features

### 🔐 Authentication & Security

- JWT Authentication
- Refresh Token Rotation
- Email Verification
- Password Reset
- Secure Password Hashing
- Protected API Routes
- Role-Based Access Control

### 👤 User Management

- Student Profiles
- Alumni Profiles
- Industry Professional Profiles
- Profile Completion Tracking
- Verification Status Management
- Skills & Interests Management

### 🎯 Mentorship Platform

- Mentor Discovery
- Mentorship Requests
- Request Approval Workflow
- Session Scheduling
- Milestone Tracking
- Resource Sharing
- Ratings & Reviews
- Relationship Lifecycle Management

### 👥 Communities

- Public & Private Communities
- Community Membership Management
- Community Messaging
- Invite-Based Access
- Community Moderation

### 📅 Events

- Event Creation
- Event Discovery
- RSVP Management
- Attendance Tracking
- Event Categories

### 🔔 Notifications

- Activity Notifications
- Mentorship Updates
- Event Notifications
- Unread Notification Counts

### ⚡ Real-Time Features

- WebSocket Infrastructure
- Community Chat
- Live Notifications

---

## 🏗 Architecture

```text
React Web Application
          │
          │ HTTPS
          ▼

┌─────────────────────────────┐
│        FastAPI API          │
└──────────────┬──────────────┘
               │

 ┌─────────────┼─────────────┐
 ▼             ▼             ▼

Auth      Mentorship     Communities

 ▼             ▼             ▼

 Events   Notifications   WebSockets

               │

               ▼

        PostgreSQL Database

               │

               ▼

          Cloudinary
```

---

## 🛠 Technology Stack

### Backend

- FastAPI
- Python
- SQLAlchemy
- PostgreSQL
- Pydantic

### Authentication

- JWT
- Refresh Tokens
- Email Verification
- Password Recovery

### Infrastructure

- Docker
- AWS
- Cloudinary

### Documentation

- OpenAPI
- Swagger UI

---

## 💡 Engineering Highlights

### Cross-Platform API

A single backend serves:

- React Web Application
- Flutter Mobile Application

ensuring consistent business rules and user experiences across platforms.

### Mentorship Lifecycle

Implemented a complete mentorship workflow:

- Mentor Discovery
- Request Submission
- Acceptance / Rejection
- Session Scheduling
- Milestone Tracking
- Resource Sharing
- Reviews
- Relationship Closure

### Real-Time Communication

WebSocket support enables:

- Community Messaging
- Live Notifications
- Future Real-Time Features

### Modern Authentication

Security features include:

- Access Tokens
- Refresh Token Rotation
- Email Verification
- Password Recovery

---

## 📚 API Documentation

Interactive OpenAPI documentation is available at:

```text
https://connectuni-api.ddns.net/docs
```

---

## 🔗 Related Repositories

### React Frontend

```text
https://github.com/Beastly12/connectuniWebapp
```

### Flutter Mobile Application

```text
https://github.com/Beastly12/ConnectUniMobileApp
```

---

## 🚀 Getting Started

### Clone Repository

```bash
git clone https://github.com/Beastly12/connectunibackend-diss.git
cd connectunibackend-diss
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure Environment Variables

Create a `.env` file and add the required credentials.

```env
DATABASE_URL=
SECRET_KEY=
JWT_SECRET=
CLOUDINARY_URL=
```

### Run Development Server

```bash
uvicorn app.main:app --reload
```

Application:

```text
http://localhost:8000
```

Swagger Documentation:

```text
http://localhost:8000/docs
```

---

## 📈 Future Enhancements

- Push Notifications
- AI-Powered Mentor Matching
- Community Analytics
- Recommendation Engine
- Multi-University Support

---

## 👨‍💻 Author

**Dafe**

Software Engineer

GitHub: https://github.com/Beastly12

---

## 📄 License

This project is licensed under the MIT License.
