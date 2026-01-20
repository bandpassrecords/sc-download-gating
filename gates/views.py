import secrets
from typing import Optional

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import SuspiciousOperation
from django.db.models import F
from django.http import FileResponse, Http404
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import GatedTrackCreateForm, GatedTrackUpdateForm
from .models import GateAccess, GatedTrack
from .soundcloud import (
    build_authorize_url,
    exchange_code_for_token,
    follow_user,
    generate_pkce_pair,
    get_followings_urns,
    get_me,
    is_configured,
    like_track,
    post_comment,
    resolve_track_from_url,
    resolve_track_urn_from_url,
    resolve_user_from_url,
    user_commented_on_track,
    user_follows_user,
    user_liked_track,
)


def _safe_upload_basename(name: str) -> str:
    # Preserve spaces/parentheses; strip any path components.
    return (name or "").strip().replace("\\", "/").split("/")[-1]


def _get_client_ip(request) -> Optional[str]:
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _get_session_access_token(request) -> str:
    """
    We keep the SoundCloud access token in-session so we can perform like/comment
    actions directly from the gate page. We clear it after download (and if expired).
    """
    token = (request.session.get("soundcloud_access_token") or "").strip()
    expires_at = int(request.session.get("soundcloud_expires_at") or 0)
    if token and expires_at:
        now_ts = int(timezone.now().timestamp())
        if now_ts >= expires_at:
            # Expired; require re-connect
            for k in ("soundcloud_access_token", "soundcloud_expires_at"):
                if k in request.session:
                    del request.session[k]
            request.session.modified = True
            return ""
    return token


def _get_soundcloud_redirect_uri(request) -> str:
    """
    SoundCloud requires the token exchange redirect_uri to exactly match the authorize redirect_uri.
    In production you likely want a fixed URL like: https://download.bandpassrecords.com/authorize
    """
    from django.conf import settings as dj_settings

    override = (getattr(dj_settings, "SOUNDCLOUD_REDIRECT_URI", "") or "").strip()
    if override:
        return override
    return request.build_absolute_uri(reverse("gates:soundcloud_callback"))


def browse(request):
    tracks = GatedTrack.objects.filter(is_active=True, is_listed=True).select_related("owner")[:48]
    return render(request, "gates/browse.html", {"tracks": tracks})


@login_required
def my_tracks(request):
    tracks = GatedTrack.objects.filter(owner=request.user).order_by("-created_at")
    return render(request, "gates/my_tracks.html", {"tracks": tracks})


@login_required
def edit_track(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, owner=request.user)
    if request.method == "POST":
        form = GatedTrackUpdateForm(request.POST, request.FILES, instance=track)
        if form.is_valid():
            form.save()
            messages.success(request, "Gate updated.")
            return redirect("gates:edit_track", public_id=track.public_id)
        messages.error(request, "Please fix the errors below.")
    else:
        form = GatedTrackUpdateForm(instance=track)
    return render(request, "gates/edit_track.html", {"track": track, "form": form})


@login_required
def upload_track_file(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, owner=request.user)

    if request.method == "POST":
        f = request.FILES.get("download_file")
        if not f:
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"errors": {"download_file": ["Please select a file."]}}, status=400)
            messages.error(request, "Please select a file.")
            return redirect("gates:upload_track_file", public_id=track.public_id)

        # Replace existing file efficiently.
        try:
            if track.download_file:
                track.download_file.delete(save=False)
        except Exception:
            pass

        track.download_file = f
        # If owner didn't set a custom download filename, preserve upload name.
        if not (track.download_filename or "").strip():
            track.download_filename = _safe_upload_basename(getattr(f, "name", ""))[:255]
        track.save(update_fields=["download_file", "download_filename", "updated_at"])

        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"redirect": reverse("gates:edit_track", kwargs={"public_id": track.public_id})})
        messages.success(request, "File uploaded.")
        return redirect("gates:edit_track", public_id=track.public_id)

    return render(request, "gates/upload_track_file.html", {"track": track})


