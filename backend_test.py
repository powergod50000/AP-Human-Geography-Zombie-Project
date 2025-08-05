#!/usr/bin/env python3
"""
Comprehensive Backend API Testing for School Work Organizer
Tests all authentication, CRUD operations, role permissions, and parent-student relationships
"""

import requests
import json
from datetime import datetime, timedelta
import uuid

# Backend URL from environment
BASE_URL = "https://ee5b69f9-18a1-4296-a4c6-185ae0f92340.preview.emergentagent.com/api"

class BackendTester:
    def __init__(self):
        self.student_token = None
        self.parent_token = None
        self.student_data = None
        self.parent_data = None
        self.test_results = []
        self.created_resources = {
            'subjects': [],
            'tasks': [],
            'projects': [],
            'project_tasks': [],
            'invites': []
        }

    def log_test(self, test_name, success, message="", details=None):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   Details: {details}")
        
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message,
            'details': details
        })

    def test_student_registration(self):
        """Test student registration with default subjects creation"""
        print("\n=== Testing Student Registration ===")
        
        student_email = f"student_{uuid.uuid4().hex[:8]}@school.edu"
        payload = {
            "email": student_email,
            "name": "Emma Johnson",
            "password": "StudentPass123!",
            "role": "student"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/register", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                self.student_token = data['access_token']
                self.student_data = data['user']
                
                # Verify response structure
                required_fields = ['access_token', 'token_type', 'user']
                user_fields = ['id', 'email', 'name', 'role']
                
                missing_fields = [f for f in required_fields if f not in data]
                missing_user_fields = [f for f in user_fields if f not in data['user']]
                
                if missing_fields or missing_user_fields:
                    self.log_test("Student Registration", False, 
                                f"Missing fields: {missing_fields + missing_user_fields}")
                else:
                    self.log_test("Student Registration", True, 
                                f"Student registered successfully: {data['user']['name']}")
                    
                    # Test if default subjects were created
                    self.test_default_subjects_creation()
            else:
                self.log_test("Student Registration", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Student Registration", False, f"Exception: {str(e)}")

    def test_default_subjects_creation(self):
        """Test that default subjects are created for new students"""
        print("\n=== Testing Default Subjects Creation ===")
        
        if not self.student_token:
            self.log_test("Default Subjects Creation", False, "No student token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = requests.get(f"{BASE_URL}/subjects", headers=headers)
            
            if response.status_code == 200:
                subjects = response.json()
                expected_subjects = ["Mathematics", "Science", "English", "History", 
                                   "Geography", "Art", "Physical Education", "Music"]
                
                subject_names = [s['name'] for s in subjects]
                missing_subjects = [s for s in expected_subjects if s not in subject_names]
                
                if len(subjects) >= 8 and not missing_subjects:
                    self.log_test("Default Subjects Creation", True, 
                                f"Created {len(subjects)} default subjects")
                    self.created_resources['subjects'] = subjects
                else:
                    self.log_test("Default Subjects Creation", False, 
                                f"Expected 8+ subjects, got {len(subjects)}. Missing: {missing_subjects}")
            else:
                self.log_test("Default Subjects Creation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Default Subjects Creation", False, f"Exception: {str(e)}")

    def test_student_login(self):
        """Test student login"""
        print("\n=== Testing Student Login ===")
        
        if not self.student_data:
            self.log_test("Student Login", False, "No student data available for login test")
            return
            
        payload = {
            "email": self.student_data['email'],
            "password": "StudentPass123!"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/login", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                if 'access_token' in data and data['user']['role'] == 'student':
                    self.log_test("Student Login", True, "Student login successful")
                else:
                    self.log_test("Student Login", False, "Invalid login response structure")
            else:
                self.log_test("Student Login", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Student Login", False, f"Exception: {str(e)}")

    def test_auth_me_endpoint(self):
        """Test /auth/me endpoint"""
        print("\n=== Testing Auth Me Endpoint ===")
        
        if not self.student_token:
            self.log_test("Auth Me Endpoint", False, "No student token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['id', 'email', 'name', 'role']
                missing_fields = [f for f in required_fields if f not in data]
                
                if not missing_fields and data['role'] == 'student':
                    self.log_test("Auth Me Endpoint", True, "User info retrieved successfully")
                else:
                    self.log_test("Auth Me Endpoint", False, 
                                f"Missing fields or wrong role: {missing_fields}")
            else:
                self.log_test("Auth Me Endpoint", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Auth Me Endpoint", False, f"Exception: {str(e)}")

    def test_task_creation(self):
        """Test task creation"""
        print("\n=== Testing Task Creation ===")
        
        if not self.student_token or not self.created_resources['subjects']:
            self.log_test("Task Creation", False, "Missing student token or subjects")
            return
            
        subject_id = self.created_resources['subjects'][0]['id']
        payload = {
            "title": "Complete Math Homework Chapter 5",
            "description": "Solve problems 1-20 from algebra chapter",
            "subject_id": subject_id,
            "due_date": (datetime.now() + timedelta(days=3)).isoformat(),
            "priority": "high"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = requests.post(f"{BASE_URL}/tasks", json=payload, headers=headers)
            
            if response.status_code == 200:
                task = response.json()
                required_fields = ['id', 'title', 'subject_id', 'student_id', 'completed', 'priority']
                missing_fields = [f for f in required_fields if f not in task]
                
                if not missing_fields:
                    self.log_test("Task Creation", True, f"Task created: {task['title']}")
                    self.created_resources['tasks'].append(task)
                else:
                    self.log_test("Task Creation", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Task Creation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Task Creation", False, f"Exception: {str(e)}")

    def test_task_completion_and_notifications(self):
        """Test task completion and parent notifications"""
        print("\n=== Testing Task Completion & Notifications ===")
        
        if not self.created_resources['tasks']:
            self.log_test("Task Completion", False, "No tasks available to complete")
            return
            
        task = self.created_resources['tasks'][0]
        payload = {"completed": True}
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = requests.put(f"{BASE_URL}/tasks/{task['id']}", 
                                  json=payload, headers=headers)
            
            if response.status_code == 200:
                updated_task = response.json()
                if updated_task['completed'] and 'completed_at' in updated_task:
                    self.log_test("Task Completion", True, 
                                f"Task completed successfully: {updated_task['title']}")
                else:
                    self.log_test("Task Completion", False, 
                                "Task not properly marked as completed")
            else:
                self.log_test("Task Completion", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Task Completion", False, f"Exception: {str(e)}")

    def test_project_creation(self):
        """Test project creation"""
        print("\n=== Testing Project Creation ===")
        
        if not self.student_token or not self.created_resources['subjects']:
            self.log_test("Project Creation", False, "Missing student token or subjects")
            return
            
        subject_id = self.created_resources['subjects'][1]['id']  # Use Science subject
        payload = {
            "name": "Solar System Research Project",
            "description": "Research and create presentation about planets",
            "subject_id": subject_id
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = requests.post(f"{BASE_URL}/projects", json=payload, headers=headers)
            
            if response.status_code == 200:
                project = response.json()
                required_fields = ['id', 'name', 'subject_id', 'student_id']
                missing_fields = [f for f in required_fields if f not in project]
                
                if not missing_fields:
                    self.log_test("Project Creation", True, f"Project created: {project['name']}")
                    self.created_resources['projects'].append(project)
                else:
                    self.log_test("Project Creation", False, f"Missing fields: {missing_fields}")
            else:
                self.log_test("Project Creation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Project Creation", False, f"Exception: {str(e)}")

    def test_project_task_management(self):
        """Test Kanban project task management"""
        print("\n=== Testing Project Task Management ===")
        
        if not self.created_resources['projects']:
            self.log_test("Project Task Management", False, "No projects available")
            return
            
        project = self.created_resources['projects'][0]
        
        # Create project tasks in different statuses
        tasks_to_create = [
            {"title": "Research planet facts", "status": "todo"},
            {"title": "Create presentation slides", "status": "in_progress"},
            {"title": "Practice presentation", "status": "todo"}
        ]
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            
            for task_data in tasks_to_create:
                response = requests.post(
                    f"{BASE_URL}/projects/{project['id']}/tasks",
                    json=task_data, headers=headers
                )
                
                if response.status_code == 200:
                    task = response.json()
                    self.created_resources['project_tasks'].append(task)
                else:
                    self.log_test("Project Task Management", False, 
                                f"Failed to create task: {response.text}")
                    return
            
            # Test updating task status (Kanban movement)
            if self.created_resources['project_tasks']:
                task_to_update = self.created_resources['project_tasks'][0]
                update_payload = {"status": "done"}
                
                response = requests.put(
                    f"{BASE_URL}/projects/{project['id']}/tasks/{task_to_update['id']}",
                    json=update_payload, headers=headers
                )
                
                if response.status_code == 200:
                    updated_task = response.json()
                    if updated_task['status'] == 'done':
                        self.log_test("Project Task Management", True, 
                                    f"Created {len(self.created_resources['project_tasks'])} project tasks and updated status")
                    else:
                        self.log_test("Project Task Management", False, 
                                    "Task status not updated properly")
                else:
                    self.log_test("Project Task Management", False, 
                                f"Failed to update task status: {response.text}")
            
        except Exception as e:
            self.log_test("Project Task Management", False, f"Exception: {str(e)}")

    def test_parent_registration(self):
        """Test parent registration"""
        print("\n=== Testing Parent Registration ===")
        
        parent_email = f"parent_{uuid.uuid4().hex[:8]}@family.com"
        payload = {
            "email": parent_email,
            "name": "Sarah Johnson",
            "password": "ParentPass123!",
            "role": "parent"
        }
        
        try:
            response = requests.post(f"{BASE_URL}/auth/register", json=payload)
            
            if response.status_code == 200:
                data = response.json()
                self.parent_token = data['access_token']
                self.parent_data = data['user']
                
                if data['user']['role'] == 'parent':
                    self.log_test("Parent Registration", True, 
                                f"Parent registered successfully: {data['user']['name']}")
                else:
                    self.log_test("Parent Registration", False, "Wrong role assigned")
            else:
                self.log_test("Parent Registration", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Parent Registration", False, f"Exception: {str(e)}")

    def test_parent_invitation_system(self):
        """Test parent invitation system"""
        print("\n=== Testing Parent Invitation System ===")
        
        if not self.student_token or not self.parent_data:
            self.log_test("Parent Invitation System", False, "Missing tokens or parent data")
            return
            
        # Student invites parent
        payload = {"parent_email": self.parent_data['email']}
        
        try:
            headers = {"Authorization": f"Bearer {self.student_token}"}
            response = requests.post(f"{BASE_URL}/invite-parent", json=payload, headers=headers)
            
            if response.status_code == 200:
                invite_data = response.json()
                invite_code = invite_data.get('invite_code')
                
                if invite_code:
                    self.log_test("Parent Invitation", True, 
                                f"Invitation sent with code: {invite_code}")
                    
                    # Parent accepts invite
                    self.test_parent_accept_invite(invite_code)
                else:
                    self.log_test("Parent Invitation", False, "No invite code returned")
            else:
                self.log_test("Parent Invitation", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Parent Invitation System", False, f"Exception: {str(e)}")

    def test_parent_accept_invite(self, invite_code):
        """Test parent accepting invitation"""
        print("\n=== Testing Parent Accept Invite ===")
        
        if not self.parent_token:
            self.log_test("Parent Accept Invite", False, "No parent token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.parent_token}"}
            # Note: The API expects invite_code as a query parameter based on the endpoint
            response = requests.post(f"{BASE_URL}/accept-invite?invite_code={invite_code}", 
                                   headers=headers)
            
            if response.status_code == 200:
                self.log_test("Parent Accept Invite", True, "Invite accepted successfully")
                # Now test parent dashboard
                self.test_parent_dashboard()
            else:
                self.log_test("Parent Accept Invite", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Parent Accept Invite", False, f"Exception: {str(e)}")

    def test_parent_dashboard(self):
        """Test parent dashboard viewing student data"""
        print("\n=== Testing Parent Dashboard ===")
        
        if not self.parent_token:
            self.log_test("Parent Dashboard", False, "No parent token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.parent_token}"}
            response = requests.get(f"{BASE_URL}/parent/students", headers=headers)
            
            if response.status_code == 200:
                students_data = response.json()
                
                if isinstance(students_data, list) and len(students_data) > 0:
                    student = students_data[0]
                    required_fields = ['student', 'stats']
                    student_fields = ['id', 'name', 'email']
                    stats_fields = ['total_tasks', 'completed_tasks', 'pending_tasks', 'total_projects']
                    
                    missing_fields = [f for f in required_fields if f not in student]
                    missing_student_fields = [f for f in student_fields if f not in student.get('student', {})]
                    missing_stats_fields = [f for f in stats_fields if f not in student.get('stats', {})]
                    
                    if not (missing_fields or missing_student_fields or missing_stats_fields):
                        self.log_test("Parent Dashboard", True, 
                                    f"Parent can view {len(students_data)} student(s) with complete stats")
                    else:
                        self.log_test("Parent Dashboard", False, 
                                    f"Missing fields in response: {missing_fields + missing_student_fields + missing_stats_fields}")
                else:
                    self.log_test("Parent Dashboard", False, "No student data returned")
            else:
                self.log_test("Parent Dashboard", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Parent Dashboard", False, f"Exception: {str(e)}")

    def test_role_based_access_control(self):
        """Test role-based access control"""
        print("\n=== Testing Role-Based Access Control ===")
        
        if not self.parent_token or not self.created_resources['subjects']:
            self.log_test("Role-Based Access Control", False, "Missing parent token or subjects")
            return
            
        # Test that parent cannot create tasks (should fail)
        subject_id = self.created_resources['subjects'][0]['id']
        payload = {
            "title": "Unauthorized task",
            "subject_id": subject_id,
            "priority": "medium"
        }
        
        try:
            headers = {"Authorization": f"Bearer {self.parent_token}"}
            response = requests.post(f"{BASE_URL}/tasks", json=payload, headers=headers)
            
            if response.status_code == 403:
                self.log_test("Role-Based Access Control", True, 
                            "Parent correctly denied task creation access")
            else:
                self.log_test("Role-Based Access Control", False, 
                            f"Parent should be denied access, got HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Role-Based Access Control", False, f"Exception: {str(e)}")

    def test_notifications_system(self):
        """Test notifications system"""
        print("\n=== Testing Notifications System ===")
        
        if not self.parent_token:
            self.log_test("Notifications System", False, "No parent token available")
            return
            
        try:
            headers = {"Authorization": f"Bearer {self.parent_token}"}
            response = requests.get(f"{BASE_URL}/notifications", headers=headers)
            
            if response.status_code == 200:
                notifications = response.json()
                
                if isinstance(notifications, list):
                    # Check if we have notifications from task completion
                    task_notifications = [n for n in notifications if 'task' in n.get('message', '').lower()]
                    
                    if task_notifications:
                        # Test marking notification as read
                        notification_id = task_notifications[0]['id']
                        read_response = requests.put(
                            f"{BASE_URL}/notifications/{notification_id}/read",
                            headers=headers
                        )
                        
                        if read_response.status_code == 200:
                            self.log_test("Notifications System", True, 
                                        f"Retrieved {len(notifications)} notifications and marked one as read")
                        else:
                            self.log_test("Notifications System", False, 
                                        f"Failed to mark notification as read: {read_response.text}")
                    else:
                        self.log_test("Notifications System", True, 
                                    f"Retrieved {len(notifications)} notifications (no task notifications yet)")
                else:
                    self.log_test("Notifications System", False, "Invalid notifications response format")
            else:
                self.log_test("Notifications System", False, 
                            f"HTTP {response.status_code}: {response.text}")
                
        except Exception as e:
            self.log_test("Notifications System", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all backend tests in sequence"""
        print("🚀 Starting Comprehensive Backend API Testing")
        print(f"Testing against: {BASE_URL}")
        print("=" * 60)
        
        # Authentication and User Management
        self.test_student_registration()
        self.test_student_login()
        self.test_auth_me_endpoint()
        
        # Core Features
        self.test_task_creation()
        self.test_task_completion_and_notifications()
        self.test_project_creation()
        self.test_project_task_management()
        
        # Parent System
        self.test_parent_registration()
        self.test_parent_invitation_system()
        
        # Security and Permissions
        self.test_role_based_access_control()
        self.test_notifications_system()
        
        # Print summary
        self.print_test_summary()

    def print_test_summary(self):
        """Print comprehensive test summary"""
        print("\n" + "=" * 60)
        print("🏁 BACKEND TESTING SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.test_results if result['success'])
        total = len(self.test_results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        print("\n📋 DETAILED RESULTS:")
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            print(f"{status} {result['test']}: {result['message']}")
        
        if total - passed > 0:
            print("\n🚨 FAILED TESTS:")
            for result in self.test_results:
                if not result['success']:
                    print(f"❌ {result['test']}: {result['message']}")
                    if result['details']:
                        print(f"   Details: {result['details']}")

if __name__ == "__main__":
    tester = BackendTester()
    tester.run_all_tests()