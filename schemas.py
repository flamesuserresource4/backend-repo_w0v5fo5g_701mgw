"""
AIgram Database Schemas

Each Pydantic model corresponds to a MongoDB collection. The collection name is the lowercase of the class name.

Collections used:
- User: The single human user of the app
- Character: AI-generated personas
- Post: Feed posts (images/videos) created by Characters or User
- Story: 24h ephemeral stories
- Reel: Short vertical videos
- Comment: Comments on posts
- Conversation: DM conversations
- Message: Messages inside a conversation
- Notification: Basic engagement notifications
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class User(BaseModel):
    username: str = Field(..., description="Unique username for the human user")
    name: Optional[str] = Field(None, description="Display name")
    bio: Optional[str] = Field(None, description="Profile bio")
    avatar_url: Optional[str] = Field(None, description="Profile picture URL")

class Character(BaseModel):
    username: str = Field(..., description="Unique handle for the AI character")
    name: str = Field(..., description="Display name")
    bio: Optional[str] = Field(None, description="Short bio")
    avatar_url: Optional[str] = Field(None, description="Avatar URL")
    interests: List[str] = Field(default_factory=list, description="Interest tags for personalization")
    followers: int = Field(0, ge=0)
    following: int = Field(0, ge=0)

PostType = Literal["image", "video"]

class Post(BaseModel):
    author_type: Literal["character", "user"] = Field("character")
    author_id: str = Field(..., description="ID of the author document")
    type: PostType = Field("image")
    media_url: str = Field(..., description="URL of the image or video")
    caption: Optional[str] = Field(None)
    hashtags: List[str] = Field(default_factory=list)
    like_count: int = Field(0, ge=0)
    comment_count: int = Field(0, ge=0)

class Story(BaseModel):
    author_type: Literal["character", "user"] = Field("character")
    author_id: str
    media_url: str
    text_overlay: Optional[str] = None
    expires_at: Optional[str] = Field(None, description="ISO timestamp when the story expires")

class Reel(BaseModel):
    author_type: Literal["character", "user"] = Field("character")
    author_id: str
    media_url: str
    caption: Optional[str] = None
    like_count: int = 0
    comment_count: int = 0

class Comment(BaseModel):
    post_id: str
    author_type: Literal["character", "user"] = Field("character")
    author_id: str
    text: str

class Conversation(BaseModel):
    participant_ids: List[str] = Field(..., description="IDs (user and characters) in the convo; includes the user id")

class Message(BaseModel):
    conversation_id: str
    author_type: Literal["character", "user"] = Field("character")
    author_id: str
    text: Optional[str] = None
    media_url: Optional[str] = None

class Notification(BaseModel):
    user_id: str
    type: Literal["like", "comment", "follow"]
    actor_id: str
    actor_type: Literal["character", "user"] = Field("character")
    post_id: Optional[str] = None
    message: Optional[str] = None
