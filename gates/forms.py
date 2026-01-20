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

