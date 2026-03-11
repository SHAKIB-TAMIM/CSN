
"""
Context processors for Campus Social Network
"""

from django.conf import settings
from .models import Notification

def site_settings(request):
    """Add site settings to context"""
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Campus Social Network'),
        'SITE_DESCRIPTION': getattr(settings, 'SITE_DESCRIPTION', 'Connect with campus friends'),
    }

def notifications(request):
    """Add notifications to context"""
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related('actor__profile').order_by('-created_at')[:5]
        
        unread_count = Notification.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
    else:
        notifications = []
        unread_count = 0
    
    return {
        'notifications': notifications,
        'notifications_unread_count': unread_count,
    }

def online_status(request):
    """Add online status to context"""
    if request.user.is_authenticated:
        return {
            'is_online': getattr(request.user.profile, 'is_online', False),
            'last_seen': getattr(request.user.profile, 'last_seen', None),
        }
    return {}