@login_required
@require_POST
def delete_track(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, owner=request.user)
    # Delete file from storage first (Django does not always remove it automatically).
    try:
        if track.download_file:
            track.download_file.delete(save=False)
    except Exception:
        # Best-effort; still delete DB row.
        pass
    track.delete()
    messages.success(request, "Gate deleted.")
    return redirect("gates:my_tracks")


@login_required
def create_track(request):
    if request.method == "POST":
        form = GatedTrackCreateForm(request.POST)
        if form.is_valid():
            track: GatedTrack = form.save(commit=False)
            track.owner = request.user
            track.save()
            form.save_m2m()
            # Create any follow targets from the form (best-effort).
            try:
                form._sync_follow_targets(track)  # type: ignore[attr-defined]
            except Exception:
                pass
            messages.success(request, "Gate created. Upload your file in step 2.")
            # After creating, send creator to the file upload step.
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse(
                    {"redirect": reverse("gates:upload_track_file", kwargs={"public_id": track.public_id})}
                )
            return redirect("gates:upload_track_file", public_id=track.public_id)
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse(
                {
                    "errors": form.errors,
                    "non_field_errors": form.non_field_errors(),
                },
                status=400,
            )
        messages.error(request, "Please fix the errors below.")
    else:
        form = GatedTrackCreateForm()
    return render(request, "gates/create_track.html", {"form": form})


