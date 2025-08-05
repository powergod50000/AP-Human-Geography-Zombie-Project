from fastapi import FastAPI, APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional
import uuid
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
# Email imports removed - using basic print for notifications

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# JWT and Password settings
SECRET_KEY = "your-secret-key-here"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Models
class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    name: str
    role: str  # "student" or "parent"
    hashed_password: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = True

class UserCreate(BaseModel):
    email: EmailStr
    name: str
    password: str
    role: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Subject(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    color: str
    student_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SubjectCreate(BaseModel):
    name: str
    color: str

class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    subject_id: str
    student_id: str
    due_date: Optional[datetime] = None
    completed: bool = False
    priority: str = "medium"  # low, medium, high
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

class TaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    subject_id: str
    due_date: Optional[datetime] = None
    priority: str = "medium"

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    subject_id: Optional[str] = None
    due_date: Optional[datetime] = None
    priority: Optional[str] = None
    completed: Optional[bool] = None

class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: Optional[str] = None
    subject_id: str
    student_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    subject_id: str

class ProjectTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    description: Optional[str] = None
    project_id: str
    student_id: str
    status: str = "todo"  # todo, in_progress, done
    due_date: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ProjectTaskCreate(BaseModel):
    title: str
    description: Optional[str] = None
    status: str = "todo"
    due_date: Optional[datetime] = None

class ParentInvite(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    student_id: str
    parent_email: EmailStr
    invite_code: str
    accepted: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ParentInviteCreate(BaseModel):
    parent_email: EmailStr

class ParentStudentRelation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str
    student_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Notification(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str
    title: str
    message: str
    type: str  # task_completed, task_due, parent_invite
    read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

# Auth helper functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# Send email notification (basic implementation)
async def send_email_notification(to_email: str, subject: str, body: str):
    try:
        # Basic email implementation - in production use proper email service
        print(f"EMAIL TO: {to_email}")
        print(f"SUBJECT: {subject}")
        print(f"BODY: {body}")
        # You would implement actual email sending here
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

# Default subjects
DEFAULT_SUBJECTS = [
    {"name": "Mathematics", "color": "#3B82F6"},
    {"name": "Science", "color": "#10B981"},
    {"name": "English", "color": "#F59E0B"},
    {"name": "History", "color": "#EF4444"},
    {"name": "Geography", "color": "#8B5CF6"},
    {"name": "Art", "color": "#EC4899"},
    {"name": "Physical Education", "color": "#06B6D4"},
    {"name": "Music", "color": "#84CC16"},
]

# Authentication endpoints
@api_router.post("/auth/register")
async def register(user_data: UserCreate):
    # Check if user exists
    existing_user = await db.users.find_one({"email": user_data.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        name=user_data.name,
        role=user_data.role,
        hashed_password=hashed_password
    )
    
    await db.users.insert_one(user.dict())
    
    # Create default subjects for students
    if user_data.role == "student":
        for subject_data in DEFAULT_SUBJECTS:
            subject = Subject(
                name=subject_data["name"],
                color=subject_data["color"],
                student_id=user.id
            )
            await db.subjects.insert_one(subject.dict())
    
    # Create access token
    access_token = create_access_token(data={"sub": user.email})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "email": user.email,
            "name": user.name,
            "role": user.role
        }
    }

@api_router.post("/auth/login")
async def login(login_data: UserLogin):
    user = await db.users.find_one({"email": login_data.email})
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token(data={"sub": user["email"]})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"]
        }
    }

@api_router.get("/auth/me")
async def get_current_user_info(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name,
        "role": current_user.role
    }

# Subject endpoints
@api_router.get("/subjects")
async def get_subjects(current_user: User = Depends(get_current_user)):
    if current_user.role == "student":
        subjects = await db.subjects.find({"student_id": current_user.id}).to_list(1000)
    else:
        # Parents see subjects from all their students
        relations = await db.parent_student_relations.find({"parent_id": current_user.id}).to_list(1000)
        student_ids = [rel["student_id"] for rel in relations]
        subjects = await db.subjects.find({"student_id": {"$in": student_ids}}).to_list(1000)
    
    return [Subject(**subject) for subject in subjects]

