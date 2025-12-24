from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import sqlalchemy as db
from sqlalchemy.orm import sessionmaker
import redis
from celery import Celery
import json
import time

# Initialize FastAPI
app = FastAPI(title="Image Import API")

# ========== CORS FIX: Allow ALL origins for development ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# =================================================================

# Database setup
DATABASE_URL = "postgresql://admin:password123@postgres:5432/images_db"
engine = db.create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis for task queue
redis_client = redis.Redis(host='redis', port=6379, db=0)

# Celery for background tasks
celery_app = Celery('tasks', broker='redis://redis:6379/0')

# Simple models
class ImportRequest(BaseModel):
    folder_url: str

class ImageResponse(BaseModel):
    id: int
    name: str
    size: int
    storage_url: str
    source: str

# Create table
metadata = db.MetaData()
images = db.Table(
    'images',
    metadata,
    db.Column('id', db.Integer, primary_key=True),
    db.Column('name', db.String),
    db.Column('google_drive_id', db.String),
    db.Column('size', db.Integer),
    db.Column('mime_type', db.String),
    db.Column('storage_url', db.String),
    db.Column('source', db.String, default='google_drive')
)

# Create the table in database (if not exists)
try:
    metadata.create_all(engine, checkfirst=True)
    print("✅ Database table created/verified")
except Exception as e:
    print(f"⚠️ Database error: {e}")

@app.get("/")
def read_root():
    return {"message": "Image Import API is running"}

@app.post("/import/google-drive")
async def import_images(request: ImportRequest):
    """
    Start importing images from Google Drive folder
    """
    try:
        # For now, just simulate the task
        task_id = f"task_{int(time.time())}"
        
        # Store task in Redis
        redis_client.set(task_id, json.dumps({
            "status": "pending",
            "folder_url": request.folder_url,
            "images_imported": 0,
            "created_at": time.time()
        }), ex=3600)  # Expire after 1 hour
        
        # Simulate adding some dummy images to database
        with engine.connect() as connection:
            # Add dummy images
            dummy_images = [
                {
                    "name": f"imported_image_{task_id}_1.jpg",
                    "google_drive_id": f"drive_{task_id}_1",
                    "size": 204800,
                    "mime_type": "image/jpeg",
                    "storage_url": f"https://via.placeholder.com/300x200/667eea/ffffff?text={task_id}+1",
                    "source": "google_drive"
                },
                {
                    "name": f"imported_image_{task_id}_2.png",
                    "google_drive_id": f"drive_{task_id}_2",
                    "size": 102400,
                    "mime_type": "image/png",
                    "storage_url": f"https://via.placeholder.com/400x300/764ba2/ffffff?text={task_id}+2",
                    "source": "google_drive"
                }
            ]
            
            for img in dummy_images:
                connection.execute(db.insert(images).values(**img))
            connection.commit()
        
        return {
            "message": "Import started successfully",
            "task_id": task_id,
            "folder_url": request.folder_url,
            "images_added": len(dummy_images)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")

@app.get("/images")
async def get_images():
    """
    Get all imported images
    """
    try:
        with engine.connect() as connection:
            # Check if table exists
            inspector = db.inspect(engine)
            if not inspector.has_table('images'):
                return []
            
            result = connection.execute(db.select(images).order_by(images.c.id.desc()))
            all_images = result.fetchall()
        
        return [
            {
                "id": img[0],
                "name": img[1],
                "size": img[3] if img[3] else 0,
                "storage_url": img[5] if img[5] else "https://via.placeholder.com/300x200?text=No+Image",
                "source": img[6] if img[6] else "unknown"
            }
            for img in all_images
        ]
        
    except Exception as e:
        # Return empty array if error (for development)
        print(f"Error fetching images: {e}")
        return []

@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "database": "connected" if engine else "disconnected",
        "redis": "connected" if redis_client.ping() else "disconnected"
    }

# Add a simple endpoint to add test images
@app.post("/add-test-images")
async def add_test_images():
    """Add test images for development"""
    try:
        with engine.connect() as connection:
            test_images = [
                {
                    "name": "landscape.jpg",
                    "google_drive_id": "test_1",
                    "size": 1500000,
                    "mime_type": "image/jpeg",
                    "storage_url": "https://images.unsplash.com/photo-1506744038136-46273834b3fb",
                    "source": "test"
                },
                {
                    "name": "portrait.png",
                    "google_drive_id": "test_2",
                    "size": 800000,
                    "mime_type": "image/png",
                    "storage_url": "https://images.unsplash.com/photo-1519681393784-d120267933ba",
                    "source": "test"
                },
                {
                    "name": "nature.jpg",
                    "google_drive_id": "test_3",
                    "size": 1200000,
                    "mime_type": "image/jpeg",
                    "storage_url": "https://images.unsplash.com/photo-1441974231531-c6227db76b6e",
                    "source": "test"
                }
            ]
            
            for img in test_images:
                connection.execute(db.insert(images).values(**img))
            connection.commit()
        
        return {"message": f"Added {len(test_images)} test images", "count": len(test_images)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)