def gate(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)

    # Best-effort: resolve track identifiers (helps verification later).
    if (not track.soundcloud_track_urn or not track.soundcloud_artist_urn) and is_configured():
        try:
            data = resolve_track_from_url(track_url=track.soundcloud_track_url, access_token=None)
            track_urn = (data.get("urn") or "").strip() or (
                f"soundcloud:tracks:{data.get('id')}" if data.get("id") is not None else ""
            )
            user = data.get("user") or {}
            artist_urn = (user.get("urn") or "").strip()
            artist_username = (user.get("username") or "").strip()
            dirty_fields = []
            if track_urn and not track.soundcloud_track_urn:
                track.soundcloud_track_urn = track_urn
                dirty_fields.append("soundcloud_track_urn")
            if artist_urn and not track.soundcloud_artist_urn:
                track.soundcloud_artist_urn = artist_urn
                dirty_fields.append("soundcloud_artist_urn")
            if artist_username and not track.soundcloud_artist_username:
                track.soundcloud_artist_username = artist_username
                dirty_fields.append("soundcloud_artist_username")
            if dirty_fields:
                dirty_fields.append("updated_at")
                track.save(update_fields=dirty_fields)
        except Exception:
            pass

    soundcloud_user_urn = request.session.get("soundcloud_user_urn") or ""
    soundcloud_username = request.session.get("soundcloud_username") or ""
    soundcloud_access_token = _get_session_access_token(request)
    access = None
    if soundcloud_user_urn:
        access = GateAccess.objects.filter(track=track, soundcloud_user_urn=soundcloud_user_urn).first()

    follow_targets = list(track.follow_targets.all())

    # Refresh verification status on every page load if we have a token.
    # This prevents stale "verified" state when the user unlikes/unfollows/deletes comments on SoundCloud later.
    if (
        soundcloud_user_urn
        and soundcloud_access_token
        and is_configured()
        and (track.require_like or track.require_comment or track.require_follow)
        and track.soundcloud_track_urn
    ):
        try:
            # Ensure we have artist identity if follow is required.
            if track.require_follow and not track.soundcloud_artist_urn:
                data = resolve_track_from_url(track_url=track.soundcloud_track_url, access_token=soundcloud_access_token)
                user = data.get("user") or {}
                artist_urn = (user.get("urn") or "").strip()
                artist_username = (user.get("username") or "").strip()
                dirty_fields = []
                if artist_urn:
                    track.soundcloud_artist_urn = artist_urn
                    dirty_fields.append("soundcloud_artist_urn")
                if artist_username:
                    track.soundcloud_artist_username = artist_username
                    dirty_fields.append("soundcloud_artist_username")
                if dirty_fields:
                    dirty_fields.append("updated_at")
                    track.save(update_fields=dirty_fields)

            # Best-effort resolve follow targets missing URNs.
            if track.require_follow and follow_targets:
                for t in follow_targets:
                    if t.soundcloud_user_urn or not t.profile_url:
                        continue
                    try:
                        data = resolve_user_from_url(profile_url=t.profile_url, access_token=soundcloud_access_token)
                        urn = (data.get("urn") or "").strip()
                        uname = (data.get("username") or "").strip()
                        if urn:
                            t.soundcloud_user_urn = urn
                            t.soundcloud_username = uname
                            t.save(update_fields=["soundcloud_user_urn", "soundcloud_username", "updated_at"])
                    except Exception:
                        pass

            liked_now = True if not track.require_like else user_liked_track(
                access_token=soundcloud_access_token,
                track_urn=track.soundcloud_track_urn,
                max_pages=10,
            )
            commented_now = True if not track.require_comment else user_commented_on_track(
                access_token=soundcloud_access_token,
                track_identifier=track.soundcloud_track_urn,
                user_urn=soundcloud_user_urn,
                max_pages=10,
            )

            # Follow: can be checked reliably, so we allow downgrading here.
            if not track.require_follow:
                followed_now = True
            else:
                required_urns = []
                if track.soundcloud_artist_urn:
                    required_urns.append(track.soundcloud_artist_urn)
                for t in follow_targets:
                    if t.soundcloud_user_urn:
                        required_urns.append(t.soundcloud_user_urn)
                if not required_urns:
                    followed_now = False
                else:
                    followings = get_followings_urns(access_token=soundcloud_access_token, max_pages=5)
                    followed_now = all((u == soundcloud_user_urn) or (u in followings) for u in required_urns)

            access, _ = GateAccess.objects.get_or_create(
                track=track,
                soundcloud_user_urn=soundcloud_user_urn,
                defaults={"soundcloud_username": soundcloud_username},
            )
            access.soundcloud_username = soundcloud_username or access.soundcloud_username
            # IMPORTANT: avoid "downgrading" a previously-verified status on refresh.
            # SoundCloud APIs can be eventually-consistent; a just-posted comment/like might not show up immediately.
            access.verified_like = bool(access.verified_like or liked_now)
            access.verified_comment = bool(access.verified_comment or commented_now)
            access.verified_follow = bool(followed_now)
            access.verified_at = timezone.now()
            access.last_ip_address = _get_client_ip(request)
            access.last_user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
            access.save(
                update_fields=[
                    "soundcloud_username",
                    "verified_like",
                    "verified_comment",
                    "verified_follow",
                    "verified_at",
                    "last_ip_address",
                    "last_user_agent",
                    "updated_at",
                ]
            )
        except Exception:
            # Don't break the public gate page if SoundCloud API is temporarily failing.
            pass

    liked_ok = bool(access and access.verified_like) if track.require_like else True
    commented_ok = bool(access and access.verified_comment) if track.require_comment else True
    follow_not_applicable = bool(
        track.require_follow
        and soundcloud_user_urn
        and track.soundcloud_artist_urn
        and soundcloud_user_urn == track.soundcloud_artist_urn
    )
    followed_ok = bool(access and access.verified_follow) if track.require_follow else True
    file_ready = bool(track.download_file)
    can_download = bool(file_ready and liked_ok and commented_ok and followed_ok)

    # Build per-target follow status for UI.
    # IMPORTANT: do not depend on having an access token to *display* targets.
    follow_targets_status = []
    artist_follow_status = {
        "urn": track.soundcloud_artist_urn,
        "username": track.soundcloud_artist_username,
        "na": bool(follow_not_applicable),
        "followed": False,
    }
    followings = set()
    if track.require_follow and soundcloud_access_token and is_configured():
        try:
            followings = get_followings_urns(access_token=soundcloud_access_token, max_pages=5)
        except Exception:
            followings = set()

    if track.require_follow:
        # If we have no token, fall back to the stored overall verification to avoid hiding targets
        # (e.g. artist is the logged user and there are additional required follow targets).
        fallback_followed = bool(access and access.verified_follow)

        if artist_follow_status["na"]:
            artist_follow_status["followed"] = True
        elif track.soundcloud_artist_urn and followings:
            artist_follow_status["followed"] = bool(track.soundcloud_artist_urn in followings)
        else:
            artist_follow_status["followed"] = bool(fallback_followed)

        for t in follow_targets:
            na = bool(t.soundcloud_user_urn and soundcloud_user_urn == t.soundcloud_user_urn)
            if na:
                followed = True
            elif t.soundcloud_user_urn and followings:
                followed = bool(t.soundcloud_user_urn in followings)
            else:
                followed = bool(fallback_followed)
            follow_targets_status.append(
                {
                    "id": t.id,
                    "profile_url": t.profile_url,
                    "urn": t.soundcloud_user_urn,
                    "username": t.soundcloud_username,
                    "na": na,
                    "followed": followed,
                }
            )

    context = {
        "track": track,
        "soundcloud_configured": is_configured(),
        "soundcloud_user_urn": soundcloud_user_urn,
        "soundcloud_username": soundcloud_username,
        "soundcloud_has_token": bool(soundcloud_access_token),
        "access": access,
        "liked_ok": liked_ok,
        "commented_ok": commented_ok,
        "followed_ok": followed_ok,
        "follow_not_applicable": follow_not_applicable,
        "follow_targets": follow_targets,
        "artist_follow_status": artist_follow_status,
        "follow_targets_status": follow_targets_status,
        "file_ready": file_ready,
        "can_download": can_download,
    }
    return render(request, "gates/gate.html", context)


