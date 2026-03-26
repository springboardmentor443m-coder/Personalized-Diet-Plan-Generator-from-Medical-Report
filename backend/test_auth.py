import requests

print("Testing Signup...")
r1 = requests.post("http://127.0.0.1:8000/signup", json={"full_name": "Test User", "email": "test@test.com", "password": "password123"})
print(r1.status_code, r1.text)

print("Testing Login...")
r2 = requests.post("http://127.0.0.1:8000/login", data={"username": "test@test.com", "password": "password123"})
print(r2.status_code, r2.json())

if r2.status_code == 200:
    token = r2.json().get("access_token")
    print("Testing Me API...")
    r3 = requests.get("http://127.0.0.1:8000/me", headers={"Authorization": f"Bearer {token}"})
    print(r3.status_code, r3.json())
