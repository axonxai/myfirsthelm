# app.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import sqlite3
import os
from typing import List, Optional

app = FastAPI(title="Tasks API")

# Get configuration from environment variables (will be set via ConfigMap)
API_PREFIX = os.getenv('API_PREFIX', '/api/v1')
DB_PATH = os.getenv('DB_PATH', '/data/tasks.db')

# Get database password from secrets
DB_PASSWORD = os.getenv('DB_PASSWORD', 'default_password')

# Pydantic models for request/response validation
class TaskBase(BaseModel):
    title: str
    completed: bool = False

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: int

    class Config:
        from_attributes = True

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
         title TEXT NOT NULL,
         completed BOOLEAN NOT NULL DEFAULT 0)
    ''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
    finally:
        conn.close()

# Initialize the database
init_db()

@app.get(f"{API_PREFIX}/tasks", response_model=List[Task])
def read_tasks():
    with next(get_db()) as conn:
        c = conn.cursor()
        c.execute('SELECT id, title, completed FROM tasks')
        tasks = [
            {"id": row[0], "title": row[1], "completed": bool(row[2])}
            for row in c.fetchall()
        ]
        return tasks

@app.post(f"{API_PREFIX}/tasks", response_model=Task, status_code=201)
def create_task(task: TaskCreate):
    with next(get_db()) as conn:
        c = conn.cursor()
        c.execute(
            'INSERT INTO tasks (title, completed) VALUES (?, ?)',
            (task.title, task.completed)
        )
        conn.commit()
        task_id = c.lastrowid
        return {"id": task_id, "title": task.title, "completed": task.completed}

@app.get(f"{API_PREFIX}/tasks/{{task_id}}", response_model=Task)
def read_task(task_id: int):
    with next(get_db()) as conn:
        c = conn.cursor()
        c.execute('SELECT id, title, completed FROM tasks WHERE id = ?', (task_id,))
        task = c.fetchone()
        if task is None:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"id": task[0], "title": task[1], "completed": bool(task[2])}

@app.put(f"{API_PREFIX}/tasks/{{task_id}}", response_model=Task)
def update_task(task_id: int, task: TaskCreate):
    with next(get_db()) as conn:
        c = conn.cursor()
        c.execute(
            'UPDATE tasks SET title = ?, completed = ? WHERE id = ?',
            (task.title, task.completed, task_id)
        )
        conn.commit()
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"id": task_id, "title": task.title, "completed": task.completed}

@app.delete(f"{API_PREFIX}/tasks/{{task_id}}")
def delete_task(task_id: int):
    with next(get_db()) as conn:
        c = conn.cursor()
        c.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()
        if c.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        return {"message": "Task deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