def soundcloud_connect(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)
    if not is_configured():
        messages.error(request, "SoundCloud OAuth is not configured yet.")
        return redirect("gates:gate", public_id=track.public_id)

    verifier, challenge = generate_pkce_pair()
    state = secrets.token_urlsafe(24)
    redirect_uri = _get_soundcloud_redirect_uri(request)

    request.session["sc_oauth_state"] = state
    request.session["sc_pkce_verifier"] = verifier
    request.session["sc_target_public_id"] = track.public_id
    request.session.modified = True

    from django.conf import settings as dj_settings

    url = build_authorize_url(
        client_id=dj_settings.SOUNDCLOUD_CLIENT_ID,
        redirect_uri=redirect_uri,
        state=state,
        code_challenge=challenge,
    )
    return redirect(url)


def soundcloud_callback(request):
    error = request.GET.get("error")
    if error:
        messages.error(request, f"SoundCloud auth failed: {error}")
        target = request.session.get("sc_target_public_id") or ""
        if target:
            return redirect("gates:gate", public_id=target)
        return redirect("core:home")

    code = request.GET.get("code") or ""
    state = request.GET.get("state") or ""
    expected_state = request.session.get("sc_oauth_state") or ""
    verifier = request.session.get("sc_pkce_verifier") or ""
    target = request.session.get("sc_target_public_id") or ""

    if not code or not state or not target:
        raise SuspiciousOperation("Missing SoundCloud OAuth parameters.")
    if not expected_state or state != expected_state:
        raise SuspiciousOperation("Invalid SoundCloud OAuth state.")
    if not verifier:
        raise SuspiciousOperation("Missing PKCE verifier.")

    track = get_object_or_404(GatedTrack, public_id=target, is_active=True)
    redirect_uri = _get_soundcloud_redirect_uri(request)

    try:
        token = exchange_code_for_token(code=code, redirect_uri=redirect_uri, code_verifier=verifier)
        me = get_me(access_token=token.access_token)
    except Exception as e:
        messages.error(request, f"Could not complete SoundCloud login: {e}")
        return redirect("gates:gate", public_id=track.public_id)

    user_urn = (me.get("urn") or "").strip()
    username = (me.get("username") or "").strip()
    if not user_urn:
        messages.error(request, "Could not read your SoundCloud user identity.")
        return redirect("gates:gate", public_id=track.public_id)

    # Make sure we can verify against a track identifier (and artist for follow).
    if (not track.soundcloud_track_urn or (track.require_follow and not track.soundcloud_artist_urn)) and is_configured():
        try:
            data = resolve_track_from_url(track_url=track.soundcloud_track_url, access_token=token.access_token)
            track_urn = (data.get("urn") or "").strip() or (
                f"soundcloud:tracks:{data.get('id')}" if data.get("id") is not None else ""
            )
            user = data.get("user") or {}
            artist_urn = (user.get("urn") or "").strip()
            artist_username = (user.get("username") or "").strip()
            dirty_fields = []
            if track_urn and not track.soundcloud_track_urn:
                track.soundcloud_track_urn = track_urn
                dirty_fields.append("soundcloud_track_urn")
            if artist_urn and not track.soundcloud_artist_urn:
                track.soundcloud_artist_urn = artist_urn
                dirty_fields.append("soundcloud_artist_urn")
            if artist_username and not track.soundcloud_artist_username:
                track.soundcloud_artist_username = artist_username
                dirty_fields.append("soundcloud_artist_username")
            if dirty_fields:
                dirty_fields.append("updated_at")
                track.save(update_fields=dirty_fields)
        except Exception:
            pass

    if not track.soundcloud_track_urn:
        messages.error(
            request,
            "This gate isn't fully configured yet (missing track identifier). Try again later.",
        )
        return redirect("gates:gate", public_id=track.public_id)

    # Verify requirements.
    liked = True
    commented = True
    followed = True
    try:
        if track.require_like:
            liked = user_liked_track(access_token=token.access_token, track_urn=track.soundcloud_track_urn)
        if track.require_comment:
            commented = user_commented_on_track(
                access_token=token.access_token,
                track_identifier=track.soundcloud_track_urn,
                user_urn=user_urn,
            )
        if track.require_follow:
            if not track.soundcloud_artist_urn:
                raise RuntimeError("Missing artist profile identifier for follow requirement.")
            # Resolve extra follow targets best-effort.
            for t in track.follow_targets.all():
                if t.soundcloud_user_urn or not t.profile_url:
                    continue
                try:
                    data = resolve_user_from_url(profile_url=t.profile_url, access_token=token.access_token)
                    urn = (data.get("urn") or "").strip()
                    uname = (data.get("username") or "").strip()
                    if urn:
                        t.soundcloud_user_urn = urn
                        t.soundcloud_username = uname
                        t.save(update_fields=["soundcloud_user_urn", "soundcloud_username", "updated_at"])
                except Exception:
                    pass

            required_urns = [track.soundcloud_artist_urn]
            for t in track.follow_targets.all():
                if t.soundcloud_user_urn:
                    required_urns.append(t.soundcloud_user_urn)

            followings = get_followings_urns(access_token=token.access_token, max_pages=5)
            followed = bool(all((u == user_urn) or (u in followings) for u in required_urns))
    except Exception as e:
        messages.error(request, f"Could not verify actions on SoundCloud: {e}")
        return redirect("gates:gate", public_id=track.public_id)

    access, _ = GateAccess.objects.get_or_create(
        track=track,
        soundcloud_user_urn=user_urn,
        defaults={"soundcloud_username": username},
    )
    access.soundcloud_username = username or access.soundcloud_username
    access.last_ip_address = _get_client_ip(request)
    access.last_user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]

    access.verified_like = liked
    access.verified_comment = commented
    access.verified_follow = followed
    access.verified_at = timezone.now()
    access.save(
        update_fields=[
            "soundcloud_username",
            "verified_like",
            "verified_comment",
            "verified_follow",
            "verified_at",
            "last_ip_address",
            "last_user_agent",
            "updated_at",
        ]
    )

    if liked and commented and followed:
        messages.success(request, "Verified! You can download the file now.")
    else:
        missing = []
        if track.require_like and not liked:
            missing.append("like")
        if track.require_comment and not commented:
            missing.append("comment")
        if track.require_follow and not followed:
            missing.append("follow")
        messages.warning(request, f"Not verified yet. Missing: {', '.join(missing)}.")

    # Remember which SoundCloud user this browser session belongs to (no token persisted).
    request.session["soundcloud_user_urn"] = user_urn
    request.session["soundcloud_username"] = username
    # Keep access token in session so users can like/comment directly from gate page.
    request.session["soundcloud_access_token"] = token.access_token
    if token.expires_in:
        request.session["soundcloud_expires_at"] = int(timezone.now().timestamp()) + int(token.expires_in)
    # Clear one-time OAuth session bits
    for k in ("sc_oauth_state", "sc_pkce_verifier", "sc_target_public_id"):
        if k in request.session:
            del request.session[k]
    request.session.modified = True

    return redirect("gates:gate", public_id=track.public_id)


