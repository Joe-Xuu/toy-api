import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel, Field, Session, create_engine, select

# --- 1. 数据库配置 ---

# 优先读取环境变量里的数据库地址(上线用)，如果没有则使用本地的 sqlite 文件(本地用)
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./local_database.db")

# 如果是 Postgres，URL 需要把 postgres:// 改成 postgresql:// (SQLAlchemy 的小癖好)
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# 创建数据库引擎
# connect_args={"check_same_thread": False} 是为了兼容 SQLite，用 Postgres 时会自动忽略
engine = create_engine(DATABASE_URL, echo=False)

# --- 2. 定义数据模型 (Table) ---

# 注意：这里继承的是 SQLModel，且加上 table=True，代表这是一张数据库表
class TodoItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True) # 增加 ID 作为主键
    title: str
    is_done: bool = False

# --- 3. 初始化工作 ---

app = FastAPI()


# 1. 解决跨域问题 (CORS) 跨域资源共享 cross origin resource sharing
# 用额外的 HTTP 头来告诉浏览器允许一个网页从另一个域（不同于该网页所在的域）请求资源。
# 这样可以在服务器和客户端之间进行安全的跨域通信。
# origin = 协议 + 域名 + 端口号
# 同源策略限制不同源之间的交互行为。
# 默认会阻止跨域请求，所以需要 CORS 机制来显式允许跨域访问。

# 普通的网页(html)无法访问 API。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 启动时自动创建表结构 (如果表不存在的话)
@app.on_event("startup")
def on_startup():
    SQLModel.metadata.create_all(engine)

# 依赖注入函数：负责打开和关闭数据库会话
def get_session():
    with Session(engine) as session:
        yield session

# --- 4. API 接口 (CRUD) ---

# 获取所有
@app.get("/todos", response_model=List[TodoItem])
def get_all_todos(session: Session = Depends(get_session)):
    # 相当于 SQL: SELECT * FROM todoitem;
    statement = select(TodoItem)
    results = session.exec(statement).all()
    return results

# 添加数据
@app.post("/todos", response_model=TodoItem)
def add_todo(item: TodoItem, session: Session = Depends(get_session)):
    session.add(item)
    session.commit()
    session.refresh(item) # 刷新数据，获取自动生成的 ID
    return item

# 删除数据 (比如根据 ID 删除) - 稍微升级了一下功能
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int, session: Session = Depends(get_session)):
    item = session.get(TodoItem, todo_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    session.delete(item)
    session.commit()
    return {"message": "Deleted successfully"}