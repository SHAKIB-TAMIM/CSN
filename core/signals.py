from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils import timezone
from .models import Profile, Follow, Post, Like, Comment, Notification

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create profile automatically when user is created"""
    if created:
        Profile.objects.get_or_create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    try:
        instance.profile.save()
    except Profile.DoesNotExist:
        # If profile doesn't exist, create it
        Profile.objects.create(user=instance)

@receiver(post_save, sender=Follow)
def update_follow_counts(sender, instance, created, **kwargs):
    """Update follower/following counts when follow relationship changes"""
    if created:
        try:
            instance.follower.profile.update_counts()
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            Profile.objects.get_or_create(user=instance.follower)
            instance.follower.profile.update_counts()
            
        try:
            instance.following.profile.update_counts()
        except Profile.DoesNotExist:
            # Create profile if it doesn't exist
            Profile.objects.get_or_create(user=instance.following)
            instance.following.profile.update_counts()

@receiver(post_delete, sender=Follow)
def update_follow_counts_on_delete(sender, instance, **kwargs):
    """Update counts when follow is deleted"""
    try:
        if instance.follower:
            try:
                instance.follower.profile.update_counts()
            except Profile.DoesNotExist:
                # If profile doesn't exist, create it
                Profile.objects.get_or_create(user=instance.follower)
                if hasattr(instance.follower, 'profile'):
                    instance.follower.profile.update_counts()
    except:
        pass  # User might already be deleted
    
    try:
        if instance.following:
            try:
                instance.following.profile.update_counts()
            except Profile.DoesNotExist:
                # If profile doesn't exist, create it
                Profile.objects.get_or_create(user=instance.following)
                if hasattr(instance.following, 'profile'):
                    instance.following.profile.update_counts()
    except:
        pass  # User might already be deleted

@receiver(post_save, sender=Like)
def update_post_likes_count(sender, instance, created, **kwargs):
    """Update post likes count when like is created"""
    if created:
        try:
            post = instance.post
            post.likes_count = post.likes.count()
            post.save(update_fields=['likes_count'])
        except:
            pass  # Post might be deleted

@receiver(post_delete, sender=Like)
def update_post_likes_count_on_delete(sender, instance, **kwargs):
    """Update likes count when like is deleted"""
    try:
        post = instance.post
        post.likes_count = post.likes.count()
        post.save(update_fields=['likes_count'])
    except:
        pass  # Post might be deleted

@receiver(post_save, sender=Comment)
def update_comment_counts(sender, instance, created, **kwargs):
    """Update comment counts"""
    if created:
        try:
            post = instance.post
            post.comments_count = post.comments.count()
            post.save(update_fields=['comments_count'])
        except:
            pass  # Post might be deleted

@receiver(post_delete, sender=Comment)
def update_comment_counts_on_delete(sender, instance, **kwargs):
    """Update comment counts when comment is deleted"""
    try:
        post = instance.post
        post.comments_count = post.comments.count()
        post.save(update_fields=['comments_count'])
    except:
        pass  # Post might be deleted

@receiver(pre_save, sender=Profile)
def update_last_seen(sender, instance, **kwargs):
    """Update last_seen timestamp"""
    instance.last_seen = timezone.now()