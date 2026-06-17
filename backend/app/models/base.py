"""
app/models/base.py
Declarative base shared by every model.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
