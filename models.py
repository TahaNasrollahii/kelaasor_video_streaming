from sqlalchemy import Column, BigInteger, String, Float
from database import Base

class BootcampMedia(Base):
    __tablename__ = "courses_bootcampmedia"
    
    id = Column(BigInteger, primary_key=True, index=True)
    file = Column(String(255))
    status = Column(String(20), default="pending")
    hls_path = Column(String(512), default="")
    error_message = Column(String, default="")
    duration = Column(Float, nullable=True)
