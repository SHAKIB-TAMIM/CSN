"""
API URL patterns for Core app
"""

from django.urls import path
from . import views

urlpatterns = [
    path('feed/', views.APIFeedView.as_view(), name='api-feed'),
    path('notification-count/', views.APINotificationCountView.as_view(), name='api-notification-count'),
    path('mark-messages-read/', views.APIMarkMessagesRead.as_view(), name='api-mark-messages-read'),
    path('upload-chat-file/', views.APIUploadChatFile.as_view(), name='api-upload-chat-file'),
    path('health/', views.APIHealthCheck.as_view(), name='api-health'),
    path('update-photo/', views.APIUpdateProfilePhoto.as_view(), name='api-update-photo'),
    path('update-cover/', views.APIUpdateCoverPhoto.as_view(), name='api-update-cover'),
    path('user-suggestions/', views.APIUserSuggestions.as_view(), name='api-user-suggestions'),
    path('unread-messages-count/', views.APIUnreadMessagesCount.as_view(), name='unread-messages-count'),
]