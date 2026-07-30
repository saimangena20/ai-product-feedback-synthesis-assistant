from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import all models so SQLAlchemy registers them
from app.models import Feedback, HistoricalTheme, Theme