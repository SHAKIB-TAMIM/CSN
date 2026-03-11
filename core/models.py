"""
Enhanced models with modern features: followers as ManyToMany, likes, shares, notifications.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from django.core.validators import MinLengthValidator, MaxLengthValidator
from django.urls import reverse
import uuid
import os

def profile_photo_path(instance, filename):
    """Generate file path for new profile photo"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('profile_photos', filename)

def post_photo_path(instance, filename):
    """Generate file path for new post photo"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('post_photos', filename)

class Profile(models.Model):
    """Extended user profile with additional fields"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    profile_photo = models.ImageField(
        default='default_profile.jpg',
        upload_to=profile_photo_path,
        blank=True,
        null=True
    )
    cover_photo = models.ImageField(
        default='default_cover.jpg',
        upload_to='cover_photos',
        blank=True,
        null=True
    )
    bio = models.TextField(
        max_length=500,
        blank=True,
        validators=[MaxLengthValidator(500)]
    )
    location = models.CharField(max_length=100, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    website = models.URLField(max_length=200, blank=True)
    
    # Social links
    facebook = models.URLField(max_length=200, blank=True)
    twitter = models.URLField(max_length=200, blank=True)
    instagram = models.URLField(max_length=200, blank=True)
    linkedin = models.URLField(max_length=200, blank=True)
    
    # Statistics
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)
    posts_count = models.PositiveIntegerField(default=0)
    
    # Status
    is_online = models.BooleanField(default=False)
    last_seen = models.DateTimeField(default=timezone.now)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['is_online']),
            models.Index(fields=['-last_seen']),
        ]

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def get_absolute_url(self):
        return reverse('profile', args=[self.user.username])

    def update_counts(self):
        """Update follower/following counts"""
        self.followers_count = self.user.followers.count()
        self.following_count = self.user.following.count()
        self.posts_count = self.user.posts.count()
        self.save(update_fields=['followers_count', 'following_count', 'posts_count'])


class Follow(models.Model):
    """Follow relationship with timestamp"""
    follower = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='following'
    )
    following = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='followers'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        indexes = [
            models.Index(fields=['follower']),
            models.Index(fields=['following']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Post(models.Model):
    """Enhanced post model with likes, shares, and comments"""
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='posts'
    )
    content = models.TextField(
        validators=[MinLengthValidator(1), MaxLengthValidator(5000)]
    )
    image = models.ImageField(
        upload_to=post_photo_path,
        blank=True,
        null=True
    )
    video = models.FileField(
        upload_to='post_videos',
        blank=True,
        null=True
    )
    
    # Privacy settings
    PRIVACY_CHOICES = [
        ('public', 'Public'),
        ('followers', 'Followers Only'),
        ('private', 'Private'),
    ]
    privacy = models.CharField(
        max_length=10,
        choices=PRIVACY_CHOICES,
        default='public'
    )
    
    # Statistics
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    shares_count = models.PositiveIntegerField(default=0)
    
    # Flags
    is_edited = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at', '-is_pinned']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['privacy']),
        ]

    def __str__(self):
        return f"Post by {self.user.username} at {self.created_at}"

    def get_absolute_url(self):
        return reverse('post-detail', args=[self.id])

    def update_counts(self):
        """Update post statistics"""
        self.likes_count = self.likes.count()
        self.comments_count = self.comments.count()
        self.save(update_fields=['likes_count', 'comments_count'])


class Like(models.Model):
    """Track post likes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')
        indexes = [
            models.Index(fields=['user']),
            models.Index(fields=['post']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.user.username} likes post {self.post.id}"


class Comment(models.Model):
    """Enhanced comment model with likes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comments')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies'
    )
    content = models.TextField(validators=[MaxLengthValidator(1000)])
    likes_count = models.PositiveIntegerField(default=0)
    is_edited = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['post', 'created_at']),
            models.Index(fields=['user']),
        ]

    def __str__(self):
        return f"Comment by {self.user.username} on post {self.post.id}"

    def update_likes_count(self):
        self.likes_count = self.comment_likes.count()
        self.save(update_fields=['likes_count'])


class CommentLike(models.Model):
    """Track comment likes"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='comment_likes')
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name='comment_likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'comment')


class Share(models.Model):
    """Track post shares"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='shares')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='shares')
    content = models.TextField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['-created_at']),
        ]


