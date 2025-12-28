import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from bson import ObjectId
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

# Event Endpoints

# Create an event
@app.post("/events")
async def create_event(event: Event):
    event_doc = event.dict()
    result = await db.events.insert_one(event_doc)
    return {"message": "Event created", "id": str(result.inserted_id)}

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
    except:
        raise HTTPException(status_code=400, detail="Invalid event ID")

    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    
    event["_id"] = str(event["_id"])
    return event

# Update an event
@app.put("/events/{event_id}")
async def update_event(event_id: str, event: Event):
    result = await db.events.update_one(
        {"_id": ObjectId(event_id)},
        {"$set": event.dict()}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"message": "Event updated"}

# Delete an event
@app.delete("/events/{event_id}")
async def delete_event(event_id: str):
    result = await db.events.delete_one(
        {"_id": ObjectId(event_id)}
    )

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Event not found")
    
    return {"message": "Event deleted"}

# Upload Event Poster (Image)
@app.post("/upload_event_poster/{event_id}")
async def upload_event_poster(event_id: str, file: UploadFile = File(...)):
    content = await file.read()
    poster_doc = {
    "event_id": event_id,
    "filename": file.filename,
    "content_type": file.content_type,
    "content": content,
    "uploaded_at": datetime.utcnow()
    }
    result = await db.event_posters.insert_one(poster_doc)
    return {"message": "Event poster uploaded", "id": str(result.inserted_id)}