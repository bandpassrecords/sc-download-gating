from django.conf import settings


def app_brand(request):
    """
    Provide app branding values to templates.
    """
    return {
        "APP_NAME": getattr(settings, "APP_NAME", "sc_download_gating"),
        "APP_DISPLAY_NAME": getattr(settings, "APP_DISPLAY_NAME", "sc_download_gating"),
    }

