# Event Management REST API

A RESTful web API built using **FastAPI** and **MongoDB Atlas** for managing events, attendees, venues, ticket bookings, and multimedia assets such as event posters, promotional videos, and venue photos.

This project was developed as part of a home assignment to demonstrate RESTful API design, database integration, file uploads, security considerations, and cloud deployment.

---

## Features

- Create and manage events
- Register attendees
- Manage venues
- Book tickets for events
- Upload and retrieve:
  - Event posters (images)
  - Promotional videos
  - Venue photos
- MongoDB Atlas cloud database integration
- Automatic API documentation (Swagger & ReDoc)

---

## Technology Stack

- **Backend Framework**: FastAPI (Python)
- **ASGI Server**: Uvicorn
- **Database**: MongoDB Atlas
- **Database Driver**: Motor (Async MongoDB driver)
- **Validation**: Pydantic
- **Environment Variables**: python-dotenv
- **Version Control**: Git & GitHub

---

## Environment Setup

### 1. Create and activate a virtual environment

```bash
python -m venv venv
venv\Scripts\activate   # On Windows
uvicorn main:app --reload

