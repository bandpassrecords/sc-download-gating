from django.contrib import admin

from .models import GateAccess, GatedTrack


@admin.register(GatedTrack)
class GatedTrackAdmin(admin.ModelAdmin):
    list_display = (
        "public_id",
        "owner",
        "title",
        "is_active",
        "is_listed",
        "require_like",
        "require_comment",
        "download_count",
        "created_at",
    )
    list_filter = ("is_active", "is_listed", "require_like", "require_comment", "created_at")
    search_fields = ("public_id", "title", "soundcloud_track_url", "soundcloud_track_urn", "owner__email")
    readonly_fields = ("public_id", "created_at", "updated_at", "download_count")


@admin.register(GateAccess)
class GateAccessAdmin(admin.ModelAdmin):
    list_display = (
        "track",
        "soundcloud_user_urn",
        "soundcloud_username",
        "verified_like",
        "verified_comment",
        "verified_at",
        "download_count",
        "last_download_at",
    )
    list_filter = ("verified_like", "verified_comment", "verified_at")
    search_fields = ("soundcloud_user_urn", "soundcloud_username", "track__public_id", "track__title")
    readonly_fields = ("created_at", "updated_at")

