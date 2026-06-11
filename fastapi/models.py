from sqlalchemy import Column, Integer, String, Float, Date
from database import Base


class PurchaseRecord(Base):
    __tablename__ = "purchases"

    id = Column(Integer, primary_key=True, index=True)
    customer_name = Column(String, nullable=False, index=True)
    country = Column(String, nullable=False, index=True)
    purchase_date = Column(Date, nullable=False, index=True)
    amount = Column(Float, nullable=False)
