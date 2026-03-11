"""
Modernized views using class-based views, mixins, and services.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView, View
)
from django.views.generic.detail import SingleObjectMixin
from django.urls import reverse, reverse_lazy
from django.http import JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
import json

from .models import (
    User, Profile, Post, Comment, Like, Follow, 
    Notification, Message, Conversation, SavedPost,
    Share, Story, Block
)
from .forms import (
    UserRegistrationForm, UserUpdateForm, ProfileUpdateForm,
    PostForm, CommentForm, MessageForm, StoryForm
)
from .decorators import ajax_required
from .services import NotificationService, FeedService, UserService
from .utils import paginate_queryset


class HomeView(TemplateView):
    """Home page view with login form"""
    template_name = 'core/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            context['feed'] = FeedService.get_feed(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        """Handle login form submission"""
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            # Update online status
            user.profile.is_online = True
            user.profile.last_seen = timezone.now()
            user.profile.save(update_fields=['is_online', 'last_seen'])
            
            next_url = request.GET.get('next', 'welcome')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('index')


class RegisterView(CreateView):
    """User registration view"""
    form_class = UserRegistrationForm
    template_name = 'core/register.html'
    success_url = reverse_lazy('index')

    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.object
        
        # Log the user in
        login(self.request, user)
        
        messages.success(
            self.request, 
            f'Account created successfully! Welcome {user.username}!'
        )
        
        # Send welcome email (async task)
        from .tasks import send_welcome_email
        send_welcome_email.delay(user.id)
        
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors below.')
        return super().form_invalid(form)


class LogoutView(View):
    """Handle logout"""
    def post(self, request):
        if request.user.is_authenticated:
            # Update online status
            request.user.profile.is_online = False
            request.user.profile.last_seen = timezone.now()
            request.user.profile.save(update_fields=['is_online', 'last_seen'])
            
            logout(request)
            messages.success(request, 'You have been logged out successfully.')
        
        return redirect('index')


class FeedView(LoginRequiredMixin, ListView):
    """Main feed showing posts from followed users"""
    model = Post
    template_name = 'core/feed.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        """Get optimized queryset with prefetching"""
        return FeedService.get_feed_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['post_form'] = PostForm()
        context['stories'] = FeedService.get_stories(self.request.user)
        context['suggested_users'] = UserService.get_suggested_users(self.request.user)[:5]
        return context


class ProfileView(LoginRequiredMixin, DetailView):
    """User profile view"""
    model = User
    template_name = 'core/profile.html'
    slug_field = 'username'
    slug_url_kwarg = 'username'
    context_object_name = 'profile_user'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.get_object()
        current_user = self.request.user
        
        # Check if viewing own profile
        context['is_own_profile'] = (user == current_user)
        
        # Get follow status
        context['is_following'] = Follow.objects.filter(
            follower=current_user, following=user
        ).exists()
        
        # Check if blocked
        context['is_blocked'] = Block.objects.filter(
            Q(blocker=current_user, blocked=user) |
            Q(blocker=user, blocked=current_user)
        ).exists()
        
        if context['is_own_profile']:
            context['user_form'] = UserUpdateForm(instance=user)
            context['profile_form'] = ProfileUpdateForm(instance=user.profile)
            context['post_form'] = PostForm()
        
        # Get user's posts with pagination
        posts = user.posts.select_related('user__profile').prefetch_related(
            'comments__user__profile',
            'likes',
            'comments__comment_likes'
        ).all()
        
        context['posts'] = paginate_queryset(
            self.request, posts, per_page=5,
            param_name='posts_page'
        )
        
        # Get followers and following
        context['followers'] = user.followers.select_related('follower__profile')[:10]
        context['following'] = user.following.select_related('following__profile')[:10]
        
        context['comment_form'] = CommentForm()
        
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    """Update user profile"""
    model = User
    form_class = UserUpdateForm
    template_name = 'core/profile_edit.html'

    def get_object(self):
        return self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'profile_form' not in context:
            context['profile_form'] = ProfileUpdateForm(instance=self.request.user.profile)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        user_form = UserUpdateForm(request.POST, instance=request.user)
        profile_form = ProfileUpdateForm(
            request.POST, 
            request.FILES, 
            instance=request.user.profile
        )
        
        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()
            
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile', username=request.user.username)
        
        messages.error(request, 'Please correct the errors below.')
        return self.render_to_response(
            self.get_context_data(
                form=user_form,
                profile_form=profile_form
            )
        )


class PostCreateView(LoginRequiredMixin, CreateView):
    """Create a new post"""
    model = Post
    form_class = PostForm
    template_name = 'core/post_form.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Post created successfully!')
        
        # Notify followers (async)
        from .tasks import notify_followers_new_post
        notify_followers_new_post.delay(form.instance.id)
        
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('profile', args=[self.request.user.username])


class PostDetailView(LoginRequiredMixin, DetailView):
    """Post detail view"""
    model = Post
    template_name = 'core/post_detail.html'
    context_object_name = 'post'

    def get_queryset(self):
        return Post.objects.select_related(
            'user__profile'
        ).prefetch_related(
            'comments__user__profile',
            'comments__replies__user__profile',
            'likes'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['is_liked'] = self.object.likes.filter(user=self.request.user).exists()
        return context


class PostDeleteView(LoginRequiredMixin, DeleteView):
    """Delete a post"""
    model = Post
    template_name = 'core/post_confirm_delete.html'

    def get_queryset(self):
        return Post.objects.filter(user=self.request.user)

    def get_success_url(self):
        messages.success(self.request, 'Post deleted successfully!')
        return reverse('profile', args=[self.request.user.username])


@method_decorator(require_POST, name='dispatch')
class FollowToggleView(LoginRequiredMixin, View):
    """Toggle follow/unfollow"""
    
    def post(self, request, username):
        user_to_follow = get_object_or_404(User, username=username)
        
        if request.user == user_to_follow:
            return JsonResponse({'error': 'You cannot follow yourself'}, status=400)
        
        # Check if blocked
        if Block.objects.filter(
            Q(blocker=request.user, blocked=user_to_follow) |
            Q(blocker=user_to_follow, blocked=request.user)
        ).exists():
            return JsonResponse({'error': 'Cannot follow this user'}, status=400)
        
        follow, created = Follow.objects.get_or_create(
            follower=request.user,
            following=user_to_follow
        )
        
        if created:
            # Create notification
            NotificationService.create_follow_notification(
                actor=request.user,
                recipient=user_to_follow
            )
            status = 'followed'
        else:
            follow.delete()
            status = 'unfollowed'
        
        # Update counts
        request.user.profile.update_counts()
        user_to_follow.profile.update_counts()
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': status,
                'followers_count': user_to_follow.profile.followers_count
            })
        
        return redirect('profile', username=username)


@method_decorator(require_POST, name='dispatch')
class LikeToggleView(LoginRequiredMixin, View):
    """Toggle like/unlike on post"""
    
    def post(self, request, post_id):
        post = get_object_or_404(Post, id=post_id)
        
        like, created = Like.objects.get_or_create(
            user=request.user,
            post=post
        )
        
        if created:
            post.likes_count += 1
            post.save(update_fields=['likes_count'])
            
            # Create notification (if not own post)
            if post.user != request.user:
                NotificationService.create_like_notification(
                    actor=request.user,
                    recipient=post.user,
                    post=post
                )
            status = 'liked'
        else:
            like.delete()
            post.likes_count -= 1
            post.save(update_fields=['likes_count'])
            status = 'unliked'
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'status': status,
                'likes_count': post.likes_count
            })
        
        return redirect('post-detail', post_id=post.id)


class CommentCreateView(LoginRequiredMixin, CreateView):
    """Create a comment on a post"""
    model = Comment
    form_class = CommentForm
    template_name = 'core/comment_form.html'

    def form_valid(self, form):
        post = get_object_or_404(Post, id=self.kwargs.get('post_id'))
        form.instance.user = self.request.user
        form.instance.post = post
        
        # Check if reply
        parent_id = self.request.POST.get('parent_id')
        if parent_id:
            parent = get_object_or_404(Comment, id=parent_id)
            form.instance.parent = parent
        
        messages.success(self.request, 'Comment added successfully!')
        
        # Create notification (if not own post)
        if post.user != self.request.user:
            notification_type = 'reply' if parent_id else 'comment'
            NotificationService.create_comment_notification(
                actor=self.request.user,
                recipient=post.user,
                post=post,
                comment=form.instance,
                notification_type=notification_type
            )
        
        return super().form_valid(form)

    def get_success_url(self):
        if self.request.POST.get('next'):
            return self.request.POST.get('next')
        return reverse('post-detail', args=[self.kwargs.get('post_id')])


class SearchView(LoginRequiredMixin, ListView):
    """Search for users and posts"""
    template_name = 'core/search.html'
    context_object_name = 'results'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        
        if not query:
            return User.objects.none()
        
        # Search users
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(profile__bio__icontains=query) |
            Q(profile__location__icontains=query)
        ).select_related('profile').distinct()
        
        return users

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['query'] = self.request.GET.get('q', '')
        context['users_count'] = self.get_queryset().count()
        
        # Also search posts (limited)
        query = self.request.GET.get('q', '')
        if query:
            context['posts'] = Post.objects.filter(
                Q(content__icontains=query)
            ).select_related('user__profile')[:10]
        
        return context


class NotificationsView(LoginRequiredMixin, ListView):
    """User notifications"""
    model = Notification
    template_name = 'core/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related(
            'actor__profile'
        ).prefetch_related(
            'post', 'comment'
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Mark all as read
        unread = self.get_queryset().filter(is_read=False)
        context['unread_count'] = unread.count()
        return context

    def post(self, request, *args, **kwargs):
        """Mark notifications as read"""
        action = request.POST.get('action')
        
        if action == 'mark_all_read':
            Notification.objects.filter(recipient=request.user, is_read=False).update(
                is_read=True
            )
            messages.success(request, 'All notifications marked as read.')
        
        elif action == 'mark_read':
            notification_id = request.POST.get('notification_id')
            Notification.objects.filter(
                id=notification_id, recipient=request.user
            ).update(is_read=True)
        
        return redirect('notifications')


class ChatView(LoginRequiredMixin, TemplateView):
    """Real-time chat interface"""
    template_name = 'core/chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all conversations for user
        conversations = Conversation.objects.filter(
            participants=self.request.user
        ).prefetch_related(
            'participants__profile'
        ).order_by('-updated_at')
        
        context['conversations'] = conversations
        
        # If specific conversation is requested
        if 'username' in self.kwargs:
            other_user = get_object_or_404(User, username=self.kwargs['username'])
            conversation = Conversation.get_or_create_conversation(
                self.request.user, other_user
            )
            
            # Mark messages as read
            Message.objects.filter(
                conversation=conversation,
                recipient=self.request.user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            
            context['active_conversation'] = conversation
            context['other_user'] = other_user
            context['messages'] = Message.objects.filter(
                conversation=conversation
            ).select_related(
                'sender__profile'
            ).order_by('created_at')[:50]
        
        context['message_form'] = MessageForm()
        
        return context


class ExploreView(LoginRequiredMixin, ListView):
    """Explore trending posts and users"""
    template_name = 'core/explore.html'
    context_object_name = 'posts'
    paginate_by = 12

    def get_queryset(self):
        # Get trending posts (most liked in last 7 days)
        week_ago = timezone.now() - timezone.timedelta(days=7)
        
        return Post.objects.filter(
            created_at__gte=week_ago,
            privacy='public'
        ).select_related(
            'user__profile'
        ).prefetch_related(
            'likes', 'comments'
        ).annotate(
            like_count=Count('likes')
        ).order_by('-like_count', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get suggested users
        context['suggested_users'] = UserService.get_suggested_users(
            self.request.user, limit=10
        )
        
        # Get trending hashtags (if implemented)
        context['trending_tags'] = ['campus', 'student', 'college']
        
        return context


class StoryCreateView(LoginRequiredMixin, CreateView):
    """Create a story"""
    model = Story
    form_class = StoryForm
    template_name = 'core/story_form.html'
    success_url = reverse_lazy('feed')

    def form_valid(self, form):
        form.instance.user = self.request.user
        messages.success(self.request, 'Story created successfully!')
        return super().form_valid(form)


class BlockUserView(LoginRequiredMixin, View):
    """Block a user"""
    
    def post(self, request, username):
        user_to_block = get_object_or_404(User, username=username)
        
        if request.user == user_to_block:
            messages.error(request, 'You cannot block yourself.')
            return redirect('profile', username=username)
        
        # Create block
        block, created = Block.objects.get_or_create(
            blocker=request.user,
            blocked=user_to_block
        )
        
        if created:
            # Remove follow relationship if exists
            Follow.objects.filter(
                Q(follower=request.user, following=user_to_block) |
                Q(follower=user_to_block, following=request.user)
            ).delete()
            
            messages.success(request, f'You have blocked {username}.')
        else:
            messages.info(request, f'You have already blocked {username}.')
        
        return redirect('profile', username=username)


class UnblockUserView(LoginRequiredMixin, View):
    """Unblock a user"""
    
    def post(self, request, username):
        user_to_unblock = get_object_or_404(User, username=username)
        
        Block.objects.filter(
            blocker=request.user,
            blocked=user_to_unblock
        ).delete()
        
        messages.success(request, f'You have unblocked {username}.')
        return redirect('profile', username=username)


# API Views (for AJAX requests)
class APIFeedView(LoginRequiredMixin, View):
    """API endpoint for infinite scroll"""
    
    def get(self, request):
        page = int(request.GET.get('page', 1))
        feed = FeedService.get_feed_queryset(request.user)
        
        paginator = Paginator(feed, 10)
        posts_page = paginator.get_page(page)
        
        data = []
        for post in posts_page:
            data.append({
                'id': post.id,
                'user': {
                    'username': post.user.username,
                    'profile_photo': post.user.profile.profile_photo.url,
                },
                'content': post.content,
                'image': post.image.url if post.image else None,
                'created_at': post.created_at.isoformat(),
                'likes_count': post.likes_count,
                'comments_count': post.comments_count,
                'is_liked': post.likes.filter(user=request.user).exists(),
            })
        
        return JsonResponse({
            'posts': data,
            'has_next': posts_page.has_next(),
            'next_page': page + 1 if posts_page.has_next() else None,
        })


class APINotificationCountView(LoginRequiredMixin, View):
    """Get unread notification count"""
    
    def get(self, request):
        count = Notification.objects.filter(
            recipient=request.user, is_read=False
        ).count()
        
        return JsonResponse({'count': count})


# Error handlers
def handler404(request, exception):
    return render(request, 'core/404.html', status=404)

def handler500(request):
    return render(request, 'core/500.html', status=500)