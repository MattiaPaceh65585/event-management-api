import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from bson import ObjectId
from bson.errors import InvalidId
import motor.motor_asyncio
import io

# Load environment variables from .env file
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
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URI)
db = client.event_management_db

# Data Models
class Event(BaseModel):
    name: str
    description: str
    date: str
    venue_id: str
    max_attendees: int

class Attendee(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None

class Venue(BaseModel):
    name: str
    address: str
    capacity: int

class Booking(BaseModel):
    event_id: str
    attendee_id: str
    ticket_type: str
    quantity: int

# Helper Methods
async def validate_object_id(id_str: str, collection, name: str):
    try:
        obj_id = ObjectId(id_str)
    except:
        raise HTTPException(status_code=400, detail=f"Invalid {name} ID format")
    
    exists = await collection.find_one({"_id": obj_id})
    if not exists:
        raise HTTPException(status_code=400, detail=f"{name} not found")
    
    return obj_id

# Event Endpoints
# Create an event
@app.post("/events")
async def create_event(event: Event):
    venue_obj_id = await validate_object_id(
        event.venue_id, db.venues, "Venue"
    )

    event_doc = event.dict()
    event_doc["venue_id"] = str(venue_obj_id)

    result = await db.events.insert_one(event_doc)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create event")

    return {
        "message": "Event created",
        "id": str(result.inserted_id)
    }

# Get all events
@app.get("/events")
async def get_events():
    events = await db.events.find().to_list(100)

    for event in events:
        event["_id"] = str(event["_id"])
    
    return events

# Get a single event
@app.get("/events/{event_id}")
async def get_event(event_id: str):
    try:
        event = await db.events.find_one({"_id": ObjectId(event_id)})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid event ID")

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event["_id"] = str(event["_id"])
    return event

# Update an event
@app.put("/events/{event_id}")
async def update_event(event_id: str, event: Event):
    try:
        event_obj_id = ObjectId(event_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid event ID")
    
    # Validate new venue reference
    venue_obj_id = await validate_object_id(
        event.venue_id, db.venues, "Venue"
    )

    update_doc = event.dict()
    update_doc["venue_id"] = str(venue_obj_id)

    result = await db.events.update_one(
        {"_id": event_obj_id},
        {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"message": "Event updated"}

# Delete an event
@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    try:    
        result = await db.events.delete_one(
            {"_id": ObjectId(event_id)}
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid event ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"message": "Event deleted"}

# Venues Endpoints
# Create a venue
@app.post("/venues")
async def create_venue(venue: Venue):
    venue_doc = venue.dict()
    result = await db.venues.insert_one(venue_doc)
    
    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create venue")
    
    return {
        "message": "Venue created",
        "id": str(result.inserted_id)
    }

# Get all venues
@app.get("/venues")
async def get_venues():
    venues = await db.venues.find().to_list(100)

    for venue in venues:
        venue["_id"] = str(venue["_id"])

    return venues

# Get a single venue
@app.get("/venues/{venue_id}")
async def get_venue(venue_id: str):
    try:
        venue = await db.venues.find_one({"_id": ObjectId(venue_id)})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid venue ID")

    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    venue["_id"] = str(venue["_id"])
    return venue

# Update a venue
@app.put("/venues/{venue_id}")
async def update_venue(venue_id: str, venue: Venue):
    try:
        result = await db.venues.update_one(
            {"_id": ObjectId(venue_id)},
            {"$set": venue.dict()}
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid venue ID")

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    return {"message": "Venue updated"}

# Delete a venue
@app.delete("/venues/{venue_id}")
async def delete_venue(venue_id: str):
    try:
        result = await db.venues.delete_one(
            {"_id": ObjectId(venue_id)}
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid venue ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    return {"message": "Venue deleted"}

# Attendees Endpoints
# Create an attendee
@app.post("/attendees")
async def create_attendee(attendee: Attendee):
    attendee_doc = attendee.dict()
    result = await db.attendees.insert_one(attendee_doc)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create attendee")
    
    return {
        "message": "Attendee created",
        "id": str(result.inserted_id)
    }

# Get all attendees
@app.get("/attendees")
async def get_attendees():
    attendees = await db.attendees.find().to_list(100)

    for attendee in attendees:
        attendee["_id"] = str(attendee["_id"])
    
    return attendees

# Get a single attendee
@app.get("/attendees/{attendee_id}")
async def get_attendee(attendee_id: str):
    try:
        attendee = await db.attendees.find_one({"_id": ObjectId(attendee_id)})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid attendee ID")

    if not attendee:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    attendee["_id"] = str(attendee["_id"])
    return attendee

# Update an attendee
@app.put("/attendees/{attendee_id}")
async def update_attendee(attendee_id: str, attendee: Attendee):
    try:
        result = await db.attendees.update_one(
            {"_id": ObjectId(attendee_id)},
            {"$set": attendee.dict()}
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid attendee ID")

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    return {"message": "Attendee updated"}

# Delete an attendee
@app.delete("/attendees/{attendee_id}")
async def delete_attendee(attendee_id: str):
    try:
        result = await db.attendees.delete_one(
            {"_id": ObjectId(attendee_id)}
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid attendee ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Attendee not found")
    
    return {"message": "Attendee deleted"}

# Bookings Endpoints
# Create a booking
@app.post("/bookings")
async def create_booking(booking: Booking):
    event_obj_id = await validate_object_id(
        booking.event_id, db.events, "Event"
    )

    attendee_obj_id = await validate_object_id(
        booking.attendee_id, db.attendees, "Attendee"
    )

    booking_doc = booking.dict()
    booking_doc["event_id"] = str(event_obj_id)
    booking_doc["attendee_id"] = str(attendee_obj_id)

    result = await db.bookings.insert_one(booking_doc)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to create booking")

    return {
        "message": "Booking created",
          "id": str(result.inserted_id)
    }

# Get all bookings
@app.get("/bookings")
async def get_bookings():
    bookings = await db.bookings.find().to_list(100)

    for booking in bookings:
        booking["_id"] = str(booking["_id"])

    return bookings

# Get a single booking
@app.get("/bookings/{booking_id}")
async def get_booking(booking_id: str):
    try:
        booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid booking ID")

    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking["_id"] = str(booking["_id"])
    return booking

# Update a booking
@app.put("/bookings/{booking_id}")
async def update_booking(booking_id: str, booking: Booking):
    try:
        booking_obj_id = ObjectId(booking_id)
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid booking ID")
    
    # Validate new event and attendee references
    event_obj_id = await validate_object_id(
        booking.event_id, db.events, "Event"
    )
    attendee_obj_id = await validate_object_id(
        booking.attendee_id, db.attendees, "Attendee"
    )

    update_doc = booking.dict()
    update_doc["event_id"] = str(event_obj_id)
    update_doc["attendee_id"] = str(attendee_obj_id)
    
    result = await db.bookings.update_one(
        {"_id": booking_obj_id},
        {"$set": update_doc}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {"message": "Booking updated"}

# Delete a booking
@app.delete("/bookings/{booking_id}")
async def delete_booking(booking_id: str):
    try:
        result = await db.bookings.delete_one(
            {"_id": ObjectId(booking_id)}
        )
    except InvalidId:
        raise HTTPException(status_code=400, detail="Invalid booking ID")

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    return {"message": "Booking deleted"}

# Upload Event Poster (Image)
@app.post("/upload_event_poster/{event_id}")
async def upload_event_poster(event_id: str, file: UploadFile = File(...)):
    await validate_object_id(event_id, db.events, "Event")

    content = await file.read()

    poster_doc = {
        "event_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    result = await db.event_posters.insert_one(poster_doc)
    return {
        "message": "Event poster uploaded", 
        "id": str(result.inserted_id)
    }


# Upload Promotional Video
@app.post("/upload_promo_video/{event_id}")
async def upload_promo_video(event_id: str, file: UploadFile = File(...)):
    await validate_object_id(event_id, db.events, "Event")

    content = await file.read()

    video_doc = {
        "event_id": event_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    result = await db.promo_videos.insert_one(video_doc)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to upload promotional video")

    return {
        "message": "Promotional video uploaded",
        "id": str(result.inserted_id)
    }

# Upload Venue Photo
@app.post("/upload_venue_photo/{venue_id}")
async def upload_venue_photo(venue_id: str, file: UploadFile = File(...)):
    await validate_object_id(venue_id, db.venues, "Venue")

    content = await file.read()

    photo_doc = {
        "venue_id": venue_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "content": content,
        "uploaded_at": datetime.utcnow()
    }

    result = await db.venue_photos.insert_one(photo_doc)

    if not result.inserted_id:
        raise HTTPException(status_code=500, detail="Failed to upload venue photo")
    
    return {
        "message": "Venue photo uploaded",
        "id": str(result.inserted_id)
    }