from django.contrib import admin
from .models import (
    Department, AnnouncementCategory, Announcement, 
    AnnouncementAuthorPermission, AnnouncementComment, 
    AnnouncementLike, AnnouncementView, Post, Like, Comment,Report
)
from .models import SiteStatistic, TeamMember, FAQ, ContactMessage

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reporter', 'reported_user', 'reason', 'is_reviewed', 'created_at']
    list_filter = ['reason', 'is_reviewed', 'created_at']
    search_fields = ['reporter__username', 'reported_user__username', 'description']
    readonly_fields = ['created_at']
    fieldsets = (
        ('Report Information', {
            'fields': ('reporter', 'reported_user', 'report_type', 'reason', 'description')
        }),
        ('Review Status', {
            'fields': ('is_reviewed', 'reviewed_by', 'reviewed_at', 'action_taken')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('reporter', 'reported_user', 'reviewed_by')
    
    
@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'code', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'code']
    prepopulated_fields = {'code': ('name',)}

@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'announcement_type', 'author', 'published_at', 'is_active', 'is_pinned']
    list_filter = ['announcement_type', 'is_active', 'is_pinned', 'audience']
    search_fields = ['title', 'content']
    date_hierarchy = 'published_at'
    raw_id_fields = ['author']
    readonly_fields = ['views_count', 'likes_count', 'comments_count']

@admin.register(AnnouncementAuthorPermission)
class AnnouncementAuthorPermissionAdmin(admin.ModelAdmin):
    list_display = ['user', 'can_create_general', 'can_create_departmental', 'is_active', 'granted_at']
    list_filter = ['can_create_general', 'can_create_departmental', 'is_active']
    search_fields = ['user__username', 'user__email']
    filter_horizontal = ['departments']
    raw_id_fields = ['user', 'granted_by']

@admin.register(AnnouncementComment)
class AnnouncementCommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'created_at', 'is_approved']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['content', 'user__username']

@admin.register(AnnouncementLike)
class AnnouncementLikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'created_at']
    list_filter = ['created_at']

@admin.register(AnnouncementView)
class AnnouncementViewAdmin(admin.ModelAdmin):
    list_display = ['user', 'announcement', 'viewed_at', 'ip_address']
    list_filter = ['viewed_at']

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'content_preview', 'privacy', 'likes_count', 'comments_count', 'created_at']
    list_filter = ['privacy', 'is_edited', 'is_pinned', 'created_at']
    search_fields = ['content', 'user__username']
    raw_id_fields = ['user']
    readonly_fields = ['likes_count', 'comments_count', 'shares_count', 'created_at', 'updated_at']
    date_hierarchy = 'created_at'
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username']
    raw_id_fields = ['user', 'post']

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['user', 'post', 'content_preview', 'created_at', 'is_edited']
    list_filter = ['is_edited', 'created_at']
    search_fields = ['content', 'user__username']
    raw_id_fields = ['user', 'post']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'

@admin.register(SiteStatistic)
class SiteStatisticAdmin(admin.ModelAdmin):
    list_display = ['display_name', 'value', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'display_name']

@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ['name', 'position', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['is_active']
    search_fields = ['name', 'position']

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer']

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'subject', 'is_read', 'is_replied', 'created_at']
    list_filter = ['is_read', 'is_replied', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['name', 'email', 'subject', 'message', 'ip_address', 'user_agent', 'created_at']
    actions = ['mark_as_read', 'mark_as_unread', 'mark_as_replied']
    
    fieldsets = (
        ('Message Information', {
            'fields': ('name', 'email', 'subject', 'message')
        }),
        ('Status', {
            'fields': ('is_read', 'is_replied', 'replied_at', 'replied_by')
        }),
        ('Technical Details', {
            'fields': ('ip_address', 'user_agent', 'created_at'),
            'classes': ('collapse',)
        }),
    )
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
    mark_as_read.short_description = "Mark selected messages as read"
    
    def mark_as_unread(self, request, queryset):
        queryset.update(is_read=False)
    mark_as_unread.short_description = "Mark selected messages as unread"
    
    def mark_as_replied(self, request, queryset):
        queryset.update(is_replied=True, replied_at=timezone.now(), replied_by=request.user)
    mark_as_replied.short_description = "Mark selected messages as replied"    