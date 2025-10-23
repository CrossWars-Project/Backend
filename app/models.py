# Models for the CrossWars backend API
# This file contains all Pydantic models for data validation and serialization

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import date
import re


# Stats-related models
class UserStatsResponse(BaseModel):
    """Response model for user stats - what gets returned to the client"""

    user_id: str  # UUID from Supabase auth
    num_solo_games: int
    num_competition_games: int
    fastest_solo_time: int  # -1 if no games played
    fastest_competition_time: int  # -1 if no games played
    num_wins: int
    dt_last_seen: Optional[date]
    streak_count: int

    class Config:
        # Allow Pydantic to work with datetime objects
        json_encoders = {date: lambda v: v.isoformat() if v else None}


class StatsUpdate(BaseModel):
    """Model for updating stats after a game"""

    game_type: str = Field(..., description="Type of game played")
    completion_time: int = Field(
        ..., gt=0, description="Game completion time in seconds"
    )
    won_game: bool = Field(
        default=False, description="True if user won a competition game"
    )

    @validator("game_type")
    def validate_game_type(cls, v):
        """Ensure game_type is either 'solo' or 'competition'"""
        if v not in ["solo", "competition"]:
            raise ValueError('game_type must be either "solo" or "competition"')
        return v

    @validator("completion_time")
    def validate_completion_time(cls, v):
        """Ensure completion time is reasonable (between 1 second and 24 hours)"""
        if v < 1:
            raise ValueError("completion_time must be at least 1 second")
        if v > 86400:  # 24 hours in seconds
            raise ValueError("completion_time cannot exceed 24 hours (86400 seconds)")
        return v


class StatsCreate(BaseModel):
    """Model for creating initial user stats (internal use)"""

    user_id: str
    num_solo_games: int = 0
    num_competition_games: int = 0
    fastest_solo_time: int = -1
    fastest_competition_time: int = -1
    num_wins: int = 0
    dt_last_seen: Optional[date] = None
    streak_count: int = 0


# Invite-related models (for future use)
class InviteCreate(BaseModel):
    """Model for creating game invites"""

    invitee_email: Optional[str] = Field(
        None, description="Email of person being invited"
    )
    expires_at: Optional[str] = Field(None, description="When the invite expires")

    @validator("invitee_email")
    def validate_email(cls, v):
        """Basic email validation"""
        if v and not re.match(r"^[^@]+@[^@]+\.[^@]+$", v):
            raise ValueError("Invalid email format")
        return v


class InviteResponse(BaseModel):
    """Response model for invite data"""

    invite_id: str
    match_id: str
    inviter_id: str
    invitee_email: Optional[str]
    token: str
    expires_at: str
    status: str


# Crossword-related models (for future use)
class CrosswordHint(BaseModel):
    """Model for crossword hints"""

    hint: str = Field(..., max_length=500, description="The crossword clue")
    assoc_word: str = Field(..., max_length=100, description="The answer word")

    @validator("hint")
    def validate_hint(cls, v):
        """Ensure hint is not empty and doesn't contain dangerous content"""
        if not v.strip():
            raise ValueError("Hint cannot be empty")
        # Basic sanitization - remove potential HTML/script tags
        cleaned = re.sub(r"<[^>]*>", "", v.strip())
        return cleaned

    @validator("assoc_word")
    def validate_word(cls, v):
        """Ensure word contains only letters and common punctuation"""
        if not v.strip():
            raise ValueError("Associated word cannot be empty")
        # Allow only letters, spaces, hyphens, and apostrophes
        if not re.match(r"^[a-zA-Z\s\'-]+$", v.strip()):
            raise ValueError(
                "Word can only contain letters, spaces, hyphens, and apostrophes"
            )
        return v.strip().upper()


# Error response models
class ErrorResponse(BaseModel):
    """Standard error response format"""

    detail: str
    status_code: int


# Success response models
class SuccessResponse(BaseModel):
    """Standard success response format"""

    message: str
    data: Optional[dict] = None
