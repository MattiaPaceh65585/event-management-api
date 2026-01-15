import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from bson import ObjectId
from bson.errors import InvalidId
import motor.motor_asyncio
import uuid
import io

# Load environment variables from .env file
# This allows sensitive data such as database credentials to be kept out of the codebase
# for security reasons.
load_dotenv()

app = FastAPI(
    title="Event Management API",
    description="RESTful API for managing events, venues, attendees, bookings and media",
    version="1.0.0"
)

# Read the MongoDB URI from environment variables
MONGO_URI = os.getenv("MONGO_URI")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI is not set in .env file")

# Connect to MongoDB Atlas
# Async access is used to improve scalability and prevent blocking during database operations.
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)

# Select the database used by the application
db = client.event_management_db

# Data Models
class Event(BaseModel):
    """
    Pydantic model used to validate event data received
    from clients. Using Pydantic ensures that malformed or missing
    fields are automatically rejected with a 422 response.
    """
    name: str
    description: str
    date: str
    venue_id: str
    max_attendees: int = Field(..., gt=-1)

class Attendee(BaseModel):
    """
    Pydantic model used to validate attendee data received
    from clients. Using Pydantic ensures that malformed or missing
    fields are automatically rejected with a 422 response.
    """
    name: str
    email: str
    phone: Optional[str] = None

class Venue(BaseModel):
    """
    Pydantic model used to validate venue data received
    from clients. Using Pydantic ensures that malformed or missing
    fields are automatically rejected with a 422 response.
    """
    name: str
    address: str
    capacity: int = Field(..., gt=-1)

class Booking(BaseModel):
    """
    Pydantic model used to validate booking data received
    from clients. Using Pydantic ensures that malformed or missing
    fields are automatically rejected with a 422 response.
    """
    event_id: str
    attendee_id: str
    ticket_type: str
    quantity: int = Field(..., gt=-1)

# Helper Methods
async def validate_public_id(public_id: str, collection, name: str):
    """
    Validates that a document with the given public_id exists in the specified collection.
    Raises an HTTPException with status code 400 if not found.
    This helper method prevents:
    - Invalid references to non-existent documents
    - Broken references between collections
    - Injection-style attacks using malformed IDs
    """
    
    doc = await collection.find_one({"public_id": public_id})
    
    if not doc:
        raise HTTPException(status_code=400, detail=f"{name} not found")
    
    return doc

# Event Endpoints
# Create an event
# The venue_id is validated to ensure the venue exists before
# inserting the event, maintaining referential integrity.
@app.post("/events")
async def create_event(event: Event):
    await validate_public_id(event.venue_id, db.venues, "Venue")

    doc = event.dict()
    doc["public_id"] = str(uuid.uuid4())

    await db.events.insert_one(doc)

    return {
        "message": "Event created",
        "event_id": doc["public_id"]
    }

# Get all events
# Returns a list of all events in the database.
@app.get("/events")
async def get_events():
    return await db.events.find({}, {"_id": 0}).to_list(100)

# Get a single event
# Retrieves a specific event by its ID.
@app.get("/events/{event_id}")
async def get_event(event_id: str):
    try:
        event = await db.events.find_one({"public_id": event_id}, {"_id": 0})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid event ID")

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    return event

# Update an existing event.
# The venue reference is revalidated to prevent updating the event
# with a non-existent venue ID.
@app.put("/events/{event_id}")
async def update_event(event_id: str, event: Event):
    await validate_public_id(event_id, db.events, "Event")
    await validate_public_id(event.venue_id, db.venues, "Venue")

    await db.events.update_one(
        {"public_id": event_id},
        {"$set": event.dict()}
    )
    return {"message": "Event updated"}

# Delete an event
# Deletes an event by its ID.
@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    result = await db.events.delete_one({"public_id": event_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"message": "Event deleted"}

# Venues Endpoints
# Creates a new venue in the database.
@app.post("/venues")
async def create_venue(venue: Venue):
    doc = venue.dict()
    doc["public_id"] = str(uuid.uuid4())

    await db.venues.insert_one(doc)
    return {
        "message": "Venue created",
        "venue_id": doc["public_id"]
    }


# Get all venues
# Returns a list of all venues in the database.
@app.get("/venues")
async def get_venues():
    return await db.venues.find({}, {"_id": 0}).to_list(100)

# Get a single venue
# Retrieves a specific venue by its ID.
@app.get("/venues/{venue_id}")
async def get_venue(venue_id: str):
    venue = await db.venues.find_one({"public_id": venue_id}, {"_id": 0})
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    return venue

# Update a venue
# Updates an existing venue by its ID.
@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, venue: Venue):
    await validate_public_id(venue_id, db.venues, "Venue")

    await db.venues.update_one(
        {"public_id": venue_id},
        {"$set": venue.dict()}
    )

    return {"message": "Venue updated"}

