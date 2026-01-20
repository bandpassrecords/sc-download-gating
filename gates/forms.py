import os

from django import forms

from .models import GatedTrack


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


class GatedTrackCreateForm(forms.ModelForm):
    class Meta:
        model = GatedTrack
        fields = (
            "title",
            "description",
            "soundcloud_track_url",
            "require_like",
            "require_comment",
            "require_follow",
            "download_file",
            "download_filename",
            "is_listed",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def clean_soundcloud_track_url(self):
        url = (self.cleaned_data.get("soundcloud_track_url") or "").strip()
        if "soundcloud.com" not in url.lower():
            raise forms.ValidationError("Please enter a valid SoundCloud track URL.")
        return url

    def save(self, commit=True):
        instance: GatedTrack = super().save(commit=False)
        # If the user didn't define a custom download filename, preserve the original upload name.
        if not (instance.download_filename or "").strip():
            f = self.cleaned_data.get("download_file")
            if f is not None and getattr(f, "name", None):
                instance.download_filename = _safe_upload_basename(f.name)[:255]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class GatedTrackUpdateForm(forms.ModelForm):
    class Meta:
        model = GatedTrack
        fields = (
            "title",
            "description",
            "require_like",
            "require_comment",
            "require_follow",
            "download_file",
            "download_filename",
            "is_listed",
            "is_active",
        )
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Allow leaving file unchanged on edit
        self.fields["download_file"].required = False

    def clean_download_file(self):
        # Keep existing file if none uploaded (or "clear" attempted)
        f = self.cleaned_data.get("download_file")
        if f:
            return f
        if self.instance and getattr(self.instance, "download_file", None):
            return self.instance.download_file
        return f

    def save(self, commit=True):
        instance: GatedTrack = super().save(commit=False)
        # If a new file was uploaded and the user didn't set a custom name, preserve original upload name.
        if "download_file" in getattr(self, "files", {}):
            if not (instance.download_filename or "").strip():
                f = self.cleaned_data.get("download_file")
                if f is not None and getattr(f, "name", None):
                    instance.download_filename = _safe_upload_basename(f.name)[:255]
        if commit:
            instance.save()
            self.save_m2m()
        return instance

