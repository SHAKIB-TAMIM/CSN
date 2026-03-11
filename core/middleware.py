
"""
Custom middleware for Campus Social Network
"""

from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from .models import Profile, Notification

class OnlineStatusMiddleware:
    """Middleware to track user online status"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Update last seen for authenticated users
        if request.user.is_authenticated:
            Profile.objects.filter(user=request.user).update(
                last_seen=timezone.now(),
                is_online=True
            )
        
        response = self.get_response(request)
        return response
    
    def process_view(self, request, view_func, view_args, view_kwargs):
        return None
    
    def process_exception(self, request, exception):
        return None


class NotificationMiddleware:
    """Middleware to add notification count to request"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add unread notification count to request
        if request.user.is_authenticated:
            request.unread_notifications = Notification.objects.filter(
                recipient=request.user,
                is_read=False
            ).count()
        else:
            request.unread_notifications = 0
        
        response = self.get_response(request)
        return response


class ProfileCompletionMiddleware:
    """Middleware to ensure users complete their profile"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip for admin, logout, and certain URLs
        if request.user.is_authenticated:
            # List of paths that don't require profile completion
            exempt_paths = [
                '/admin/',
                '/logout/',
                '/profile/edit/',
                '/profile/update/',
                '/api/',
            ]
            
            path = request.path
            if not any(path.startswith(exempt) for exempt in exempt_paths):
                # Check if profile is complete
                try:
                    profile = request.user.profile
                    # Add your profile completion criteria here
                    # For example:
                    # if not profile.bio or not profile.profile_photo:
                    #     messages.warning(request, "Please complete your profile")
                    #     return redirect('profile-edit')
                except:
                    # Profile doesn't exist - should be created by signal
                    pass
        
        response = self.get_response(request)
        return response


class AJAXMiddleware:
    """Middleware to add AJAX detection to request"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Add is_ajax method to request
        request.is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        response = self.get_response(request)
        return response