# Delete a venue
# Deletes a venue by its ID.
@app.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str):
    result = await db.venues.delete_one({"public_id": venue_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")

    return {"message": "Venue deleted"}

# Attendees Endpoints
# Create an attendee
# Creates a new attendee in the database.
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    doc = attendee.dict()
    doc["public_id"] = str(uuid.uuid4())

    await db.attendees.insert_one(doc)
    return {
        "message": "Attendee created",
        "attendee_id": doc["public_id"]
    }

# Get all attendees
# Returns a list of all attendees in the database.
@app.get("/attendees")
async def get_attendees():
    return await db.attendees.find({}, {"_id": 0}).to_list(100)

# Get a single attendee
# Retrieves a specific attendee by its ID.
@app.get("/attendees/{attendee_id}")
async def get_attendee(attendee_id: str):
    attendee = await db.attendees.find_one(
        {"public_id": attendee_id},
        {"_id": 0}
    )

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")

    return attendee

# Update an attendee
# Updates an existing attendee by its ID.
@app.put("/attendees/{attendee_id}")
async def update_attendee(attendee_id: str, attendee: Attendee):
    await validate_public_id(attendee_id, db.attendees, "Attendee")

    await db.attendees.update_one(
        {"public_id": attendee_id},
        {"$set": attendee.dict()}
    )

    return {"message": "Attendee updated"}

# Delete an attendee
# Deletes an attendee by its ID.
@app.delete("/attendees/{attendee_id}")
async def delete_attendee(attendee_id: str):
    result = await db.attendees.delete_one({"public_id": attendee_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")

    return {"message": "Attendee deleted"}

# Bookings Endpoints
# Create a booking
# The event_id and attendee_id are validated to ensure they exist before
# inserting the booking, maintaining referential integrity.
@app.post("/bookings")
async def create_booking(booking: Booking):
    await validate_public_id(booking.event_id, db.events, "Event")
    await validate_public_id(booking.attendee_id, db.attendees, "Attendee")

    doc = booking.dict()
    doc["public_id"] = str(uuid.uuid4())

    await db.bookings.insert_one(doc)
    return {
        "message": "Booking created",
        "booking_id": doc["public_id"]
    }

# Get all bookings
# Returns a list of all bookings in the database.
@app.get("/bookings")
async def get_bookings():
    return await db.bookings.find({}, {"_id": 0}).to_list(100)

# Get a single booking
# Retrieves a specific booking by its ID.
@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    booking = await db.bookings.find_one(
        {"public_id": booking_id},
        {"_id": 0}
    )

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    return booking

# Update a booking
# Updates an existing booking by its ID.
@app.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, booking: Booking):
    await validate_public_id(booking_id, db.bookings, "Booking")
    await validate_public_id(booking.event_id, db.events, "Event")
    await validate_public_id(booking.attendee_id, db.attendees, "Attendee")

    await db.bookings.update_one(
        {"public_id": booking_id},
        {"$set": booking.dict()}
    )

    return {"message": "Booking updated"}

# Delete a booking
# Deletes a booking by its ID.
@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str):
    result = await db.bookings.delete_one({"public_id": booking_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {"message": "Booking deleted"}

# Upload Event Poster (Image)
# Files are stored directly in MongoDB as binary data.
# This approach simplifies retrieval for small media files
# and avoids dependency on external storage services.
@app.post("/upload_event_poster/{event_id}")
async def upload_event_poster(event_id: str, file: UploadFile = File(...)):
    await validate_public_id(event_id, db.events, "Event")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    content = await file.read()

    doc = {
        "public_id": str(uuid.uuid4()),
        "event_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    db.event_posters.insert_one(doc)

    return {"message": "Poster uploaded", "id": doc["public_id"]}


# Upload Promotional Video
# Files are stored directly in MongoDB as binary data.
# This approach simplifies retrieval for small media files
# and avoids dependency on external storage services.
@app.post("/upload_promo_video/{event_id}")
async def upload_promo_video(event_id: str, file: UploadFile = File(...)):
    await validate_public_id(event_id, db.events, "Event")

    if not file.content_type.startswith("video/"):
        raise HTTPException(status_code=400, detail="Only video files allowed")

    content = await file.read()

    doc = {
        "public_id": str(uuid.uuid4()),
        "event_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    await db.promo_videos.insert_one(doc)

    return {"message": "Promotional video uploaded", "id": doc["public_id"]}

# Upload Venue Photo
# Files are stored directly in MongoDB as binary data.
# This approach simplifies retrieval for small media files
# and avoids dependency on external storage services.
@app.post("/upload_venue_photo/{venue_id}")
async def upload_venue_photo(venue_id: str, file: UploadFile = File(...)):
    await validate_public_id(venue_id, db.venues, "Venue")

    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files allowed")

    content = await file.read()

    doc = {
        "public_id": str(uuid.uuid4()),
        "venue_id": venue_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    await db.venue_photos.insert_one(doc)

    return {"message": "Venue photo uploaded", "id": doc["public_id"]}