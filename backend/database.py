from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import datetime
import os

# 使用 SQLite 資料庫
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./educareer.db")

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Department(Base):
    __tablename__ = "departments"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    school_name = Column(String, nullable=False, index=True)
    department_name = Column(String, nullable=False, index=True)
    study_field = Column(String, nullable=False)  # 學門分類
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class EnrollmentStat(Base):
    __tablename__ = "enrollment_stats"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    academic_year = Column(Integer, nullable=False)  # 學年度
    student_count = Column(Integer, nullable=False)  # 在學學生數
    freshman_registration_rate = Column(Float, nullable=True)  # 新生註冊率
    
    department = relationship("Department")

class SalaryTrend(Base):
    __tablename__ = "salary_trends"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    study_field = Column(String, nullable=False, index=True)  # 學門分類
    years_after_graduation = Column(Integer, nullable=False)  # 畢業後年資 (如 1年, 3年, 5年)
    average_salary = Column(Float, nullable=False)  # 平均薪資 (連續數值)
    record_year = Column(Integer, nullable=False)  # 統計年份

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
