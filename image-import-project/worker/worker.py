from celery import Celery
import sqlalchemy as db
from sqlalchemy.exc import SQLAlchemyError
import time
import os

# Setup Celery with configuration
app = Celery(
    'tasks',
    broker='redis://redis:6379/0',
    backend='redis://redis:6379/0'  # Optional: for storing task results
)

# Celery configuration
app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
)

# Database setup
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://admin:password123@postgres:5432/images_db'
)

try:
    engine = db.create_engine(DATABASE_URL, pool_pre_ping=True)
    print(f"Database connection established to: {DATABASE_URL}")
except Exception as e:
    print(f"Database connection error: {e}")
    engine = None

# Create images table (run once)
def create_images_table():
    """Create the images table if it doesn't exist"""
    if engine is None:
        print("Cannot create table: No database connection")
        return
    
    try:
        metadata = db.MetaData()
        images = db.Table(
            'images',
            metadata,
            db.Column('id', db.Integer, primary_key=True),
            db.Column('name', db.String(255)),
            db.Column('google_drive_id', db.String(255)),
            db.Column('size', db.Integer),
            db.Column('mime_type', db.String(100)),
            db.Column('storage_url', db.String(500)),
            db.Column('source', db.String(50), default='google_drive'),
            db.Column('created_at', db.TIMESTAMP, server_default=db.func.now()),
            db.Column('status', db.String(20), default='imported')
        )
        metadata.create_all(engine, checkfirst=True)
        print("Images table created/verified successfully")
    except SQLAlchemyError as e:
        print(f"Error creating table: {e}")

# Call this once when worker starts
create_images_table()

# Simple task - this simulates importing images
@app.task(bind=True, max_retries=3)
def import_google_drive_images(self, folder_url: str, task_id: str):
    """
    Simulate importing images from Google Drive
    In real app, this would connect to Google Drive API and S3
    """
    print(f"Starting import task {task_id} from: {folder_url}")
    
    try:
        # Simulate work
        time.sleep(2)
        
        if engine is None:
            raise Exception("Database not connected")
        
        with engine.connect() as connection:
            # Verify table exists
            metadata = db.MetaData()
            metadata.reflect(bind=engine)
            
            if 'images' not in metadata.tables:
                print("Creating images table...")
                create_images_table()
                metadata.reflect(bind=engine)
            
            images_table = metadata.tables['images']
            
            # Add some dummy images (in real app, these come from Google Drive)
            dummy_images = [
                {
                    "name": "sample1.jpg",
                    "google_drive_id": f"drive_{task_id}_1",
                    "size": 204800,
                    "mime_type": "image/jpeg",
                    "storage_url": "https://via.placeholder.com/300x200/0088cc/ffffff?text=Sample+1",
                    "source": "google_drive",
                    "status": "imported"
                },
                {
                    "name": "sample2.png",
                    "google_drive_id": f"drive_{task_id}_2",
                    "size": 102400,
                    "mime_type": "image/png",
                    "storage_url": "https://via.placeholder.com/400x300/00aa66/ffffff?text=Sample+2",
                    "source": "google_drive",
                    "status": "imported"
                },
                {
                    "name": "sample3.jpg",
                    "google_drive_id": f"drive_{task_id}_3",
                    "size": 307200,
                    "mime_type": "image/jpeg",
                    "storage_url": "https://via.placeholder.com/500x400/aa44cc/ffffff?text=Sample+3",
                    "source": "google_drive",
                    "status": "imported"
                }
            ]
            
            inserted_count = 0
            for img in dummy_images:
                try:
                    result = connection.execute(
                        db.insert(images_table).values(**img)
                    )
                    inserted_count += 1
                except SQLAlchemyError as e:
                    print(f"Error inserting image {img['name']}: {e}")
                    continue
            
            connection.commit()
            print(f"Import completed for: {folder_url}. Inserted {inserted_count} images.")
            
            return {
                "status": "completed",
                "task_id": task_id,
                "images_imported": inserted_count,
                "folder_url": folder_url
            }
            
    except Exception as e:
        print(f"Error in import task {task_id}: {e}")
        
        # Retry logic (Celery will handle this with @app.task(bind=True))
        try:
            raise self.retry(exc=e, countdown=60)  # Retry after 60 seconds
        except Exception as retry_error:
            print(f"Retry failed for task {task_id}: {retry_error}")
            return {
                "status": "failed",
                "task_id": task_id,
                "error": str(e),
                "folder_url": folder_url
            }

# Optional: Add a simple ping task for health checks
@app.task
def ping():
    """Simple task for health checking"""
    return {"status": "pong", "service": "image-import-worker"}

# Celery startup
if __name__ == '__main__':
    app.start()