def authorize(request):
    """
    Public redirect URI endpoint for SoundCloud OAuth.
    Configure SoundCloud to redirect to:
      https://download.bandpassrecords.com/authorize

    We simply reuse the same callback handler.
    """
    return soundcloud_callback(request)


@require_POST
def soundcloud_logout(request, public_id: str):
    """
    Clear SoundCloud identity/token from this browser session (fan logout).
    Does NOT affect creator (Django) login.
    """
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)
    for k in (
        "soundcloud_user_urn",
        "soundcloud_username",
        "soundcloud_access_token",
        "soundcloud_expires_at",
        "sc_oauth_state",
        "sc_pkce_verifier",
        "sc_target_public_id",
    ):
        if k in request.session:
            del request.session[k]
    request.session.modified = True
    messages.success(request, "Disconnected from SoundCloud.")
    return redirect("gates:gate", public_id=track.public_id)


@require_POST
def soundcloud_like(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)
    token = _get_session_access_token(request)
    user_urn = (request.session.get("soundcloud_user_urn") or "").strip()
    username = (request.session.get("soundcloud_username") or "").strip()
    if not token or not user_urn:
        messages.error(request, "Please connect SoundCloud first.")
        return redirect("gates:gate", public_id=track.public_id)

    if not track.soundcloud_track_urn and is_configured():
        try:
            urn = resolve_track_urn_from_url(track_url=track.soundcloud_track_url, access_token=token)
            if urn:
                track.soundcloud_track_urn = urn
                track.save(update_fields=["soundcloud_track_urn", "updated_at"])
        except Exception:
            pass

    if not track.soundcloud_track_urn:
        messages.error(request, "Could not identify the SoundCloud track for this gate yet.")
        return redirect("gates:gate", public_id=track.public_id)

    try:
        like_track(access_token=token, track_identifier=track.soundcloud_track_urn)
    except Exception as e:
        messages.error(request, f"Could not like the track on SoundCloud: {e}")
        return redirect("gates:gate", public_id=track.public_id)

    access, _ = GateAccess.objects.get_or_create(
        track=track,
        soundcloud_user_urn=user_urn,
        defaults={"soundcloud_username": username},
    )
    access.soundcloud_username = username or access.soundcloud_username
    access.verified_like = True
    access.last_ip_address = _get_client_ip(request)
    access.last_user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
    access.verified_at = timezone.now()
    access.save(
        update_fields=[
            "soundcloud_username",
            "verified_like",
            "verified_at",
            "last_ip_address",
            "last_user_agent",
            "updated_at",
        ]
    )

    messages.success(request, "Liked the track on SoundCloud.")
    return redirect("gates:gate", public_id=track.public_id)


