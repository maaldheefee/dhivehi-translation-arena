from pathlib import Path

from sqlalchemy import create_engine

from app.models import Base

# Ensure the data directory exists
Path("data").mkdir(parents=True, exist_ok=True)

# Create the database
engine = create_engine("sqlite:///data/translations.db")
Base.metadata.create_all(engine)

print("Database initialized successfully!")
