from django.db.models import Q, Count, Prefetch
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Post, Follow, Notification, Profile, Story
import hashlib
import json

class FeedService:
    """Service for managing user feeds"""
    
    @staticmethod
    def get_feed_queryset(user):
        """Get optimized feed queryset for a user"""
        # Get users that current user follows
        following = user.following.values_list('following', flat=True)
        
        # Get posts from followed users and self
        return Post.objects.filter(
            Q(user_id__in=following) | Q(user=user),
            privacy='public'
        ).select_related(
            'user__profile'
        ).prefetch_related(
            'likes',
            Prefetch(
                'comments',
                queryset=Comment.objects.select_related('user__profile').order_by('created_at')[:3]
            )
        ).annotate(
            like_count=Count('likes', distinct=True),
            comment_count=Count('comments', distinct=True)
        ).order_by('-created_at', '-is_pinned')
    
    @staticmethod
    def get_feed_cache_key(user_id, page):
        """Generate cache key for user feed"""
        return f"feed_{user_id}_page_{page}"
    
    @staticmethod
    def clear_feed_cache(user_id):
        """Clear user's feed cache"""
        pattern = f"feed_{user_id}_page_*"
        # Implementation depends on cache backend
        cache.delete_pattern(pattern) if hasattr(cache, 'delete_pattern') else None
    
    @staticmethod
    def get_stories(user):
        """Get stories from followed users"""
        following = user.following.values_list('following', flat=True)
        return Story.objects.filter(
            user_id__in=following,
            expires_at__gt=timezone.now()
        ).select_related('user__profile').order_by('-created_at')


class UserService:
    """Service for user-related operations"""
    
    @staticmethod
    def get_suggested_users(user, limit=10):
        """Get suggested users to follow"""
        # Get users that current user follows
        following = user.following.values_list('following', flat=True)
        
        # Get users who are followed by people current user follows
        # (friends of friends) but not already followed
        friends_of_friends = Follow.objects.filter(
            follower_id__in=following
        ).exclude(
            following_id__in=following
        ).exclude(
            following=user
        ).values_list('following', flat=True).distinct()[:limit*2]
        
        # Get popular users (by follower count)
        popular = User.objects.exclude(
            id__in=following
        ).exclude(
            id=user.id
        ).annotate(
            follower_count=Count('followers')
        ).order_by('-follower_count')[:limit]
        
        # Combine and deduplicate
        user_ids = set(list(friends_of_friends) + [u.id for u in popular])
        
        return User.objects.filter(
            id__in=user_ids
        ).select_related('profile')[:limit]
    
    @staticmethod
    def search_users(query, exclude_user=None, limit=20):
        """Search users by username, email, or name"""
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(profile__bio__icontains=query)
        ).select_related('profile').distinct()
        
        if exclude_user:
            users = users.exclude(id=exclude_user.id)
        
        return users[:limit]
    
    @staticmethod
    def get_user_stats(user):
        """Get user statistics"""
        return {
            'posts_count': user.posts.count(),
            'followers_count': user.followers.count(),
            'following_count': user.following.count(),
            'likes_received': user.posts.aggregate(total=Count('likes'))['total'],
        }


class NotificationService:
    """Service for creating and managing notifications"""
    
    @staticmethod
    def create_follow_notification(actor, recipient):
        """Create follow notification"""
        if actor == recipient:
            return None
            
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            notification_type='follow',
            text=f'{actor.username} started following you',
            url=f'/profile/{actor.username}/'
        )
    
    @staticmethod
    def create_like_notification(actor, recipient, post):
        """Create like notification"""
        if actor == recipient:
            return None
            
        # Check if similar notification exists (debounce)
        recent = Notification.objects.filter(
            recipient=recipient,
            actor=actor,
            post=post,
            notification_type='like',
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).exists()
        
        if recent:
            return None
            
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            post=post,
            notification_type='like',
            text=f'{actor.username} liked your post',
            url=f'/post/{post.id}/'
        )
    
    @staticmethod
    def create_comment_notification(actor, recipient, post, comment, notification_type='comment'):
        """Create comment notification"""
        if actor == recipient:
            return None
            
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            post=post,
            comment=comment,
            notification_type=notification_type,
            text=f'{actor.username} commented on your post' if notification_type == 'comment' 
                 else f'{actor.username} replied to your comment',
            url=f'/post/{post.id}/#comment-{comment.id}'
        )
    
    @staticmethod
    def create_message_notification(actor, recipient, message):
        """Create message notification"""
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            notification_type='message',
            text=f'{actor.username} sent you a message',
            url=f'/chat/{actor.username}/'
        )
    
    @staticmethod
    def create_post_notification(actor, recipient, post):
        """Create post notification for followers"""
        return Notification.objects.create(
            recipient=recipient,
            actor=actor,
            post=post,
            notification_type='post',
            text=f'{actor.username} created a new post',
            url=f'/post/{post.id}/'
        )
    
    @staticmethod
    def create_birthday_notifications():
        """Create birthday notifications for users"""
        today = timezone.now().date()
        profiles = Profile.objects.filter(
            birth_date__month=today.month,
            birth_date__day=today.day
        ).select_related('user')
        
        notifications = []
        for profile in profiles:
            followers = profile.user.followers.all()
            for follow in followers:
                notifications.append(
                    Notification(
                        recipient=follow.follower,
                        actor=profile.user,
                        notification_type='birthday',
                        text=f'Today is {profile.user.username}\'s birthday!',
                        url=f'/profile/{profile.user.username}/'
                    )
                )
        
        Notification.objects.bulk_create(notifications)


class PostService:
    """Service for post-related operations"""
    
    @staticmethod
    def get_trending_posts(days=7, limit=10):
        """Get trending posts based on engagement"""
        since = timezone.now() - timezone.timedelta(days=days)
        
        return Post.objects.filter(
            created_at__gte=since,
            privacy='public'
        ).annotate(
            engagement=Count('likes') + Count('comments') * 2
        ).order_by('-engagement', '-created_at')[:limit]
    
    @staticmethod
    def get_post_for_user(post_id, user):
        """Get post with permission check"""
        post = Post.objects.select_related(
            'user__profile'
        ).prefetch_related(
            'likes',
            'comments__user__profile',
            'comments__replies__user__profile'
        ).get(id=post_id)
        
        # Check privacy
        if post.privacy == 'private' and post.user != user:
            raise PermissionDenied("You don't have permission to view this post")
        
        if post.privacy == 'followers':
            is_follower = Follow.objects.filter(
                follower=user,
                following=post.user
            ).exists()
            if not is_follower and post.user != user:
                raise PermissionDenied("This post is only visible to followers")
        
        return post
    
    @staticmethod
    def get_post_analytics(post_id):
        """Get analytics for a post"""
        post = Post.objects.get(id=post_id)
        return {
            'likes': post.likes.count(),
            'comments': post.comments.count(),
            'shares': post.shares.count(),
            'engagement_rate': (post.likes.count() + post.comments.count()) / max(post.user.followers.count(), 1),
        }