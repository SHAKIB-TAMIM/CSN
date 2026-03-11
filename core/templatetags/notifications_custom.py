
from django import template
from django.urls import reverse
from core.models import Notification

register = template.Library()

@register.simple_tag(takes_context=True)
def notifications_unread_count(context):
    """Get unread notifications count for current user"""
    request = context['request']
    if request.user.is_authenticated:
        return Notification.objects.filter(recipient=request.user, is_read=False).count()
    return 0

@register.inclusion_tag('core/notifications_dropdown.html', takes_context=True)
def render_notifications(context, limit=5):
    """Render notifications dropdown"""
    request = context['request']
    if request.user.is_authenticated:
        notifications = Notification.objects.filter(
            recipient=request.user
        ).select_related('actor__profile').order_by('-created_at')[:limit]
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
    else:
        notifications = []
        unread_count = 0
    
    return {
        'notifications': notifications,
        'unread_count': unread_count,
        'request': request,
    }

@register.simple_tag
def notification_url(notification):
    """Get URL for notification"""
    if notification.url:
        return notification.url
    if notification.post:
        return reverse('post-detail', args=[notification.post.id])
    if notification.comment:
        return reverse('post-detail', args=[notification.comment.post.id])
    if notification.notification_type == 'follow':
        return reverse('profile', args=[notification.actor.username])
    return '#'
