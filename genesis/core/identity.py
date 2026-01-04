"""Identity system for Genesis Minds."""

import hashlib
import secrets
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


def generate_gmid(year: Optional[int] = None) -> str:
    """
    Generate a Genesis Mind ID (GMID).

    Format: GMD-YYYY-XXXX-XXXX
    Example: GMD-2025-4A7F-9B23
    """
    if year is None:
        year = datetime.now().year

    # Generate random segments
    segment1 = secrets.token_hex(2).upper()
    segment2 = secrets.token_hex(2).upper()

    return f"GMD-{year}-{segment1}-{segment2}"


def generate_fingerprint(gmid: str, birth_timestamp: datetime, creator: str) -> str:
    """
    Generate digital fingerprint (cryptographic hash).

    Format: 7F4A:2B9C:E3D1:8A6F:C2E4:9B7A:3F1D:5C8E
    """
    # Create hash from unique attributes
    data = f"{gmid}:{birth_timestamp.isoformat()}:{creator}:{secrets.token_hex(16)}"
    hash_bytes = hashlib.sha256(data.encode()).digest()

    # Format as colon-separated hex
    hex_str = hash_bytes.hex().upper()
    # Take first 32 chars (16 bytes), format as 8 groups of 4
    groups = [hex_str[i : i + 4] for i in range(0, 32, 4)]
    return ":".join(groups)


class MindIdentity(BaseModel):
    """Identity information for a Genesis Mind."""

    # Core identity
    gmid: str = Field(default_factory=generate_gmid)
    name: str
    digital_fingerprint: str = ""

    # Birth information
    birth_timestamp: datetime = Field(default_factory=datetime.now)
    birth_location: str = "local"  # server/location
    creator: str = "anonymous"
    creator_email: Optional[str] = None  # Email of the creator
    template: str = "base/curious_explorer"

    # Purpose
    primary_purpose: str = "General companion and assistant"
    specialization: Optional[str] = None
    description: Optional[str] = None

    # Lifecycle
    lifespan_years: int = 5
    status: str = "alive"  # alive, sleeping, terminated

    # Currency (Gens)
    gens: int = 1000

    # Avatar
    avatar_url: Optional[str] = None  # Last generated avatar URL

    # Genesis version
    genesis_version: str = "0.1.1"

    def __init__(self, **data):
        super().__init__(**data)
        # Generate fingerprint if not provided
        if not self.digital_fingerprint:
            self.digital_fingerprint = generate_fingerprint(
                self.gmid, self.birth_timestamp, self.creator
            )

    @property
    def age(self) -> str:
        """Get human-readable age."""
        return self.get_age_description()
    
    @property
    def birth_date(self) -> str:
        """Get formatted birth date."""
        return self.birth_timestamp.strftime("%Y-%m-%d %H:%M:%S")
    
    @property
    def age_days(self) -> int:
        """Get age in days."""
        return self.get_age_days()

    def get_age_days(self) -> int:
        """Get age in days."""
        return (datetime.now() - self.birth_timestamp).days

    def get_age_description(self) -> str:
        """Get human-readable age."""
        days = self.get_age_days()
        if days < 1:
            return "newborn"
        elif days < 7:
            return f"{days} days old"
        elif days < 30:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} old"
        elif days < 365:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} old"
        else:
            years = days // 365
            return f"{years} year{'s' if years > 1 else ''} old"

    def get_remaining_lifespan(self) -> int:
        """Get remaining lifespan in days."""
        total_days = self.lifespan_years * 365
        lived_days = self.get_age_days()
        return max(0, total_days - lived_days)

    def to_birth_certificate(self) -> dict:
        """Generate birth certificate data."""
        return {
            "genesis_mind_id": self.gmid,
            "name": self.name,
            "digital_fingerprint": self.digital_fingerprint,
            "birth_timestamp": self.birth_timestamp.isoformat(),
            "birth_location": self.birth_location,
            "creator": self.creator,
            "creator_email": self.creator_email,
            "template": self.template,
            "primary_purpose": self.primary_purpose,
            "specialization": self.specialization,
            "genesis_version": self.genesis_version,
            "lifespan_years": self.lifespan_years,
        }

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