@api_router.post("/subjects")
async def create_subject(subject_data: SubjectCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create subjects")
    
    subject = Subject(
        name=subject_data.name,
        color=subject_data.color,
        student_id=current_user.id
    )
    
    await db.subjects.insert_one(subject.dict())
    return subject

# Task endpoints
@api_router.get("/tasks")
async def get_tasks(current_user: User = Depends(get_current_user)):
    if current_user.role == "student":
        tasks = await db.tasks.find({"student_id": current_user.id}).to_list(1000)
    else:
        # Parents see tasks from all their students
        relations = await db.parent_student_relations.find({"parent_id": current_user.id}).to_list(1000)
        student_ids = [rel["student_id"] for rel in relations]
        tasks = await db.tasks.find({"student_id": {"$in": student_ids}}).to_list(1000)
    
    return [Task(**task) for task in tasks]

@api_router.post("/tasks")
async def create_task(task_data: TaskCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create tasks")
    
    task = Task(
        title=task_data.title,
        description=task_data.description,
        subject_id=task_data.subject_id,
        student_id=current_user.id,
        due_date=task_data.due_date,
        priority=task_data.priority
    )
    
    await db.tasks.insert_one(task.dict())
    
    # Notify parents
    await notify_parents_about_task(current_user.id, f"New task created: {task.title}")
    
    return task

@api_router.put("/tasks/{task_id}")
async def update_task(task_id: str, task_data: TaskUpdate, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can update tasks")
    
    task = await db.tasks.find_one({"id": task_id, "student_id": current_user.id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {k: v for k, v in task_data.dict().items() if v is not None}
    
    if task_data.completed is not None and task_data.completed and not task["completed"]:
        update_data["completed_at"] = datetime.utcnow()
        # Notify parents about completion
        await notify_parents_about_task(current_user.id, f"Task completed: {task['title']}")
    
    await db.tasks.update_one({"id": task_id}, {"$set": update_data})
    
    updated_task = await db.tasks.find_one({"id": task_id})
    return Task(**updated_task)

@api_router.delete("/tasks/{task_id}")
async def delete_task(task_id: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can delete tasks")
    
    result = await db.tasks.delete_one({"id": task_id, "student_id": current_user.id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return {"message": "Task deleted successfully"}

# Project endpoints
@api_router.get("/projects")
async def get_projects(current_user: User = Depends(get_current_user)):
    if current_user.role == "student":
        projects = await db.projects.find({"student_id": current_user.id}).to_list(1000)
    else:
        # Parents see projects from all their students
        relations = await db.parent_student_relations.find({"parent_id": current_user.id}).to_list(1000)
        student_ids = [rel["student_id"] for rel in relations]
        projects = await db.projects.find({"student_id": {"$in": student_ids}}).to_list(1000)
    
    return [Project(**project) for project in projects]

@api_router.post("/projects")
async def create_project(project_data: ProjectCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create projects")
    
    project = Project(
        name=project_data.name,
        description=project_data.description,
        subject_id=project_data.subject_id,
        student_id=current_user.id
    )
    
    await db.projects.insert_one(project.dict())
    return project

@api_router.get("/projects/{project_id}/tasks")
async def get_project_tasks(project_id: str, current_user: User = Depends(get_current_user)):
    project = await db.projects.find_one({"id": project_id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check access
    if current_user.role == "student" and project["student_id"] != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role == "parent":
        relation = await db.parent_student_relations.find_one({
            "parent_id": current_user.id,
            "student_id": project["student_id"]
        })
        if not relation:
            raise HTTPException(status_code=403, detail="Access denied")
    
    tasks = await db.project_tasks.find({"project_id": project_id}).to_list(1000)
    return [ProjectTask(**task) for task in tasks]

@api_router.post("/projects/{project_id}/tasks")
async def create_project_task(project_id: str, task_data: ProjectTaskCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can create project tasks")
    
    project = await db.projects.find_one({"id": project_id, "student_id": current_user.id})
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    task = ProjectTask(
        title=task_data.title,
        description=task_data.description,
        project_id=project_id,
        student_id=current_user.id,
        status=task_data.status,
        due_date=task_data.due_date
    )
    
    await db.project_tasks.insert_one(task.dict())
    return task

@api_router.put("/projects/{project_id}/tasks/{task_id}")
async def update_project_task(project_id: str, task_id: str, task_data: dict, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can update project tasks")
    
    task = await db.project_tasks.find_one({"id": task_id, "project_id": project_id, "student_id": current_user.id})
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    update_data = {k: v for k, v in task_data.items() if v is not None}
    await db.project_tasks.update_one({"id": task_id}, {"$set": update_data})
    
    # Notify parents if task is completed
    if task_data.get("status") == "done" and task["status"] != "done":
        await notify_parents_about_task(current_user.id, f"Project task completed: {task['title']}")
    
    updated_task = await db.project_tasks.find_one({"id": task_id})
    return ProjectTask(**updated_task)

# Parent invitation endpoints
@api_router.post("/invite-parent")
async def invite_parent(invite_data: ParentInviteCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "student":
        raise HTTPException(status_code=403, detail="Only students can invite parents")
    
    # Check if parent already exists and is connected
    parent = await db.users.find_one({"email": invite_data.parent_email, "role": "parent"})
    if parent:
        existing_relation = await db.parent_student_relations.find_one({
            "parent_id": parent["id"],
            "student_id": current_user.id
        })
        if existing_relation:
            raise HTTPException(status_code=400, detail="Parent is already connected")
    
    # Create invite
    invite_code = str(uuid.uuid4())[:8]
    invite = ParentInvite(
        student_id=current_user.id,
        parent_email=invite_data.parent_email,
        invite_code=invite_code
    )
    
    await db.parent_invites.insert_one(invite.dict())
    
    # Send email invitation
    await send_email_notification(
        invite_data.parent_email,
        f"School Work Tracker - Invitation from {current_user.name}",
        f"You've been invited by {current_user.name} to track their school work. Use invite code: {invite_code}"
    )
    
    return {"message": "Invitation sent successfully", "invite_code": invite_code}

@api_router.post("/accept-invite")
async def accept_invite(invite_code: str, current_user: User = Depends(get_current_user)):
    if current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can accept invites")
    
    invite = await db.parent_invites.find_one({"invite_code": invite_code, "accepted": False})
    if not invite:
        raise HTTPException(status_code=404, detail="Invalid or expired invite code")
    
    # Create parent-student relation
    relation = ParentStudentRelation(
        parent_id=current_user.id,
        student_id=invite["student_id"]
    )
    
    await db.parent_student_relations.insert_one(relation.dict())
    await db.parent_invites.update_one({"id": invite["id"]}, {"$set": {"accepted": True}})
    
    return {"message": "Invite accepted successfully"}

# Parent dashboard endpoints
@api_router.get("/parent/students")
async def get_parent_students(current_user: User = Depends(get_current_user)):
    if current_user.role != "parent":
        raise HTTPException(status_code=403, detail="Only parents can access this endpoint")
    
    relations = await db.parent_student_relations.find({"parent_id": current_user.id}).to_list(1000)
    student_ids = [rel["student_id"] for rel in relations]
    
    students = await db.users.find({"id": {"$in": student_ids}, "role": "student"}).to_list(1000)
    
    # Get summary data for each student
    result = []
    for student in students:
        tasks = await db.tasks.find({"student_id": student["id"]}).to_list(1000)
        projects = await db.projects.find({"student_id": student["id"]}).to_list(1000)
        
        completed_tasks = len([t for t in tasks if t["completed"]])
        total_tasks = len(tasks)
        
        result.append({
            "student": {
                "id": student["id"],
                "name": student["name"],
                "email": student["email"]
            },
            "stats": {
                "total_tasks": total_tasks,
                "completed_tasks": completed_tasks,
                "pending_tasks": total_tasks - completed_tasks,
                "total_projects": len(projects)
            }
        })
    
    return result

# Notification endpoints
@api_router.get("/notifications")
async def get_notifications(current_user: User = Depends(get_current_user)):
    notifications = await db.notifications.find({"user_id": current_user.id}).sort("created_at", -1).to_list(100)
    return [Notification(**notification) for notification in notifications]

@api_router.put("/notifications/{notification_id}/read")
async def mark_notification_read(notification_id: str, current_user: User = Depends(get_current_user)):
    await db.notifications.update_one(
        {"id": notification_id, "user_id": current_user.id},
        {"$set": {"read": True}}
    )
    return {"message": "Notification marked as read"}

# Helper function to notify parents
async def notify_parents_about_task(student_id: str, message: str):
    relations = await db.parent_student_relations.find({"student_id": student_id}).to_list(1000)
    student = await db.users.find_one({"id": student_id})
    
    for relation in relations:
        parent = await db.users.find_one({"id": relation["parent_id"]})
        if parent:
            # Create in-app notification
            notification = Notification(
                user_id=parent["id"],
                title="Student Update",
                message=f"{student['name']}: {message}",
                type="task_update"
            )
            await db.notifications.insert_one(notification.dict())
            
            # Send email notification
            await send_email_notification(
                parent["email"],
                f"School Work Update - {student['name']}",
                message
            )

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()