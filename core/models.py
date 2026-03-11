"""
Enhanced models with modern features: followers as ManyToMany, likes, shares, notifications.
"""

from django.db import models
from django.contrib.auth.models import User
from django.db.models import Q, Count
from django.utils import timezone
from django.core.validators import FileExtensionValidator, MinLengthValidator, MaxLengthValidator
from django.urls import reverse
from django.utils.text import slugify  
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
    
    # University fields - REQUIRED for new users
    department = models.ForeignKey(
        'Department', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,  # Will be required after email verification
        related_name='students'
    )
    batch = models.CharField(
        max_length=20, 
        blank=True,  # Will be required after email verification
        help_text="e.g., 2024, 2023, etc."
    )
    student_id = models.CharField(
        max_length=50, 
        blank=True,  # Will be required after email verification
        unique=True,
        null=True
    )
    university = models.CharField(
        max_length=200, 
        blank=True, 
        default="Campus University"
    )
    
    # Email verification fields
    email_verified = models.BooleanField(default=False)
    email_verification_otp = models.CharField(max_length=6, blank=True, null=True)
    email_verification_sent_at = models.DateTimeField(null=True, blank=True)
    profile_completed = models.BooleanField(default=False)  # Track if profile is fully completed
    
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
        try:
            self.followers_count = self.user.followers.count() if self.user else 0
            self.following_count = self.user.following.count() if self.user else 0
            self.posts_count = self.user.posts.count() if self.user else 0
            self.save(update_fields=['followers_count', 'following_count', 'posts_count'])
        except:
            # If user doesn't exist, set counts to 0
            self.followers_count = 0
            self.following_count = 0
            self.posts_count = 0
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


# Add this to your Post model (around line 200-220 in your models.py)

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
        upload_to='post_videos/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['mp4', 'mov', 'avi', 'webm', 'mkv'])]
    )
    document = models.FileField(
        upload_to='post_documents/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'zip', 'rar'])]
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
    
    def delete(self, *args, **kwargs):
        """Delete associated files when post is deleted"""
        if self.image and os.path.isfile(self.image.path):
            os.remove(self.image.path)
        if self.video and os.path.isfile(self.video.path):
            os.remove(self.video.path)
        if self.document and os.path.isfile(self.document.path):
            os.remove(self.document.path)
        super().delete(*args, **kwargs)


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
        ('report', 'User Report'),
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
        ('user', 'User'),
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
        ('fake', 'Fake Account'),
        ('inappropriate', 'Inappropriate Content'),
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


# ==================== ANNOUNCEMENT MODELS ====================

class AnnouncementCategory(models.Model):
    """Categories for announcements (General, Departmental, etc.)"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-bullhorn')
    color = models.CharField(max_length=20, default='indigo-600')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Announcement Categories'

    def __str__(self):
        return self.name


class Department(models.Model):
    """University Departments"""
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default='fas fa-building')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.code})"


class Announcement(models.Model):
    """University announcements (notices, events, news)"""
    
    ANNOUNCEMENT_TYPES = [
        ('notice', '📢 Notice'),
        ('event', '🎉 Event'),
        ('news', '📰 News'),
        ('academic', '📚 Academic'),
        ('exam', '📝 Exam Schedule'),
        ('result', '📊 Result'),
        ('holiday', '🎪 Holiday'),
        ('emergency', '🚨 Emergency'),
    ]
    
    AUDIENCE_TYPES = [
        ('general', '🌍 General - Everyone'),
        ('students', '👥 All Students'),
        ('faculty', '👨‍🏫 Faculty Only'),
        ('staff', '👔 Staff Only'),
        ('department', '🏛️ Specific Department'),
        ('batch', '🎓 Specific Batch'),
    ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(unique=True, max_length=255)
    announcement_type = models.CharField(max_length=20, choices=ANNOUNCEMENT_TYPES, default='notice')
    category = models.ForeignKey(AnnouncementCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    
    # Content
    content = models.TextField()
    summary = models.TextField(max_length=500, blank=True, help_text="Brief summary for cards")
    
    # Media
    featured_image = models.ImageField(upload_to='announcements/featured/', blank=True, null=True)
    attachment = models.FileField(upload_to='announcements/attachments/', blank=True, null=True)
    external_link = models.URLField(blank=True, null=True)
    
    # Author/Permissions
    author = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcements_created')
    department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='announcements')
    
    # Targeting
    audience = models.CharField(max_length=20, choices=AUDIENCE_TYPES, default='general')
    target_department = models.ForeignKey(Department, on_delete=models.SET_NULL, null=True, blank=True, related_name='targeted_announcements')
    target_batch = models.CharField(max_length=20, blank=True, help_text="e.g., 2024, 2023, etc.")
    
    # Dates
    published_at = models.DateTimeField(default=timezone.now)
    event_start_date = models.DateTimeField(null=True, blank=True)
    event_end_date = models.DateTimeField(null=True, blank=True)
    deadline = models.DateTimeField(null=True, blank=True, help_text="For submissions, registrations, etc.")
    
    # Location (for events)
    location = models.CharField(max_length=255, blank=True)
    is_virtual = models.BooleanField(default=False)
    meeting_link = models.URLField(blank=True, null=True)
    
    # Status
    is_pinned = models.BooleanField(default=False)
    is_important = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)
    
    # Stats
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-published_at']
        indexes = [
            models.Index(fields=['-published_at']),
            models.Index(fields=['announcement_type']),
            models.Index(fields=['audience']),
            models.Index(fields=['department']),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse('announcement-detail', args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            # Create a unique slug using slugify
            base_slug = slugify(self.title)
            unique_slug = base_slug
            counter = 1
            
            # Check if slug exists and make it unique
            while Announcement.objects.filter(slug=unique_slug).exists():
                unique_slug = f"{base_slug}-{counter}"
                counter += 1
            
            self.slug = unique_slug
        super().save(*args, **kwargs)


class AnnouncementLike(models.Model):
    """Likes on announcements"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcement_likes')
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'announcement')


