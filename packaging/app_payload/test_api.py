import requests
import json

BASE = "http://127.0.0.1:8000"

# 1. Register a test user
res = requests.post(f"{BASE}/api/register", json={
    "username": "testuser_eval",
    "password": "testpass",
    "nickname": "Test User"
})
print("Register:", res.status_code, res.text)
data = res.json()
user_id = data.get("userId")

if not user_id:
    # Try login
    res = requests.post(f"{BASE}/api/login", json={
        "username": "testuser_eval",
        "password": "testpass"
    })
    print("Login:", res.status_code, res.text)
    data = res.json()
    user_id = data.get("userId")

print("User ID:", user_id)

if user_id:
    # 2. Save progress with evaluation
    evaluation = {
        "interactionCount": 5,
        "socraticPassRate": 0.8,
        "difficultyLevel": "medium",
        "codePracticeTime": 30,
        "focusTimeToday": 120,
        "flashcardsStudied": 10,
        "streakDays": 3,
        "interactionHistory": [{"date": "2026-05-09", "count": 5}],
        "lastStudyDate": "2026-05-09"
    }
    res = requests.post(f"{BASE}/api/progress/save", json={
        "userId": user_id,
        "evaluation": evaluation,
        "currentPath": [{"topic": "Test", "status": "current"}],
        "profile": {"knowledgeBase": "test"}
    })
    print("Save progress:", res.status_code, res.text)

    # 3. Load progress
    res = requests.post(f"{BASE}/api/progress/load", json={
        "userId": user_id
    })
    print("Load progress:", res.status_code, res.text)
    loaded = res.json()
    print("Loaded evaluation:", json.dumps(loaded.get("evaluation"), ensure_ascii=False, indent=2))
