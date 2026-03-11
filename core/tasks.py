from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from .models import User, Notification, Post
from .services import NotificationService

@shared_task
def send_welcome_email(user_id):
    """Send welcome email to new user"""
    try:
        user = User.objects.get(id=user_id)
        subject = 'Welcome to Campus Social Network!'
        html_message = render_to_string('emails/welcome.html', {'user': user})
        plain_message = strip_tags(html_message)
        
        send_mail(
            subject,
            plain_message,
            settings.DEFAULT_FROM_EMAIL,
            [user.email],
            html_message=html_message,
            fail_silently=False,
        )
    except User.DoesNotExist:
        pass

@shared_task
def send_notification_email(notification_id):
    """Send email notification"""
    try:
        notification = Notification.objects.get(id=notification_id)
        if not notification.is_emailed:
            subject = f'New {notification.get_notification_type_display()}'
            html_message = render_to_string(
                'emails/notification.html', 
                {'notification': notification}
            )
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [notification.recipient.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            notification.is_emailed = True
            notification.save(update_fields=['is_emailed'])
    except Notification.DoesNotExist:
        pass

@shared_task
def notify_followers_new_post(post_id):
    """Notify followers about new post"""
    try:
        post = Post.objects.select_related('user').get(id=post_id)
        followers = post.user.followers.select_related('follower').all()
        
        for follow in followers:
            NotificationService.create_post_notification(
                actor=post.user,
                recipient=follow.follower,
                post=post
            )
    except Post.DoesNotExist:
        pass

@shared_task
def cleanup_expired_stories():
    """Delete expired stories"""
    from .models import Story
    Story.objects.filter(expires_at__lt=timezone.now()).delete()

@shared_task
def update_online_status():
    """Update online status (set offline after 5 minutes of inactivity)"""
    from .models import Profile
    from django.utils import timezone
    from datetime import timedelta
    
    five_minutes_ago = timezone.now() - timedelta(minutes=5)
    Profile.objects.filter(
        last_seen__lt=five_minutes_ago,
        is_online=True
    ).update(is_online=False)

@shared_task
def send_daily_digest():
    """Send daily digest emails to users"""
    from django.db.models import Count
    from datetime import timedelta
    
    yesterday = timezone.now() - timedelta(days=1)
    
    for user in User.objects.filter(is_active=True):
        # Get unread notifications from last 24 hours
        notifications = Notification.objects.filter(
            recipient=user,
            created_at__gte=yesterday,
            is_read=False
        ).count()
        
        # Get new posts from followed users
        followed_users = user.following.values_list('following', flat=True)
        new_posts = Post.objects.filter(
            user_id__in=followed_users,
            created_at__gte=yesterday
        ).count()
        
        if notifications > 0 or new_posts > 0:
            subject = 'Your Campus Social Network Daily Digest'
            html_message = render_to_string(
                'emails/daily_digest.html',
                {
                    'user': user,
                    'notifications': notifications,
                    'new_posts': new_posts,
                }
            )
            plain_message = strip_tags(html_message)
            
            send_mail(
                subject,
                plain_message,
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                html_message=html_message,
                fail_silently=True,
            )

@shared_task
def update_statistics():
    from django.core.management import call_command
    call_command('update_statistics')            