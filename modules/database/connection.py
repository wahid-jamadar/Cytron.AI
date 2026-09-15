from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from config.settings import settings

# Create SQLAlchemy engine for MySQL
engine = create_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_recycle=3600,
    pool_pre_ping=True
)

# Create session maker
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for declarative models
Base = declarative_base()

def get_db():
    """Dependency that provides a transactional database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
