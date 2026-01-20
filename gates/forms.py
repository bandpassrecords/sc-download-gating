import os

from django import forms

from .models import GatedFollowTarget, GatedTrack
from .soundcloud import is_configured, resolve_user_from_url


def _safe_upload_basename(upload_name: str) -> str:
    """
    Preserve the uploaded filename as-is (spaces/parentheses included),
    while stripping any path components for safety.
    """
    name = (upload_name or "").strip()
    # Browsers typically send basename only, but be defensive against paths.
    name = name.replace("\\", "/").split("/")[-1]
    name = os.path.basename(name)
    return name


_INPUT_CLASS = "form-control bg-dark border-dark text-light"
_TEXTAREA_CLASS = "form-control bg-dark border-dark text-light"
_CHECKBOX_CLASS = "form-check-input bg-dark border-dark"


def _apply_bootstrap_dark_classes(form: forms.Form):
    for name, field in form.fields.items():
        widget = field.widget
        # Booleans
        if isinstance(widget, (forms.CheckboxInput,)):
            widget.attrs["class"] = _CHECKBOX_CLASS
            continue
        # Textareas
        if isinstance(widget, forms.Textarea):
            widget.attrs["class"] = _TEXTAREA_CLASS
            continue
        # Everything else (text/url/file/etc)
        widget.attrs["class"] = _INPUT_CLASS


class GatedTrackCreateForm(forms.ModelForm):
    # Rendered manually as a dynamic list of inputs (see templates).
    additional_follow_profiles = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Optional: require following additional SoundCloud profiles (collabs).",
        label="Additional profiles to follow (optional)",
    )

    class Meta:
        model = GatedTrack
        fields = (
            "title",
            "description",
            "soundcloud_track_url",
            "require_like",
            "require_comment",
            "require_follow",
            "download_filename",
            "is_listed",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_dark_classes(self)

    def clean_soundcloud_track_url(self):
        url = (self.cleaned_data.get("soundcloud_track_url") or "").strip()
        if "soundcloud.com" not in url.lower():
            raise forms.ValidationError("Please enter a valid SoundCloud track URL.")
        return url

    def save(self, commit=True):
        instance: GatedTrack = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            self._sync_follow_targets(instance)
        return instance

    def _sync_follow_targets(self, track: GatedTrack):
        urls = [u.strip() for u in self.data.getlist("additional_follow_profiles") if u.strip()]
        if not urls:
            raw = (self.cleaned_data.get("additional_follow_profiles") or "").strip()
            urls = [u.strip() for u in raw.splitlines() if u.strip()]

        # Replace targets (simple + predictable)
        track.follow_targets.all().delete()

        seen = set()
        cleaned = []
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            cleaned.append(url)

        for url in cleaned[:25]:
            urn = ""
            username = ""
            if is_configured():
                try:
                    data = resolve_user_from_url(profile_url=url, access_token=None)
                    urn = (data.get("urn") or "").strip()
                    username = ((data.get("username") or "") if isinstance(data, dict) else "").strip()
                except Exception:
                    pass
            GatedFollowTarget.objects.create(
                track=track,
                profile_url=url,
                soundcloud_user_urn=urn,
                soundcloud_username=username,
            )


class GatedTrackUpdateForm(forms.ModelForm):
    # Rendered manually as a dynamic list of inputs (see templates).
    additional_follow_profiles = forms.CharField(
        required=False,
        widget=forms.HiddenInput(),
        help_text="Optional: require following additional SoundCloud profiles (collabs).",
        label="Additional profiles to follow (optional)",
    )

    class Meta:
        model = GatedTrack
        fields = (
            "title",
            "description",
            "require_like",
            "require_comment",
            "require_follow",
            "download_filename",
            "is_listed",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _apply_bootstrap_dark_classes(self)

    def save(self, commit=True):
        instance: GatedTrack = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
            self._sync_follow_targets(instance)
        return instance

    def _sync_follow_targets(self, track: GatedTrack):
        urls = [u.strip() for u in self.data.getlist("additional_follow_profiles") if u.strip()]
        if not urls:
            raw = (self.cleaned_data.get("additional_follow_profiles") or "").strip()
            urls = [u.strip() for u in raw.splitlines() if u.strip()]

        track.follow_targets.all().delete()

        seen = set()
        cleaned = []
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            cleaned.append(url)

        for url in cleaned[:25]:
            urn = ""
            username = ""
            if is_configured():
                try:
                    data = resolve_user_from_url(profile_url=url, access_token=None)
                    urn = (data.get("urn") or "").strip()
                    username = ((data.get("username") or "") if isinstance(data, dict) else "").strip()
                except Exception:
                    pass
            GatedFollowTarget.objects.create(
                track=track,
                profile_url=url,
                soundcloud_user_urn=urn,
                soundcloud_username=username,
            )