@require_POST
def soundcloud_follow(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)
    token = _get_session_access_token(request)
    user_urn = (request.session.get("soundcloud_user_urn") or "").strip()
    username = (request.session.get("soundcloud_username") or "").strip()
    if not token or not user_urn:
        messages.error(request, "Please connect SoundCloud first.")
        return redirect("gates:gate", public_id=track.public_id)

    if not track.soundcloud_artist_urn and is_configured():
        try:
            data = resolve_track_from_url(track_url=track.soundcloud_track_url, access_token=token)
            user = data.get("user") or {}
            artist_urn = (user.get("urn") or "").strip()
            artist_username = (user.get("username") or "").strip()
            dirty_fields = []
            if artist_urn and not track.soundcloud_artist_urn:
                track.soundcloud_artist_urn = artist_urn
                dirty_fields.append("soundcloud_artist_urn")
            if artist_username and not track.soundcloud_artist_username:
                track.soundcloud_artist_username = artist_username
                dirty_fields.append("soundcloud_artist_username")
            if dirty_fields:
                dirty_fields.append("updated_at")
                track.save(update_fields=dirty_fields)
        except Exception:
            pass

    if not track.soundcloud_artist_urn:
        messages.error(request, "Could not identify the SoundCloud artist for this gate yet.")
        return redirect("gates:gate", public_id=track.public_id)

    if user_urn != track.soundcloud_artist_urn:
        try:
            follow_user(access_token=token, user_identifier=track.soundcloud_artist_urn)
        except Exception as e:
            messages.error(request, f"Could not follow the artist on SoundCloud: {e}")
            return redirect("gates:gate", public_id=track.public_id)
    else:
        messages.info(request, "You are the artist for this track — artist follow is not required.")

    access, _ = GateAccess.objects.get_or_create(
        track=track,
        soundcloud_user_urn=user_urn,
        defaults={"soundcloud_username": username},
    )
    access.soundcloud_username = username or access.soundcloud_username
    # Recompute overall follow requirement (artist + extra targets).
    required_urns = [track.soundcloud_artist_urn] if track.soundcloud_artist_urn else []
    for t in track.follow_targets.all():
        if t.soundcloud_user_urn:
            required_urns.append(t.soundcloud_user_urn)
    if required_urns:
        followings = get_followings_urns(access_token=token, max_pages=5)
        access.verified_follow = bool(all((u == user_urn) or (u in followings) for u in required_urns))
    else:
        access.verified_follow = False
    access.last_ip_address = _get_client_ip(request)
    access.last_user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
    access.verified_at = timezone.now()
    access.save(
        update_fields=[
            "soundcloud_username",
            "verified_follow",
            "verified_at",
            "last_ip_address",
            "last_user_agent",
            "updated_at",
        ]
    )

    messages.success(request, "Follow updated.")
    return redirect("gates:gate", public_id=track.public_id)


