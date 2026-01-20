from django.shortcuts import render
from django.db.models import Count
from gates.models import GatedTrack
from accounts.models import UserProfile


def home(request):
    """Homepage with featured content"""
    
    featured_tracks = GatedTrack.objects.filter(is_active=True, is_listed=True).select_related(
        "owner"
    ).order_by("-download_count", "-created_at")[:8]

    recent_tracks = GatedTrack.objects.filter(is_active=True, is_listed=True).select_related(
        "owner"
    ).order_by("-created_at")[:6]

    stats = {
        "total_gates": GatedTrack.objects.filter(is_active=True).count(),
        "total_creators": UserProfile.objects.count(),
    }
    
    context = {
        "featured_tracks": featured_tracks,
        "recent_tracks": recent_tracks,
        "stats": stats,
    }
    
    return render(request, 'core/home.html', context)


def about(request):
    """About page"""
    return render(request, 'core/about.html')


def contact(request):
    """Contact page"""
    return render(request, 'core/contact.html')


def help_page(request):
    """Help/FAQ page"""
    return render(request, 'core/help.html')


def privacy_policy(request):
    """Privacy policy page"""
    return render(request, 'core/privacy_policy.html')


def terms_of_service(request):
    """Terms of service page"""
    return render(request, 'core/terms_of_service.html')
