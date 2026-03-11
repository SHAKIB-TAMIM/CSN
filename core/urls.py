from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from .api import urls as api_urls

urlpatterns = [
    # Authentication
    path('', views.HomeView.as_view(), name='index'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    
    # Password Reset (Django built-in)
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
    
    # Profile
    path('profile/<str:username>/', views.ProfileView.as_view(), name='profile'),
    path('profile/edit/', views.ProfileUpdateView.as_view(), name='profile-edit'),
    
    # Posts
    path('post/new/', views.PostCreateView.as_view(), name='post-create'),
    path('post/<int:pk>/', views.PostDetailView.as_view(), name='post-detail'),
    path('post/<int:pk>/delete/', views.PostDeleteView.as_view(), name='post-delete'),
    
    # Interactions
    path('post/<int:post_id>/like/', views.LikeToggleView.as_view(), name='post-like'),
    path('post/<int:post_id>/comment/', views.CommentCreateView.as_view(), name='post-comment'),
    path('follow/<str:username>/', views.FollowToggleView.as_view(), name='follow-toggle'),
    
    # Messaging
    path('chat/', views.ChatView.as_view(), name='chat'),
    path('chat/<str:username>/', views.ChatView.as_view(), name='chat-with'),
    
    # Notifications
    path('notifications/', views.NotificationsView.as_view(), name='notifications'),
    
    # Stories
    path('story/new/', views.StoryCreateView.as_view(), name='story-create'),
    
    # Block/Unblock
    path('block/<str:username>/', views.BlockUserView.as_view(), name='block-user'),
    path('unblock/<str:username>/', views.UnblockUserView.as_view(), name='unblock-user'),
    
    # Welcome redirect
    path('welcome/', views.ProfileView.as_view(), name='welcome'),
    
    # API endpoints
    path('api/', include(api_urls)),
]