@require_POST
def soundcloud_follow_target(request, public_id: str, target_id: int):
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)
    token = _get_session_access_token(request)
    user_urn = (request.session.get("soundcloud_user_urn") or "").strip()
    username = (request.session.get("soundcloud_username") or "").strip()
    if not token or not user_urn:
        messages.error(request, "Please connect SoundCloud first.")
        return redirect("gates:gate", public_id=track.public_id)

    target = track.follow_targets.filter(id=target_id).first()
    if not target:
        messages.error(request, "Follow target not found.")
        return redirect("gates:gate", public_id=track.public_id)

    if not target.soundcloud_user_urn and is_configured() and target.profile_url:
        try:
            data = resolve_user_from_url(profile_url=target.profile_url, access_token=token)
            target.soundcloud_user_urn = (data.get("urn") or "").strip()
            target.soundcloud_username = (data.get("username") or "").strip()
            target.save(update_fields=["soundcloud_user_urn", "soundcloud_username", "updated_at"])
        except Exception:
            pass

    if not target.soundcloud_user_urn:
        messages.error(request, "Could not identify that SoundCloud profile yet.")
        return redirect("gates:gate", public_id=track.public_id)

    if user_urn == target.soundcloud_user_urn:
        messages.info(request, "You are this profile — follow is not required.")
    else:
        try:
            follow_user(access_token=token, user_identifier=target.soundcloud_user_urn)
        except Exception as e:
            messages.error(request, f"Could not follow the profile on SoundCloud: {e}")
            return redirect("gates:gate", public_id=track.public_id)

    # Recompute overall follow requirement (artist + extra targets).
    followed_ok = True
    if track.require_follow:
        required_urns = []
        if track.soundcloud_artist_urn:
            required_urns.append(track.soundcloud_artist_urn)
        for t in track.follow_targets.all():
            if t.soundcloud_user_urn:
                required_urns.append(t.soundcloud_user_urn)
        if required_urns:
            followings = get_followings_urns(access_token=token, max_pages=5)
            followed_ok = all((u == user_urn) or (u in followings) for u in required_urns)

    access, _ = GateAccess.objects.get_or_create(
        track=track,
        soundcloud_user_urn=user_urn,
        defaults={"soundcloud_username": username},
    )
    access.soundcloud_username = username or access.soundcloud_username
    access.verified_follow = bool(followed_ok)
    access.last_ip_address = _get_client_ip(request)
    access.last_user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
    access.verified_at = timezone.now()
    access.save(
        update_fields=[
            "soundcloud_username",
            "verified_follow",
            "verified_at",
            "last_ip_address",
            "last_user_agent",
            "updated_at",
        ]
    )

    messages.success(request, "Follow updated.")
    return redirect("gates:gate", public_id=track.public_id)


