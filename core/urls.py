from django.shortcuts import redirect
from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .api import urls as api_urls

urlpatterns = [
    # Authentication
    path('', views.HomeView.as_view(), name='index'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-otp/', views.ResendOTPView.as_view(), name='resend-otp'),
    path('complete-profile/', views.CompleteProfileView.as_view(), name='complete-profile'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html',next_page='welcome'), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('accounts/confirm-email/', lambda request: redirect('index'), name='account_confirm_email_redirect'),
    # Password Reset (Django built-in)
    path('password-change/', auth_views.PasswordChangeView.as_view(
        template_name='core/password_change.html',
        success_url='/password-change/done/'
    ), name='password_change'),

    path('password-change/done/', auth_views.PasswordChangeDoneView.as_view(
        template_name='core/password_change_done.html'
    ), name='password_change_done'),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='core/password_reset.html'
         ), name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='core/password_reset_done.html'
         ), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='core/password_reset_confirm.html'
         ), name='password_reset_confirm'),
    path('password-reset-complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='core/password_reset_complete.html'
         ), name='password_reset_complete'),

    # Main views
    path('feed/', views.FeedView.as_view(), name='feed'),
    path('explore/', views.ExploreView.as_view(), name='explore'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('discover/', views.DiscoverUsersView.as_view(), name='discover-users'),
    # Profile
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile-edit'),
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),


    # Posts
    path('post/new/', views.PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('post/<int:pk>/save/', views.save_post, name='save-post'),
    path('post/<int:pk>/unsave/', views.unsave_post, name='unsave-post'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post-delete'),
    path('post/<int:pk>/edit/', views.PostUpdateView.as_view(), name='post-update'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post-delete'),

    # Interactions
    path('post/<int:post_id>/like/', views.LikeToggleView.as_view(), name='post-like'),
    path('post/<int:post_id>/comment/', views.CommentCreateView.as_view(), name='post-comment'),
    path('follow/<str:username>/', views.FollowToggleView.as_view(), name='follow-toggle'),
    path('report/<str:username>/', views.ReportUserView.as_view(), name='report-user'),

    path('saved-posts/', views.SavedPostsView.as_view(), name='saved-posts'),
    path('api/following-for-share/', views.get_following_for_share, name='following-for-share'),
    # Messaging
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('chat/<str:username>/', views.ChatView.as_view(), name='chat-with'),
    path('chat/messages/<str:username>/', views.chat_messages, name='chat-messages'),
    path('chat/send/<str:username>/', views.send_message, name='chat-send'),
    path('chat/typing/<str:username>/', views.typing_indicator, name='chat-typing'),

    # Notifications
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),

    # Stories
    path('story/new/', views.StoryCreateView.as_view(), name='story-create'),

    # Block/Unblock
    path('block/<str:username>/', views.BlockUserView.as_view(), name='block-user'),
    path('unblock/<str:username>/', views.UnblockUserView.as_view(), name='unblock-user'),


    path('delete-account/confirm/', views.DeleteAccountConfirmView.as_view(), name='delete-account-confirm'),
    path('delete-account/', views.DeleteAccountView.as_view(), name='delete-account'),

    # Welcome redirect
    path('welcome/', views.welcome, name='welcome'),

    # API endpoints
    path('api/', include('core.api.urls')),

    path('announcement/create/', views.AnnouncementCreateView.as_view(), name='announcement-create'),
    path('announcement/<slug:slug>/', views.AnnouncementDetailView.as_view(), name='announcement-detail'),
    path('announcement/<int:pk>/like/', views.AnnouncementLikeToggleView.as_view(), name='announcement-like'),
    path('announcement/<int:pk>/comment/', views.AnnouncementCommentView.as_view(), name='announcement-comment'),
    path('announcement/<int:pk>/edit/', views.AnnouncementUpdateView.as_view(), name='announcement-update'),
    path('announcement/<int:pk>/delete/', views.AnnouncementDeleteView.as_view(), name='announcement-delete'),
    path('admin/announcement-permissions/', views.AdminAnnouncementPermissionsView.as_view(), name='admin-announcement-permissions'),
    path('announcement/comment/<int:pk>/edit/', views.AnnouncementCommentUpdateView.as_view(), name='announcement-comment-edit'),
    path('announcement/comment/<int:pk>/delete/', views.AnnouncementCommentDeleteView.as_view(), name='announcement-comment-delete'),
    path('report-post/', views.report_post, name='report-post'),
    path('comment/<int:pk>/edit/', views.CommentUpdateView.as_view(), name='comment-update'),
    path('comment/<int:pk>/delete/', views.CommentDeleteView.as_view(), name='comment-delete'),

    # Legal & Information Pages
    path('about/', views.AboutView.as_view(), name='about'),
    path('contact/', views.ContactView.as_view(), name='contact'),
    path('privacy/', views.PrivacyView.as_view(), name='privacy'),
    path('terms/', views.TermsView.as_view(), name='terms'),

]
