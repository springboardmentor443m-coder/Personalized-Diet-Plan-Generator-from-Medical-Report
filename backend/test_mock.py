import traceback
from database import SessionLocal
from schemas import UserCreate
from api import signup

db = SessionLocal()
user = UserCreate(full_name="Mock", email="mock@test.com", password="pwd")

try:
    signup(user=user, db=db)
    print("Success")
except Exception as e:
    traceback.print_exc()
finally:
    db.close()