@require_POST
def soundcloud_comment(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)
    token = _get_session_access_token(request)
    user_urn = (request.session.get("soundcloud_user_urn") or "").strip()
    username = (request.session.get("soundcloud_username") or "").strip()
    if not token or not user_urn:
        messages.error(request, "Please connect SoundCloud first.")
        return redirect("gates:gate", public_id=track.public_id)

    body = (request.POST.get("comment_body") or "").strip()
    if not body:
        messages.error(request, "Please enter a comment.")
        return redirect("gates:gate", public_id=track.public_id)

    if not track.soundcloud_track_urn and is_configured():
        try:
            urn = resolve_track_urn_from_url(track_url=track.soundcloud_track_url, access_token=token)
            if urn:
                track.soundcloud_track_urn = urn
                track.save(update_fields=["soundcloud_track_urn", "updated_at"])
        except Exception:
            pass

    if not track.soundcloud_track_urn:
        messages.error(request, "Could not identify the SoundCloud track for this gate yet.")
        return redirect("gates:gate", public_id=track.public_id)

    try:
        post_comment(access_token=token, track_identifier=track.soundcloud_track_urn, body=body)
    except Exception as e:
        messages.error(request, f"Could not post your comment on SoundCloud: {e}")
        return redirect("gates:gate", public_id=track.public_id)

    access, _ = GateAccess.objects.get_or_create(
        track=track,
        soundcloud_user_urn=user_urn,
        defaults={"soundcloud_username": username},
    )
    access.soundcloud_username = username or access.soundcloud_username
    access.verified_comment = True
    access.last_ip_address = _get_client_ip(request)
    access.last_user_agent = request.META.get("HTTP_USER_AGENT", "")[:2000]
    access.verified_at = timezone.now()
    access.save(
        update_fields=[
            "soundcloud_username",
            "verified_comment",
            "verified_at",
            "last_ip_address",
            "last_user_agent",
            "updated_at",
        ]
    )

    messages.success(request, "Comment posted on SoundCloud.")
    return redirect("gates:gate", public_id=track.public_id)


def download(request, public_id: str):
    track = get_object_or_404(GatedTrack, public_id=public_id, is_active=True)

    user_urn = request.session.get("soundcloud_user_urn") or ""
    if not user_urn:
        messages.error(request, "Please connect SoundCloud to verify the gate first.")
        return redirect("gates:gate", public_id=track.public_id)

    access = GateAccess.objects.filter(track=track, soundcloud_user_urn=user_urn).first()
    if not access:
        messages.error(request, "Please verify the gate first.")
        return redirect("gates:gate", public_id=track.public_id)

    if track.require_like and not access.verified_like:
        messages.error(request, "You still need to like the track on SoundCloud.")
        return redirect("gates:gate", public_id=track.public_id)
    if track.require_comment and not access.verified_comment:
        messages.error(request, "You still need to comment on the track on SoundCloud.")
        return redirect("gates:gate", public_id=track.public_id)
    if track.require_follow and not access.verified_follow:
        messages.error(request, "You still need to follow the artist on SoundCloud.")
        return redirect("gates:gate", public_id=track.public_id)

    # Update counters
    GatedTrack.objects.filter(id=track.id).update(download_count=F("download_count") + 1)
    GateAccess.objects.filter(id=access.id).update(
        download_count=F("download_count") + 1,
        last_download_at=timezone.now(),
        last_ip_address=_get_client_ip(request),
        last_user_agent=request.META.get("HTTP_USER_AGENT", "")[:2000],
    )

    if not track.download_file:
        raise Http404("File not found")

    # Clear SoundCloud access token after download (we only need it for verification + actions).
    for k in ("soundcloud_access_token", "soundcloud_expires_at"):
        if k in request.session:
            del request.session[k]
    request.session.modified = True

    filename = track.resolved_download_filename()
    return FileResponse(track.download_file.open("rb"), as_attachment=True, filename=filename)

