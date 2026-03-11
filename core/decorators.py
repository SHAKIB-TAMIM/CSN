
"""
Custom decorators for the Campus Social Network application
"""

from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseForbidden
from functools import wraps

def ajax_required(view_func):
    """
    Decorator to ensure the request is AJAX
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return view_func(request, *args, **kwargs)
        else:
            return HttpResponseForbidden("This endpoint only accepts AJAX requests")
    return _wrapped_view

def login_required_message(view_func):
    """
    Decorator that adds a message for login required
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, "Please login to access this page")
            return redirect('index')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def staff_required(view_func):
    """
    Decorator to ensure user is staff
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("You need staff privileges to access this page")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def verified_email_required(view_func):
    """
    Decorator to ensure user has verified email
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('index')
        if not request.user.email:
            messages.warning(request, "Please add an email address to continue")
            return redirect('profile-edit')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def ownership_required(model, user_field='user'):
    """
    Decorator to ensure user owns the object
    Usage: @ownership_required(Post)
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Try to get object ID from various possible kwarg names
            obj_id = kwargs.get('pk') or kwargs.get('id') or kwargs.get('post_id')
            
            if not obj_id:
                # Try to find any kwarg that ends with '_id'
                for key, value in kwargs.items():
                    if key.endswith('_id'):
                        obj_id = value
                        break
            
            if not obj_id:
                raise PermissionDenied("Could not determine object ID")
            
            try:
                obj = model.objects.get(pk=obj_id)
                # Check ownership
                obj_user = getattr(obj, user_field)
                if hasattr(obj_user, 'id'):
                    # If user_field is a ForeignKey to User
                    if obj_user.id != request.user.id:
                        raise PermissionDenied("You don't have permission to modify this object")
                else:
                    # If user_field is directly the user ID or username
                    if obj_user != request.user and obj_user != request.user.id:
                        raise PermissionDenied("You don't have permission to modify this object")
                
                return view_func(request, *args, **kwargs)
            except model.DoesNotExist:
                raise PermissionDenied("Object not found")
        return _wrapped_view
    return decorator

def rate_limit(max_requests=60, timeout=60):
    """
    Simple rate limiting decorator
    Note: This is a simplified version. For production, use django-ratelimit
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # This is a placeholder - implement actual rate limiting logic here
            # You might want to use cache for this
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def ajax_login_required(view_func):
    """
    Decorator that combines login_required and ajax_required
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required")
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return HttpResponseForbidden("AJAX request required")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def superuser_required(view_func):
    """
    Decorator to ensure user is superuser
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied("Superuser privileges required")
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def post_ownership_required(view_func):
    """
    Specific decorator for Post ownership
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from .models import Post
        
        post_id = kwargs.get('pk') or kwargs.get('post_id')
        if not post_id:
            raise PermissionDenied("Post ID not provided")
        
        try:
            post = Post.objects.get(pk=post_id)
            if post.user != request.user:
                raise PermissionDenied("You don't own this post")
            return view_func(request, *args, **kwargs)
        except Post.DoesNotExist:
            raise PermissionDenied("Post not found")
    return _wrapped_view

def comment_ownership_required(view_func):
    """
    Specific decorator for Comment ownership
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from .models import Comment
        
        comment_id = kwargs.get('pk') or kwargs.get('comment_id')
        if not comment_id:
            raise PermissionDenied("Comment ID not provided")
        
        try:
            comment = Comment.objects.get(pk=comment_id)
            if comment.user != request.user:
                raise PermissionDenied("You don't own this comment")
            return view_func(request, *args, **kwargs)
        except Comment.DoesNotExist:
            raise PermissionDenied("Comment not found")
    return _wrapped_view