class AnnouncementComment(models.Model):
    """Comments on announcements"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='announcement_comments')
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    content = models.TextField()
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_edited = models.BooleanField(default=False)
    class Meta:
        ordering = ['created_at']


class AnnouncementView(models.Model):
    """Track views"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='views')
    ip_address = models.GenericIPAddressField()
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'announcement')


class AnnouncementAuthorPermission(models.Model):
    """Users who can create announcements (granted by admin)"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='announcement_permission')
    can_create_general = models.BooleanField(default=False, help_text="Can create general announcements")
    can_create_departmental = models.BooleanField(default=False, help_text="Can create departmental announcements")
    departments = models.ManyToManyField(Department, blank=True, related_name='authorized_users', 
                                         help_text="Which departments they can post for")
    can_create_events = models.BooleanField(default=False)
    can_create_notices = models.BooleanField(default=False)
    can_create_news = models.BooleanField(default=False)
    granted_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='granted_permissions')
    granted_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.username}'s announcement permissions"


# ==================== SIGNALS ====================

from django.db.models.signals import post_save, post_delete, pre_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db import models  # Add this import for F()

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
        try:
            if instance.follower and hasattr(instance.follower, 'profile'):
                instance.follower.profile.update_counts()
        except:
            pass
        
        try:
            if instance.following and hasattr(instance.following, 'profile'):
                instance.following.profile.update_counts()
        except:
            pass

@receiver(post_delete, sender=Follow)
def update_follow_counts_on_delete(sender, instance, **kwargs):
    """Update counts when follow is deleted"""
    try:
        # Safely update follower's profile
        if instance.follower and hasattr(instance.follower, 'profile'):
            try:
                instance.follower.profile.update_counts()
            except:
                pass  # Profile doesn't exist, skip
    except:
        pass
    
    try:
        # Safely update following's profile
        if instance.following and hasattr(instance.following, 'profile'):
            try:
                instance.following.profile.update_counts()
            except:
                pass  # Profile doesn't exist, skip
    except:
        pass

# FIXED: Like signals - use F() to prevent race conditions and double counting
@receiver(post_save, sender=Like)
def update_post_likes_count_on_save(sender, instance, created, **kwargs):
    """Update post likes count when like is created"""
    if created:
        # Use F() to update directly in database
        Post.objects.filter(id=instance.post.id).update(
            likes_count=models.F('likes_count') + 1
        )

@receiver(post_delete, sender=Like)
def update_post_likes_count_on_delete(sender, instance, **kwargs):
    """Update likes count when like is deleted"""
    # Use F() to update directly in database
    Post.objects.filter(id=instance.post.id).update(
        likes_count=models.F('likes_count') - 1
    )

# FIXED: Comment signals - use F() to prevent race conditions
@receiver(post_save, sender=Comment)
def update_comment_counts_on_save(sender, instance, created, **kwargs):
    """Update comment counts when comment is created"""
    if created:
        Post.objects.filter(id=instance.post.id).update(
            comments_count=models.F('comments_count') + 1
        )

@receiver(post_delete, sender=Comment)
def update_comment_counts_on_delete(sender, instance, **kwargs):
    """Update comment counts when comment is deleted"""
    Post.objects.filter(id=instance.post.id).update(
        comments_count=models.F('comments_count') - 1
    )

    
# ==================== DYNAMIC CONTENT MODELS ====================

class SiteStatistic(models.Model):
    """Dynamic statistics for the site"""
    name = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=50, help_text="Can be number or text like '24/7'")
    display_name = models.CharField(max_length=100, help_text="Name to display (e.g., 'Active Users')")
    icon = models.CharField(max_length=50, default='fas fa-users')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']
        verbose_name_plural = 'Site Statistics'

    def __str__(self):
        return f"{self.display_name}: {self.value}"


class TeamMember(models.Model):
    """Team members for about page"""
    name = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    department = models.CharField(max_length=100, blank=True)
    batch = models.CharField(max_length=20, blank=True)
    photo = models.ImageField(upload_to='team/', blank=True, null=True)
    bio = models.TextField(blank=True, max_length=500)
    
    # Social links
    facebook = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    linkedin = models.URLField(blank=True)
    github = models.URLField(blank=True)
    
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name

    @property
    def photo_url(self):
        if self.photo and hasattr(self.photo, 'url'):
            return self.photo.url
        return '/static/core/images/team/default-avatar.png'


class FAQ(models.Model):
    """Frequently Asked Questions for contact page"""
    question = models.CharField(max_length=200)
    answer = models.TextField()
    category = models.CharField(max_length=50, choices=[
        ('general', 'General'),
        ('account', 'Account'),
        ('technical', 'Technical'),
        ('privacy', 'Privacy & Security'),
        ('other', 'Other'),
    ], default='general')
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['category', 'order']
        verbose_name_plural = 'FAQs'

    def __str__(self):
        return self.question


class ContactMessage(models.Model):
    """Store contact form submissions"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='contact_messages')
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    
    # Status tracking
    is_read = models.BooleanField(default=False)
    is_replied = models.BooleanField(default=False)
    replied_at = models.DateTimeField(null=True, blank=True)
    replied_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='replied_messages')
    
    # Metadata
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.subject}"

    def mark_as_read(self):
        self.is_read = True
        self.save(update_fields=['is_read'])