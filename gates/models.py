import secrets
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def _generate_public_id():
    # 32-ish chars, URL safe
    return secrets.token_urlsafe(24)


class GatedTrack(models.Model):
    """
    A SoundCloud track that gates access to a downloadable file.

    - Owners are Django Users (your existing accounts system).
    - Downloaders authenticate with SoundCloud OAuth (stored in session, not tied to Django User).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="gated_tracks")

    public_id = models.CharField(
        max_length=64, unique=True, db_index=True, default=_generate_public_id, editable=False
    )

    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)

    soundcloud_track_url = models.URLField(help_text="Public SoundCloud URL to the track")
    # Preferred identifier (SoundCloud URN string, e.g. soundcloud:tracks:12345678)
    soundcloud_track_urn = models.CharField(max_length=128, blank=True, db_index=True)
    # Track owner (artist) identity (for follow requirement)
    soundcloud_artist_urn = models.CharField(max_length=128, blank=True, db_index=True)
    soundcloud_artist_username = models.CharField(max_length=255, blank=True)

    require_like = models.BooleanField(default=True)
    require_comment = models.BooleanField(default=True)
    require_follow = models.BooleanField(default=False)

    # File is uploaded in a dedicated step after gate creation.
    download_file = models.FileField(upload_to="gated_downloads/%Y/%m/%d/", blank=True)
    download_filename = models.CharField(
        max_length=255,
        blank=True,
        help_text="Optional filename to use for the downloaded file.",
    )

    is_active = models.BooleanField(default=True)
    is_listed = models.BooleanField(
        default=False,
        help_text="If enabled, this gate appears on public browse pages.",
    )

    download_count = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title or 'Untitled gate'} ({self.public_id})"

    def resolved_download_filename(self):
        if self.download_filename:
            return self.download_filename
        if self.download_file and getattr(self.download_file, "name", None):
            return self.download_file.name.split("/")[-1]
        return "download"


class GatedFollowTarget(models.Model):
    """
    Additional SoundCloud profiles that must be followed to unlock the download
    (e.g. collaborations).
    """

    track = models.ForeignKey(GatedTrack, on_delete=models.CASCADE, related_name="follow_targets")
    profile_url = models.URLField(blank=True)
    soundcloud_user_urn = models.CharField(max_length=128, blank=True, db_index=True)
    soundcloud_username = models.CharField(max_length=255, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("track", "soundcloud_user_urn"), ("track", "profile_url")]
        ordering = ["created_at"]

    def __str__(self):
        ident = self.soundcloud_username or self.soundcloud_user_urn or self.profile_url or "target"
        return f"{self.track.public_id} -> {ident}"


class GateAccess(models.Model):
    """
    Stores that a given SoundCloud user has satisfied the gate for a track.
    """

    track = models.ForeignKey(GatedTrack, on_delete=models.CASCADE, related_name="gate_accesses")

    soundcloud_user_urn = models.CharField(max_length=128, db_index=True)
    soundcloud_username = models.CharField(max_length=255, blank=True)

    verified_like = models.BooleanField(default=False)
    verified_comment = models.BooleanField(default=False)
    verified_follow = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    download_count = models.PositiveIntegerField(default=0)
    last_download_at = models.DateTimeField(null=True, blank=True)

    last_ip_address = models.GenericIPAddressField(null=True, blank=True)
    last_user_agent = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("track", "soundcloud_user_urn")]
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.soundcloud_user_urn} -> {self.track.public_id}"

    def mark_verified(self, liked: bool, commented: bool, followed: bool):
        self.verified_like = liked
        self.verified_comment = commented
        self.verified_follow = followed
        self.verified_at = timezone.now()
        self.save(
            update_fields=[
                "verified_like",
                "verified_comment",
                "verified_follow",
                "verified_at",
                "updated_at",
            ]
        )

