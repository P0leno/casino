from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
import json
import sqlite3
from app.routers.auth import verify_init_data
from app.utils.database import get_db_connection, DB_PATH
from app.utils.redis_models import RedisSettings

router = APIRouter(prefix="/api", tags=["banners"])

class BannersRequest(BaseModel):
    initData: str

class CreateBannerRequest(BaseModel):
    initData: str
    title: str
    subtitle: Optional[str] = None
    bg_from: str = "#0a2a4a"
    bg_to: Optional[str] = None
    image_url: Optional[str] = None
    action: Optional[str] = None
    active: bool = True

class UpdateBannerRequest(BaseModel):
    initData: str
    title: Optional[str] = None
    subtitle: Optional[str] = None
    bg_from: Optional[str] = None
    bg_to: Optional[str] = None
    image_url: Optional[str] = None
    action: Optional[str] = None
    active: Optional[bool] = None

class DeleteBannerRequest(BaseModel):
    initData: str
    banner_id: int

@router.post("/banners")
async def get_banners(req: BannersRequest):
    user_id = verify_init_data(req.initData)
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, subtitle, bg_from, bg_to, image_url, action, active FROM banners ORDER BY sort_order ASC")
        rows = cursor.fetchall()
        banners = [
            {
                "id": row[0],
                "title": row[1],
                "subtitle": row[2],
                "bg_from": row[3],
                "bg_to": row[4],
                "image_url": row[5],
                "action": row[6],
                "active": bool(row[7]),
            }
            for row in rows
        ]
        return banners
    finally:
        conn.close()

@router.post("/banners/create")
async def create_banner(req: CreateBannerRequest):
    user_id = verify_init_data(req.initData)
    if not user_id or not RedisSettings.is_admin(int(user_id)):
        raise HTTPException(status_code=403, detail="Admin only")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO banners (title, subtitle, bg_from, bg_to, image_url, action, active, sort_order) VALUES (?, ?, ?, ?, ?, ?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM banners))",
            (req.title, req.subtitle, req.bg_from, req.bg_to, req.image_url, req.action, int(req.active))
        )
        conn.commit()
        return {"ok": True, "banner_id": cursor.lastrowid}
    finally:
        conn.close()

@router.post("/banners/update/{banner_id}")
async def update_banner(banner_id: int, req: UpdateBannerRequest):
    user_id = verify_init_data(req.initData)
    if not user_id or not RedisSettings.is_admin(int(user_id)):
        raise HTTPException(status_code=403, detail="Admin only")

    updates = {}
    if req.title is not None: updates["title"] = req.title
    if req.subtitle is not None: updates["subtitle"] = req.subtitle
    if req.bg_from is not None: updates["bg_from"] = req.bg_from
    if req.bg_to is not None: updates["bg_to"] = req.bg_to
    if req.image_url is not None: updates["image_url"] = req.image_url
    if req.action is not None: updates["action"] = req.action
    if req.active is not None: updates["active"] = int(req.active)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [banner_id]

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE banners SET {set_clause} WHERE id = ?", values)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Banner not found")
        return {"ok": True}
    finally:
        conn.close()

@router.post("/banners/delete/{banner_id}")
async def delete_banner(banner_id: int, req: DeleteBannerRequest):
    user_id = verify_init_data(req.initData)
    if not user_id or not RedisSettings.is_admin(int(user_id)):
        raise HTTPException(status_code=403, detail="Admin only")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM banners WHERE id = ?", (banner_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Banner not found")
        return {"ok": True}
    finally:
        conn.close()

@router.post("/banners/reorder")
async def reorder_banners(req: dict):
    init_data = req.get("initData")
    order = req.get("order", [])
    user_id = verify_init_data(init_data)
    if not user_id or not RedisSettings.is_admin(int(user_id)):
        raise HTTPException(status_code=403, detail="Admin only")

    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        for idx, banner_id in enumerate(order):
            cursor.execute("UPDATE banners SET sort_order = ? WHERE id = ?", (idx, banner_id))
        conn.commit()
        return {"ok": True}
    finally:
        conn.close()
