from django.db.models import Q, Count, Prefetch
from django.core.cache import cache
from django.utils import timezone
from django.contrib.auth.models import User
from .models import Post, Follow, Notification, Profile, Story, Comment
import hashlib
import json
from datetime import timedelta
from .models import Announcement
from .models import AnnouncementAuthorPermission

class FeedService:
    """Service for managing user feeds"""
    
    @staticmethod
    def get_feed_queryset(user):
        """Get optimized feed queryset for a user"""
        # Get users that current user follows
        following = user.following.values_list('following', flat=True)
        
        # Get posts from followed users (not private) and public posts from everyone
        return Post.objects.filter(
            # Posts from followed users that are not private
            (Q(user_id__in=following) & ~Q(privacy='private')) |
            # Public posts from all users
            Q(privacy='public') |
            # User's own posts
            Q(user=user)
        ).select_related(
            'user__profile'
        ).prefetch_related(
            'likes',
            Prefetch(
                'comments',
                queryset=Comment.objects.select_related('user__profile').order_by('created_at')
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
        if hasattr(cache, 'delete_pattern'):
            cache.delete_pattern(pattern)
    
    @staticmethod
    def get_stories(user):
        """Get stories from followed users"""
        from .models import Story, Follow
        
        # Get users that current user follows
        following = user.following.values_list('following', flat=True)
        
        # Get active stories (not expired) from followed users
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
        
        # Get popular users (by follower count) - EXCLUDING STAFF AND ADMIN
        popular = User.objects.exclude(
            id__in=following
        ).exclude(
            id=user.id
        ).exclude(
            is_staff=True  # Exclude staff users
        ).exclude(
            is_superuser=True  # Exclude superusers/admins
        ).annotate(
            follower_count=Count('followers')
        ).order_by('-follower_count')[:limit]
        
        # Combine and deduplicate
        user_ids = set(list(friends_of_friends) + [u.id for u in popular])
        
        return User.objects.filter(
            id__in=user_ids,
            is_staff=False,
            is_superuser=False
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
        from django.core.exceptions import PermissionDenied
        
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


class AnnouncementService:
    """Service for managing announcements"""
    
    @staticmethod
    def get_visible_announcements(user):
        """Get announcements visible to a specific user"""
        from django.db.models import Q
        from .models import Announcement
        
        base_qs = Announcement.objects.filter(
            is_active=True,
            is_archived=False
        ).select_related(
            'author__profile',
            'category',
            'department'
        ).prefetch_related(
            'likes',
            'comments'
        )
        
        # Filter by audience
        if user.is_authenticated:
            # For logged-in users
            if user.is_staff or user.is_superuser:
                # Staff sees everything
                return base_qs
            
            # Regular users - check if they have department/batch
            user_dept = None
            user_batch = None
            if hasattr(user, 'profile') and user.profile:
                user_dept = user.profile.department
                user_batch = user.profile.batch
            
            # Build query
            query = Q(audience='general') | Q(audience='students')
            
            if user_dept:
                query |= Q(audience='department', target_department=user_dept)
            
            if user_batch:
                query |= Q(audience='batch', target_batch=user_batch)
            
            return base_qs.filter(query).distinct()
        else:
            # Anonymous users only see general announcements
            return base_qs.filter(audience='general')
    
    @staticmethod
    def can_create_announcement(user, announcement_type=None, department=None):
        """Check if user can create announcements"""
        
        print(f"\n🔥🔥🔥🔥🔥 CAN_CREATE_ANNOUNCEMENT CALLED for user: {user.username} 🔥🔥🔥🔥🔥")
        print(f"User ID: {user.id}")
        print(f"Is staff: {user.is_staff}")
        print(f"Is superuser: {user.is_superuser}")
        
        # Admin and staff can always create
        if user.is_superuser or user.is_staff:
            print(f"✅ User is superuser/staff - returning True")
            return True
        
        # Try to get permission
        try:
            print(f"🔎 Attempting to get AnnouncementAuthorPermission for user {user.username}...")
            from .models import AnnouncementAuthorPermission
            permission = AnnouncementAuthorPermission.objects.get(user=user)
            print(f"✅ Found permission record!")
            print(f"   - can_create_general: {permission.can_create_general}")
            print(f"   - can_create_departmental: {permission.can_create_departmental}")
            print(f"   - can_create_events: {permission.can_create_events}")
            print(f"   - can_create_notices: {permission.can_create_notices}")
            print(f"   - can_create_news: {permission.can_create_news}")
            print(f"   - is_active: {permission.is_active}")
            
            if not permission.is_active:
                print("❌ Permission is not active - returning False")
                return False
            
            # Check if they have any permission
            result = (permission.can_create_general or 
                    permission.can_create_departmental or 
                    permission.can_create_events or 
                    permission.can_create_notices or 
                    permission.can_create_news)
            print(f"📊 User has ANY permission: {result} - returning {result}")
            return result
            
        except AnnouncementAuthorPermission.DoesNotExist:
            print(f"❌ No AnnouncementAuthorPermission found for user {user.username} - returning False")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {type(e).__name__}: {e} - returning False")
            return False
    
        
    @staticmethod
    def can_edit_announcement(user, announcement):
            """Check if user can edit an announcement"""
            # Author can always edit their own
            if user == announcement.author:
                return True
            
            # Superusers and staff can edit any
            if user.is_superuser or user.is_staff:
                return True
            
            # Check if user has permission for this type
            return AnnouncementService.can_create_announcement(
                user, 
                announcement_type=announcement.announcement_type,
                department=announcement.department
            )
    
    @staticmethod
    def can_delete_announcement(user, announcement):
        """Check if user can delete an announcement"""
        # Same logic as edit
        return AnnouncementService.can_edit_announcement(user, announcement)
    
    @staticmethod
    def get_trending_announcements(limit=10):
        """Get trending announcements based on views and likes"""
        week_ago = timezone.now() - timedelta(days=7)
        
        return Announcement.objects.filter(
            published_at__gte=week_ago,
            is_active=True
        ).annotate(
            engagement=Count('likes') + Count('comments') * 2 + Count('views') * 0.5
        ).order_by('-engagement', '-published_at')[:limit]
    
    @staticmethod
    def get_department_announcements(department_code, limit=20):
        """Get announcements for a specific department"""
        from .models import Announcement, Department
        
        try:
            dept = Department.objects.get(code=department_code)
            return Announcement.objects.filter(
                Q(department=dept) | Q(target_department=dept),
                is_active=True
            ).order_by('-published_at')[:limit]
        except Department.DoesNotExist:
            return Announcement.objects.none()
    
    @staticmethod
    def get_upcoming_events(days=30, limit=10):
        """Get upcoming events"""
        from django.utils import timezone
        from datetime import timedelta
        from .models import Announcement
        
        now = timezone.now()
        future = now + timedelta(days=days)
        
        return Announcement.objects.filter(
            announcement_type='event',
            event_start_date__gte=now,
            event_start_date__lte=future,
            is_active=True
        ).order_by('event_start_date')[:limit]
    
    @staticmethod
    def increment_view_count(announcement, user=None, ip_address=None):
        """Increment view count for an announcement"""
        from .models import AnnouncementView
        
        if user and user.is_authenticated:
            view, created = AnnouncementView.objects.get_or_create(
                user=user,
                announcement=announcement,
                defaults={'ip_address': ip_address or '0.0.0.0'}
            )
        else:
            # For anonymous users, track by IP
            if ip_address:
                view, created = AnnouncementView.objects.get_or_create(
                    ip_address=ip_address,
                    announcement=announcement,
                    defaults={'user': None}
                )
            else:
                created = False
        
        if created:
            announcement.views_count += 1
            announcement.save(update_fields=['views_count'])
        
        return created
    
    @staticmethod
    def search_announcements(query, user=None):
        """Search announcements by title or content"""
        from django.db.models import Q
        from .models import Announcement
        
        base_qs = Announcement.objects.filter(is_active=True)
        
        # Apply visibility filters
        if user:
            base_qs = AnnouncementService.get_visible_announcements(user)
        
        # Apply search query
        return base_qs.filter(
            Q(title__icontains=query) |
            Q(content__icontains=query) |
            Q(summary__icontains=query)
        ).distinct()