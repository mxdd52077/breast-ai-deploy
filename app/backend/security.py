import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from threading import Lock

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import HTTPException, Request, Response
from sqlalchemy import select

from .db import LoginSession, Session, User

hasher = PasswordHasher()
limits = defaultdict(deque)
lock = Lock()

def rate_limit(key, count=15, seconds=60):
    now=time.time()
    with lock:
        queue=limits[key]
        while queue and queue[0]<now-seconds:
            queue.popleft()
        if len(queue)>=count:
            raise HTTPException(429,"操作太频繁，请稍后再试。")
        queue.append(now)

def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()

def verify_password(encoded, password):
    try:
        return hasher.verify(encoded,password)
    except VerificationError:
        return False

def issue_session(db, user, response: Response):
    token=secrets.token_urlsafe(40)
    csrf=secrets.token_hex(24)
    db.add(LoginSession(token_hash=digest(token),user_id=user.id,csrf=csrf,expires=time.time()+60*60*24*7))
    secure=os.getenv("APEX_SECURE_COOKIES")=="true" or bool(os.getenv("VERCEL"))
    response.set_cookie("apex_session",token,httponly=True,samesite="strict",secure=secure,max_age=604800,path="/")
    return {"user":{"id":user.id,"name":user.name,"demo":user.demo,"institution_access":user.institution_access},"csrf":csrf}

def current_user(request: Request):
    token=request.cookies.get("apex_session","")
    with Session() as db:
        session=db.get(LoginSession,digest(token))
        if not session or session.expires<time.time():
            raise HTTPException(401,"请先登录。")
        if request.method not in {"GET","HEAD","OPTIONS"}:
            if not secrets.compare_digest(request.headers.get("x-csrf-token",""),session.csrf):
                raise HTTPException(403,"会话已更新，请刷新后重试。")
        user=db.get(User,session.user_id)
        if not user:
            raise HTTPException(401,"请先登录。")
        request.state.csrf=session.csrf
        return user

def institution_user(request: Request):
    user=current_user(request)
    if not user.institution_access:
        raise HTTPException(403,"此账户没有机构工作区权限。")
    return user
