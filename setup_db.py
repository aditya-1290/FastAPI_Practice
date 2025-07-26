from database import Base, engine
import models
import time
from sqlalchemy.exc import OperationalError

def setup_database_with_retry(max_retries=3):
    for attempt in range(max_retries):
        try:
            Base.metadata.create_all(bind=engine)
            print("Database tables created successfully")
            return
        except OperationalError as e:
            if "Deadlock" in str(e):
                print(f"Deadlock encountered, retrying ({attempt + 1}/{max_retries})")
                time.sleep(1)  # Wait before retrying
                continue
            raise
    raise Exception("Failed to create tables after multiple retries")

if __name__ == "__main__":
    setup_database_with_retry()