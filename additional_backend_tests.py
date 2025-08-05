#!/usr/bin/env python3
"""
Additional Backend Tests for Edge Cases and Error Handling
"""

import requests
import json
import uuid

BASE_URL = "https://ee5b69f9-18a1-4296-a4c6-185ae0f92340.preview.emergentagent.com/api"

def test_duplicate_registration():
    """Test duplicate email registration"""
    print("=== Testing Duplicate Registration ===")
    
    email = f"duplicate_{uuid.uuid4().hex[:8]}@test.com"
    payload = {
        "email": email,
        "name": "Test User",
        "password": "TestPass123!",
        "role": "student"
    }
    
    # First registration
    response1 = requests.post(f"{BASE_URL}/auth/register", json=payload)
    print(f"First registration: {response1.status_code}")
    
    # Second registration with same email
    response2 = requests.post(f"{BASE_URL}/auth/register", json=payload)
    print(f"Duplicate registration: {response2.status_code}")
    
    if response2.status_code == 400:
        print("✅ PASS: Duplicate registration properly rejected")
    else:
        print("❌ FAIL: Duplicate registration should be rejected")

def test_invalid_login():
    """Test login with invalid credentials"""
    print("\n=== Testing Invalid Login ===")
    
    payload = {
        "email": "nonexistent@test.com",
        "password": "wrongpassword"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=payload)
    print(f"Invalid login response: {response.status_code}")
    
    if response.status_code == 401:
        print("✅ PASS: Invalid login properly rejected")
    else:
        print("❌ FAIL: Invalid login should return 401")

def test_unauthorized_access():
    """Test accessing protected endpoints without token"""
    print("\n=== Testing Unauthorized Access ===")
    
    endpoints = [
        "/auth/me",
        "/subjects",
        "/tasks",
        "/projects",
        "/notifications"
    ]
    
    all_passed = True
    for endpoint in endpoints:
        response = requests.get(f"{BASE_URL}{endpoint}")
        if response.status_code != 401:
            print(f"❌ FAIL: {endpoint} should require authentication")
            all_passed = False
    
    if all_passed:
        print("✅ PASS: All protected endpoints require authentication")

def test_invalid_task_operations():
    """Test operations on non-existent tasks"""
    print("\n=== Testing Invalid Task Operations ===")
    
    # Create a student first
    student_email = f"student_{uuid.uuid4().hex[:8]}@test.com"
    payload = {
        "email": student_email,
        "name": "Test Student",
        "password": "TestPass123!",
        "role": "student"
    }
    
    reg_response = requests.post(f"{BASE_URL}/auth/register", json=payload)
    if reg_response.status_code != 200:
        print("❌ FAIL: Could not create test student")
        return
    
    token = reg_response.json()['access_token']
    headers = {"Authorization": f"Bearer {token}"}
    
    # Try to update non-existent task
    fake_task_id = str(uuid.uuid4())
    update_response = requests.put(
        f"{BASE_URL}/tasks/{fake_task_id}",
        json={"completed": True},
        headers=headers
    )
    
    # Try to delete non-existent task
    delete_response = requests.delete(
        f"{BASE_URL}/tasks/{fake_task_id}",
        headers=headers
    )
    
    if update_response.status_code == 404 and delete_response.status_code == 404:
        print("✅ PASS: Operations on non-existent tasks properly rejected")
    else:
        print(f"❌ FAIL: Expected 404 for non-existent tasks, got {update_response.status_code}, {delete_response.status_code}")

def test_cross_user_access():
    """Test that users cannot access each other's data"""
    print("\n=== Testing Cross-User Access Control ===")
    
    # Create two students
    students = []
    for i in range(2):
        email = f"student{i}_{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "name": f"Student {i}",
            "password": "TestPass123!",
            "role": "student"
        }
        
        response = requests.post(f"{BASE_URL}/auth/register", json=payload)
        if response.status_code == 200:
            students.append({
                'token': response.json()['access_token'],
                'id': response.json()['user']['id']
            })
    
    if len(students) != 2:
        print("❌ FAIL: Could not create test students")
        return
    
    # Student 1 creates a task
    headers1 = {"Authorization": f"Bearer {students[0]['token']}"}
    subjects_response = requests.get(f"{BASE_URL}/subjects", headers=headers1)
    
    if subjects_response.status_code != 200:
        print("❌ FAIL: Could not get subjects")
        return
    
    subjects = subjects_response.json()
    if not subjects:
        print("❌ FAIL: No subjects available")
        return
    
    task_payload = {
        "title": "Private Task",
        "subject_id": subjects[0]['id'],
        "priority": "medium"
    }
    
    task_response = requests.post(f"{BASE_URL}/tasks", json=task_payload, headers=headers1)
    if task_response.status_code != 200:
        print("❌ FAIL: Could not create task")
        return
    
    task_id = task_response.json()['id']
    
    # Student 2 tries to access Student 1's task
    headers2 = {"Authorization": f"Bearer {students[1]['token']}"}
    access_response = requests.put(
        f"{BASE_URL}/tasks/{task_id}",
        json={"completed": True},
        headers=headers2
    )
    
    if access_response.status_code == 404:
        print("✅ PASS: Cross-user task access properly denied")
    else:
        print(f"❌ FAIL: Cross-user access should be denied, got {access_response.status_code}")

if __name__ == "__main__":
    print("🔍 Running Additional Backend Tests")
    print("=" * 50)
    
    test_duplicate_registration()
    test_invalid_login()
    test_unauthorized_access()
    test_invalid_task_operations()
    test_cross_user_access()
    
    print("\n✅ Additional testing completed!")