class SavedPost(models.Model):
    """User saved posts"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_posts')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='saved_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'post')


class Notification(models.Model):
    """Notification system"""
    NOTIFICATION_TYPES = [
        ('follow', 'New Follower'),
        ('like', 'Post Like'),
        ('comment', 'New Comment'),
        ('reply', 'Comment Reply'),
        ('share', 'Post Share'),
        ('mention', 'Mention'),
        ('friend_request', 'Friend Request'),
        ('friend_accept', 'Friend Request Accepted'),
        ('birthday', 'Birthday'),
        ('post', 'New Post'),
    ]

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='actor_notifications'
    )
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    
    text = models.CharField(max_length=255)
    url = models.CharField(max_length=255)
    
    is_read = models.BooleanField(default=False)
    is_emailed = models.BooleanField(default=False)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.text}"


class Message(models.Model):
    """Direct messaging system"""
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages'
    )
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_messages'
    )
    content = models.TextField(validators=[MaxLengthValidator(5000)])
    
    # Media attachments
    image = models.ImageField(upload_to='chat_images/', blank=True, null=True)
    file = models.FileField(upload_to='chat_files/', blank=True, null=True)
    
    # Status
    is_read = models.BooleanField(default=False)
    is_delivered = models.BooleanField(default=False)
    is_edited = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['sender', 'recipient', '-created_at']),
            models.Index(fields=['recipient', 'is_read']),
        ]

    def __str__(self):
        return f"Message from {self.sender.username} to {self.recipient.username}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=['is_read', 'read_at'])


class Conversation(models.Model):
    """Track conversations between users"""
    participants = models.ManyToManyField(User, related_name='conversations')
    last_message = models.ForeignKey(
        Message,
        on_delete=models.SET_NULL,
        null=True,
        related_name='+'
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return f"Conversation between {', '.join([u.username for u in self.participants.all()])}"

    @classmethod
    def get_or_create_conversation(cls, user1, user2):
        """Get or create a conversation between two users"""
        conversations = cls.objects.filter(participants=user1).filter(participants=user2)
        if conversations.exists():
            return conversations.first()
        
        conversation = cls.objects.create()
        conversation.participants.add(user1, user2)
        return conversation


class Story(models.Model):
    """Temporary stories (like Instagram stories)"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='stories')
    image = models.ImageField(upload_to='stories/')
    text = models.CharField(max_length=100, blank=True)
    background_color = models.CharField(max_length=7, default='#000000')
    
    viewed_by = models.ManyToManyField(User, related_name='viewed_stories', blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Story by {self.user.username}"

    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at


class Block(models.Model):
    """User blocking system"""
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocking'
    )
    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='blocked_by'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('blocker', 'blocked')

    def __str__(self):
        return f"{self.blocker.username} blocked {self.blocked.username}"


class Report(models.Model):
    """Content reporting system"""
    REPORT_TYPES = [
        ('post', 'Post'),
        ('comment', 'Comment'),
        ('user', 'User'),
        ('message', 'Message'),
    ]
    
    REASON_CHOICES = [
        ('spam', 'Spam'),
        ('harassment', 'Harassment'),
        ('nudity', 'Nudity'),
        ('violence', 'Violence'),
        ('hate_speech', 'Hate Speech'),
        ('other', 'Other'),
    ]

    reporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_made'
    )
    reported_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='reports_received',
        null=True,
        blank=True
    )
    post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, null=True, blank=True)
    
    report_type = models.CharField(max_length=10, choices=REPORT_TYPES)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    description = models.TextField(max_length=1000, blank=True)
    
    is_reviewed = models.BooleanField(default=False)
    reviewed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews_made'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    action_taken = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Report by {self.reporter.username} - {self.report_type}"


# Signals for automatic updates
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create profile automatically when user is created"""
    if created:
        Profile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save profile when user is saved"""
    instance.profile.save()

@receiver(post_save, sender=Follow)
def update_follow_counts(sender, instance, created, **kwargs):
    """Update follower/following counts when follow relationship changes"""
    if created:
        instance.follower.profile.update_counts()
        instance.following.profile.update_counts()

@receiver(post_delete, sender=Follow)
def update_follow_counts_on_delete(sender, instance, **kwargs):
    """Update counts when follow is deleted"""
    instance.follower.profile.update_counts()
    instance.following.profile.update_counts()

@receiver(post_save, sender=Like)
def update_post_likes_count(sender, instance, created, **kwargs):
    """Update post likes count when like is created/deleted"""
    if created:
        instance.post.likes_count = instance.post.likes.count()
        instance.post.save(update_fields=['likes_count'])

@receiver(post_delete, sender=Like)
def update_post_likes_count_on_delete(sender, instance, **kwargs):
    """Update likes count when like is deleted"""
    instance.post.likes_count = instance.post.likes.count()
    instance.post.save(update_fields=['likes_count'])

@receiver(post_save, sender=Comment)
def update_comment_counts(sender, instance, created, **kwargs):
    """Update comment counts"""
    if created:
        instance.post.comments_count = instance.post.comments.count()
        instance.post.save(update_fields=['comments_count'])

@receiver(post_delete, sender=Comment)
def update_comment_counts_on_delete(sender, instance, **kwargs):
    """Update comment counts when comment is deleted"""
    instance.post.comments_count = instance.post.comments.count()
    instance.post.save(update_fields=['comments_count'])