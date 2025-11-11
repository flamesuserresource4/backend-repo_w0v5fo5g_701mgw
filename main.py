import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from random import randint, choice, sample
from datetime import datetime, timedelta, timezone

from database import db, create_document, get_documents
from schemas import User, Character, Post, Story, Reel, Comment, Conversation, Message, Notification

app = FastAPI(title="AIgram Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class BootstrapResponse(BaseModel):
    characters: int
    posts: int
    stories: int


def _now():
    return datetime.now(timezone.utc)


def ensure_bootstrap(character_count: int = 24, posts_per_character: int = 2):
    if db is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    existing = db["character"].count_documents({})
    created_chars = 0
    created_posts = 0
    created_stories = 0

    if existing >= 5:
        return BootstrapResponse(characters=existing, posts=db["post"].count_documents({}), stories=db["story"].count_documents({}))

    first_names = [
        "Ava","Liam","Noah","Mia","Zoe","Kai","Leo","Ivy","Nora","Mila","Aria","Ezra","Finn","Luna","Nova","Zara","Enzo","Atlas","Jade","Ada"
    ]
    last_names = ["Wilde","Rivera","Okafor","Nguyen","Kim","Singh","Khan","Garcia","Silva","Ivanov","Sato","Hernandez","Smith","Brown"]
    interests_pool = [
        "travel","food","art","fitness","tech","gaming","fashion","music","photo","nature","design","books","coffee","pets","memes"
    ]

    # Create characters
    for i in range(character_count):
        name = f"{choice(first_names)} {choice(last_names)}"
        username = (name.split()[0] + str(randint(100, 999))).lower()
        char = Character(
            username=username,
            name=name,
            bio=" ".join(["Exploring", choice(["virtual", "creative", "digital", "urban", "cozy"]) ,"worlds 🌐"]),
            avatar_url=f"https://i.pravatar.cc/150?img={randint(1,70)}",
            interests=sample(interests_pool, k=randint(2,4)),
            followers=randint(100,9000),
            following=randint(50,900),
        )
        create_document("character", char)
        created_chars += 1

    # Create posts and stories
    characters = list(db["character"].find({}).limit(character_count))
    for c in characters:
        for _ in range(posts_per_character):
            media_url = f"https://picsum.photos/seed/{c['username']}-{randint(1,9999)}/800/1000"
            post = Post(
                author_type="character",
                author_id=str(c.get("_id")),
                type="image",
                media_url=media_url,
                caption=f"{choice(['Sunset vibes', 'Daily snap', 'Weekend mood', 'New drop', 'Behind the scenes'])} #{choice(interests_pool)}",
                hashtags=[choice(interests_pool), choice(interests_pool)],
                like_count=randint(10, 5000),
                comment_count=randint(0, 200)
            )
            create_document("post", post)
            created_posts += 1
        # occasional story
        if randint(0, 1) == 1:
            story = Story(
                author_type="character",
                author_id=str(c.get("_id")),
                media_url=f"https://picsum.photos/seed/story-{c['username']}/720/1280",
                text_overlay=choice(["Out and about", "Work in progress", "New playlist", "Coffee time", None]),
                expires_at=(_now() + timedelta(hours=24)).isoformat()
            )
            create_document("story", story)
            created_stories += 1

    return BootstrapResponse(
        characters=created_chars,
        posts=created_posts,
        stories=created_stories,
    )


@app.get("/")
def read_root():
    return {"message": "AIgram Backend Running"}


@app.get("/api/bootstrap", response_model=BootstrapResponse)
def api_bootstrap():
    return ensure_bootstrap()


@app.get("/api/feed")
def get_feed(limit: int = 25):
    try:
        posts = list(db["post"].find({}).sort("created_at", -1).limit(limit))
        # hydrate with author basic info
        author_ids = [p.get("author_id") for p in posts]
        characters = {str(c.get("_id")): c for c in db["character"].find({"_id": {"$in": [db["character"].database.client.get_default_database().codec_options.document_class()._id if False else None]}})}
        # fallback simple map
        char_map = {str(c.get("_id")): c for c in db["character"].find({})}
        for p in posts:
            aid = p.get("author_id")
            c = char_map.get(aid)
            if c:
                p["author"] = {
                    "username": c.get("username"),
                    "name": c.get("name"),
                    "avatar_url": c.get("avatar_url"),
                }
        return jsonable_encoder(posts)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stories")
def get_stories(limit: int = 20):
    stories = list(db["story"].find({}).sort("created_at", -1).limit(limit))
    char_map = {str(c.get("_id")): c for c in db["character"].find({})}
    for s in stories:
        c = char_map.get(s.get("author_id"))
        if c:
            s["author"] = {
                "username": c.get("username"),
                "name": c.get("name"),
                "avatar_url": c.get("avatar_url"),
            }
    return jsonable_encoder(stories)


@app.get("/api/characters")
def get_characters(limit: int = 50):
    chars = list(db["character"].find({}).limit(limit))
    return jsonable_encoder(chars)


@app.post("/api/like/{post_id}")
def like_post(post_id: str):
    from bson import ObjectId
    try:
        res = db["post"].update_one({"_id": ObjectId(post_id)}, {"$inc": {"like_count": 1}, "$set": {"updated_at": _now()}})
        if res.modified_count == 0:
            raise HTTPException(status_code=404, detail="Post not found")
        post = db["post"].find_one({"_id": ObjectId(post_id)})
        return jsonable_encoder(post)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
