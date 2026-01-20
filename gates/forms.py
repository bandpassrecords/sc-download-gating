from django import forms

from .models import GatedTrack


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

