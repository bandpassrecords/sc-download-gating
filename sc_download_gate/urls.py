"""
URL configuration for sc_download_gate project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponseNotFound
from gates import views as gates_views

# Handler for favicon.ico to prevent 404 errors
def favicon_handler(request):
    return HttpResponseNotFound()

# Handler for Chrome DevTools requests
def chrome_devtools_handler(request):
    return HttpResponseNotFound()

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', favicon_handler),  # Handle favicon requests
    path('.well-known/appspecific/com.chrome.devtools.json', chrome_devtools_handler),  # Handle Chrome DevTools requests
    # SoundCloud OAuth redirect URI endpoint
    path('authorize', gates_views.authorize),
    path('', include('core.urls')),
    path('accounts/', include('accounts.urls')),
    path('accounts/', include('allauth.urls')),  # Allauth URLs (login, signup, etc.)
    path('g/', include('gates.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
