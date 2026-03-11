"""
Modernized views using class-based views, mixins, and services.
"""

from datetime import timedelta
from urllib import request

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin , UserPassesTestMixin
from django.contrib import messages
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView,
    TemplateView, FormView, View
)
from django.views.decorators.csrf import csrf_protect
from django.contrib.admin.views.decorators import staff_member_required
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_http_methods
from django.views.generic.detail import SingleObjectMixin
from django.urls import reverse, reverse_lazy
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect, HttpResponseForbidden
from django.db.models import Q, Count, Prefetch
from django.core.paginator import Paginator
from django.utils.decorators import method_decorator
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
import json
from django.contrib.admin.models import LogEntry, ADDITION

from .models import (
    User, Profile, Post, Comment, Like, Follow, 
    Notification, Message, Conversation, SavedPost,
    Share, Story, Block, Report
)
from .forms import (
    UniversityRegistrationForm, EmailVerificationForm, CompleteProfileForm,         
    UserUpdateForm, ProfileUpdateForm, PostForm, CommentForm,                 
    MessageForm, StoryForm, ContactForm
)

from .decorators import ajax_required
from .services import NotificationService, FeedService, UserService
from .utils import paginate_queryset, generate_otp, is_otp_valid, send_otp_email
from .models import Announcement, AnnouncementCategory, Department, AnnouncementAuthorPermission, AnnouncementComment, AnnouncementLike, AnnouncementView
from .services import AnnouncementService
from django.views.generic.edit import CreateView
from .models import Story
from .forms import StoryForm
from .models import SiteStatistic, TeamMember, FAQ, ContactMessage
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from allauth.account.views import ConfirmEmailView

def welcome(request):
    """Redirect to the logged-in user's profile"""
    if request.user.is_authenticated:
        return redirect('profile', username=request.user.username)
    else:
        
        return redirect('index')
    

class WelcomeView(TemplateView):
    """Welcome page with dynamic statistics"""
    template_name = 'core/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get statistics for welcome page
        context['statistics'] = SiteStatistic.objects.filter(
            name__in=['active_users', 'daily_posts', 'total_campuses', 'active_community']
        ).order_by('order')
        
        return context


class AboutView(TemplateView):
    """About page with dynamic team and stats"""
    template_name = 'core/about.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all statistics
        context['statistics'] = SiteStatistic.objects.filter(is_active=True).order_by('order')
        
        # Get team members
        context['team_members'] = TeamMember.objects.filter(is_active=True)
        
        # Calculate additional stats
        from django.contrib.auth.models import User
        from core.models import Post
        
        context['total_users'] = User.objects.filter(is_active=True).count()
        context['total_posts'] = Post.objects.count()
        
        # Posts in last 7 days
        week_ago = timezone.now() - timedelta(days=7)
        context['recent_posts'] = Post.objects.filter(created_at__gte=week_ago).count()
        
        return context


class ContactView(LoginRequiredMixin, TemplateView):
    """Contact page with dynamic FAQ - Only logged-in users can contact"""
    template_name = 'core/contact.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get FAQs grouped by category
        faqs = FAQ.objects.filter(is_active=True)
        context['faq_categories'] = {}
        for faq in faqs:
            if faq.category not in context['faq_categories']:
                context['faq_categories'][faq.category] = []
            context['faq_categories'][faq.category].append(faq)
        
        return context

    def post(self, request, *args, **kwargs):
        # Get form data - but use the logged-in user's email
        name = request.user.get_full_name() or request.user.username
        email = request.user.email  # Use logged-in user's email, not from form
        subject = request.POST.get('subject')
        message = request.POST.get('message')
        
        # Validate required fields
        if not all([subject, message]):
            messages.error(request, "Please fill in all required fields.")
            return redirect('contact')
        
        # Validate that user has an email
        if not email:
            messages.error(request, "Your account doesn't have an email address. Please update your profile first.")
            return redirect('profile-edit')
        
        # Save to database
        contact_message = ContactMessage.objects.create(
            name=name,
            email=email,
            subject=subject,
            message=message,
            user=request.user,
            ip_address=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        try:
            # Send email to admin
            self.send_admin_notification(contact_message)
            
            # Send auto-reply to user
            self.send_user_autoreply(contact_message)
            
            messages.success(
                request, 
                f"Thank you {name}! Your message has been sent. We'll get back to you within 24 hours."
            )
        except Exception as e:
            # Log the error but still save the message
            print(f"Email sending failed: {e}")
            messages.warning(
                request,
                "Your message has been received but there was an issue with email notification. Our team will still respond to your query."
            )
        
        return redirect('contact')
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
    def send_admin_notification(self, contact_message):
        """Send email notification to admin"""
        subject = f"New Contact Form Message: {contact_message.subject}"
        
        # HTML email content
        html_content = render_to_string('emails/admin_notification.html', {
            'message': contact_message,
            'site_url': settings.SITE_URL,
        })
        text_content = strip_tags(html_content)
        
        # Send email
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [settings.ADMIN_EMAIL],
            reply_to=[contact_message.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
    
    def send_user_autoreply(self, contact_message):
        """Send auto-reply to user"""
        subject = f"Thank you for contacting Campus Network"
        
        # HTML email content
        html_content = render_to_string('emails/user_autoreply.html', {
            'message': contact_message,
            'site_url': settings.SITE_URL,
        })
        text_content = strip_tags(html_content)
        
        # Send email
        email = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [contact_message.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()


class PrivacyView(TemplateView):
    """Privacy policy page"""
    template_name = 'core/privacy.html'


class TermsView(TemplateView):
    """Terms of service page"""
    template_name = 'core/terms.html'


class HomeView(TemplateView):
    """Home page view with login form"""
    template_name = 'core/index.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Clear messages for anonymous users on login page
        if not self.request.user.is_authenticated:
            storage = messages.get_messages(self.request)
            storage.used = True
            
        if self.request.user.is_authenticated:
            context['feed'] = FeedService.get_feed_queryset(self.request.user)
        return context

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            print(f"✅ Authentication successful for {user.username}")
            
            # 🔴 IMPORTANT: Log the user in FIRST
            login(request, user)
            print(f"✅ Login successful, user: {request.user.username}")
            print(f"Authenticated: {request.user.is_authenticated}")
            
            # Check if profile exists
            try:
                profile = user.profile
            except:
                from core.models import Profile
                profile = Profile.objects.create(user=user)
            
            # Check email verification
            from allauth.account.models import EmailAddress
            email_address = EmailAddress.objects.filter(user=user, verified=True).first()
            
            if not email_address:
                # Send new verification email
                from allauth.account.utils import send_email_confirmation
                send_email_confirmation(request, user)
                
                messages.info(request, "Please verify your email first. We've sent a verification link to your inbox.")
                return redirect('/accounts/confirm-email/')
            
            # Check if profile is complete
            profile_complete = bool(profile.bio and profile.department and profile.batch and profile.student_id)
            
            if not profile_complete:
                request.session['profile_completion_user_id'] = user.id
                messages.warning(request, "Please complete your profile information.")
                return redirect('complete-profile')
            
            # Update online status
            user.profile.is_online = True
            user.profile.last_seen = timezone.now()
            user.profile.save(update_fields=['is_online', 'last_seen'])
            
            # Clear any old messages
            storage = messages.get_messages(request)
            storage.used = True
            
            messages.success(request, f"Welcome back, {user.username}!")
            next_url = request.GET.get('next', 'feed')
            return redirect(next_url)
        else:
            messages.error(request, 'Invalid username or password')
            return redirect('index')


class CustomConfirmEmailView(ConfirmEmailView):
    """Custom email confirmation view that redirects to complete-profile after verification"""
    
    def get(self, *args, **kwargs):
        try:
            self.object = self.get_object()
            
            # Check if already verified
            if self.object.email_address.verified:
                messages.info(self.request, "Your email has already been verified. Please login.")
                return redirect('index')
            
            # Confirm the email
            self.object.confirm(self.request)
            
            # Get the user
            user = self.object.email_address.user
            
            # Auto-login the user
            from django.contrib.auth import login
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Update online status
            user.profile.is_online = True
            user.profile.last_seen = timezone.now()
            user.profile.save(update_fields=['is_online', 'last_seen'])
            
            messages.success(self.request, f"Email verified successfully! Welcome {user.username}!")
            
            # Check if profile is complete
            if not user.profile.bio or not user.profile.department or not user.profile.batch:
                messages.info(self.request, "Please complete your profile information to continue.")
                return redirect('complete-profile')
            
            return redirect('feed')
            
        except Exception as e:
            messages.error(self.request, f"Email verification failed: {str(e)}")
            return redirect('index')


class RegisterView(FormView):
    """Step 1: Registration with university email"""
    template_name = 'core/register.html'
    form_class = UniversityRegistrationForm
    success_url = reverse_lazy('verify-email')

    def form_valid(self, form):
        # Save user (inactive)
        user = form.save(commit=False)
        user.is_active = False  # Deactivate until email verification
        user.save()
        
        # Generate and save OTP
        otp = generate_otp()
        user.profile.email_verification_otp = otp
        user.profile.email_verification_sent_at = timezone.now()
        user.profile.save()
        
        # Send OTP email
        try:
            send_otp_email(user, otp)
            messages.success(
                self.request,
                f"Registration successful! An OTP has been sent to {user.email}. Please verify within 10 minutes."
            )
        except Exception as e:
            messages.warning(
                self.request,
                "Account created but OTP email could not be sent. Please request a new OTP."
            )
        
        # Store user ID in session for verification
        self.request.session['verification_user_id'] = user.id
        
        return super().form_valid(form)


class CustomConfirmEmailView(ConfirmEmailView):
    """Custom email confirmation view that redirects to feed after verification"""
    
    def get(self, *args, **kwargs):
        try:
            self.object = self.get_object()
            if self.object.email_address.verified:
                messages.success(self.request, "Your email has already been verified. Please login.")
                return redirect('index')
            
            # Confirm the email
            self.object.confirm(self.request)
            
            # Get the user
            user = self.object.email_address.user
            
            # Auto-login the user
            from django.contrib.auth import login
            login(self.request, user, backend='django.contrib.auth.backends.ModelBackend')
            
            # Update online status
            user.profile.is_online = True
            user.profile.last_seen = timezone.now()
            user.profile.save(update_fields=['is_online', 'last_seen'])
            
            messages.success(self.request, f"Email verified successfully! Welcome {user.username}!")
            
            # Check if profile is complete
            if not user.profile.bio or not user.profile.department:
                messages.info(self.request, "Please complete your profile information.")
                return redirect('profile-edit')
            
            return redirect('feed')
            
        except Exception as e:
            messages.error(self.request, "Email verification failed. Please try again.")
            return redirect('index')
        

class VerifyEmailView(TemplateView):
    """Step 2: Verify email with OTP"""
    template_name = 'core/verify_email.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = EmailVerificationForm()
        return context

    def post(self, request, *args, **kwargs):
        form = EmailVerificationForm(request.POST)
        
        if form.is_valid():
            otp = form.cleaned_data['otp']
            user_id = request.session.get('verification_user_id')
            
            if not user_id:
                messages.error(request, "Session expired. Please register again.")
                return redirect('register')
            
            try:
                user = User.objects.get(id=user_id)
                profile = user.profile
                
                # Check if OTP matches and is valid
                if profile.email_verification_otp == otp and is_otp_valid(profile.email_verification_sent_at):
                    # Mark email as verified
                    profile.email_verified = True
                    profile.email_verification_otp = None
                    profile.save()
                    
                    # Activate user
                    user.is_active = True
                    user.save()
                    
                    messages.success(request, "Email verified successfully! Now complete your profile.")
                    request.session['profile_completion_user_id'] = user.id
                    return redirect('complete-profile')
                else:
                    messages.error(request, "Invalid or expired OTP. Please try again.")
            except User.DoesNotExist:
                messages.error(request, "User not found. Please register again.")
                return redirect('register')
        
        return self.render_to_response(self.get_context_data(form=form))

def verify_email_redirect(request):
    messages.info(request, 'Email verification is not required. You are already logged in.')
    return redirect('feed')

def email_verification_sent(request):
    """Custom email verification sent page"""
    return render(request, 'core/email_verification_sent.html')

class ResendOTPView(View):
    """Resend OTP to user"""
    
    def post(self, request):
        user_id = request.session.get('verification_user_id')
        
        if not user_id:
            messages.error(request, "Session expired. Please register again.")
            return redirect('register')
        
        try:
            user = User.objects.get(id=user_id)
            
            # Generate new OTP
            otp = generate_otp()
            user.profile.email_verification_otp = otp
            user.profile.email_verification_sent_at = timezone.now()
            user.profile.save()
            
            # Send new OTP
            send_otp_email(user, otp)
            
            messages.success(request, "New OTP has been sent to your email.")
        except User.DoesNotExist:
            messages.error(request, "User not found.")
            return redirect('register')
        
        return redirect('verify-email')


class CompleteProfileView(LoginRequiredMixin, FormView):
    """Step 3: Complete profile with university details"""
    template_name = 'core/complete_profile.html'
    form_class = CompleteProfileForm
    success_url = reverse_lazy('feed')

    def dispatch(self, request, *args, **kwargs):
        print("=" * 60)
        print("DISPATCH CALLED")
        print("=" * 60)
        print(f"User: {request.user}")
        print(f"Authenticated: {request.user.is_authenticated}")
        print(f"Session: {request.session.items()}")
        
        # First check if user is authenticated
        if not request.user.is_authenticated:
            print("❌ User not authenticated - redirecting to login")
            return self.handle_no_permission()
        
        print("✅ User is authenticated")
        
        try:
            profile = request.user.profile
            print(f"Profile exists: Yes")
            print(f"Profile completed: {profile.profile_completed}")
            print(f"Bio: {profile.bio}")
            print(f"Department: {profile.department}")
            print(f"Batch: {profile.batch}")
            print(f"Student ID: {profile.student_id}")
            
            # Check if profile is already complete
            if profile.profile_completed:
                print("✅ Profile already complete - redirecting to feed")
                return redirect('feed')
            
            # Check if they have all required fields
            if profile.bio and profile.department and profile.batch and profile.student_id:
                print("✅ All fields present but flag false - fixing and redirecting")
                profile.profile_completed = True
                profile.save(update_fields=['profile_completed'])
                return redirect('feed')
            
            print("❌ Profile incomplete - showing form")
            
        except Exception as e:
            print(f"❌ Error accessing profile: {e}")
        
        return super().dispatch(request, *args, **kwargs)
    
    def get_context_data(self, **kwargs):
        """Add departments to the template context"""
        context = super().get_context_data(**kwargs)
        
        # Import Department model
        from .models import Department
        
        # Get all active departments ordered by name
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        
        # Debug print to check if departments are found
        print(f"✅ Found {context['departments'].count()} departments")
        for dept in context['departments']:
            print(f"   - {dept.name} ({dept.code})")
        
        return context

    def form_valid(self, form):
        """Process the valid form"""
        user = self.request.user
        
        # Update profile with form data
        profile = user.profile
        profile.bio = form.cleaned_data['bio']
        profile.department = form.cleaned_data['department']
        profile.batch = form.cleaned_data['batch']
        profile.student_id = form.cleaned_data['student_id']
        profile.location = form.cleaned_data.get('location', '')
        profile.profile_completed = True
        profile.save()
        
        # Ensure user is active
        if not user.is_active:
            user.is_active = True
            user.save()
        
        messages.success(self.request, 'Profile completed successfully! Welcome to Campus Network!')
        
        return super().form_valid(form)

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


class FeedView(LoginRequiredMixin, TemplateView):
    """Main feed showing posts from followed users"""
    template_name = 'core/feed.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['post_form'] = PostForm()
        
        # Get user's own active story (if any)
        from .models import Story
        from django.utils import timezone
        
        user_story = Story.objects.filter(
            user=self.request.user,
            expires_at__gt=timezone.now()
        ).first()
        context['user_story'] = user_story
        
        # Get stories from followed users
        context['stories'] = FeedService.get_stories(self.request.user)
        
        # Get all stories (including user's own) for display in the template
        following = self.request.user.following.values_list('following', flat=True)
        all_stories = Story.objects.filter(
            user_id__in=list(following) + [self.request.user.id],
            expires_at__gt=timezone.now()
        ).select_related('user__profile').order_by('-created_at')
        context['all_stories'] = all_stories
        
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

        user_story = Story.objects.filter(
            user=user,
            expires_at__gt=timezone.now()
        ).first()
        context['user_story'] = user_story
        
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
        
        # Always add profile_form if not present
        if 'profile_form' not in context:
            context['profile_form'] = ProfileUpdateForm(instance=self.request.user.profile)
        context['departments'] = Department.objects.filter(is_active=True).order_by('name')
        
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
        
        # Create context with both forms and departments
        context = self.get_context_data(
            form=user_form,
            profile_form=profile_form,
            departments=Department.objects.filter(is_active=True).order_by('name')
        )
        return self.render_to_response(context)


# Update the PostCreateView in core/views.py

class PostCreateView(LoginRequiredMixin, CreateView):
    """Create a new post with support for images, videos, and documents"""
    model = Post
    form_class = PostForm
    template_name = 'core/post_form.html'

    def form_valid(self, form):
        form.instance.user = self.request.user
        
        # Handle file uploads
        if 'image' in self.request.FILES:
            form.instance.image = self.request.FILES['image']
        elif 'video' in self.request.FILES:
            form.instance.video = self.request.FILES['video']
        elif 'document' in self.request.FILES:
            form.instance.document = self.request.FILES['document']
        
        # Save the post
        response = super().form_valid(form)
        
        # Update user's post count
        self.request.user.profile.posts_count = self.request.user.posts.count()
        self.request.user.profile.save(update_fields=['posts_count'])
        
        messages.success(self.request, 'Post created successfully!')
        
        # Check if it's an HTMX request (for infinite scroll/feed)
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'core/includes/post.html', {'post': self.object})
        
        return response

    def form_invalid(self, form):
        messages.error(self.request, 'Error creating post. Please check your input.')
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'core/includes/post_form_errors.html', {'form': form})
        return redirect(self.request.META.get('HTTP_REFERER', 'feed'))

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


class PostDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a post (only by author or admin)"""
    model = Post
    template_name = 'core/post_confirm_delete.html'
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.user or self.request.user.is_staff
    
    def get_success_url(self):
        messages.success(self.request, 'Post deleted successfully!')
        return reverse('profile', args=[self.request.user.username])
    
    def delete(self, request, *args, **kwargs):
        post = self.get_object()
        response = super().delete(request, *args, **kwargs)
        if request.headers.get('HX-Request'):
            return HttpResponse(status=200, headers={'HX-Refresh': 'true'})
        return response


class PostUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update a post (only by author or admin)"""
    model = Post
    template_name = 'core/post_form.html'
    fields = ['content', 'image', 'video', 'privacy']
    
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.user or self.request.user.is_staff
    
    def form_valid(self, form):
        form.instance.is_edited = True
        messages.success(self.request, 'Post updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('profile', args=[self.request.user.username])


class SavedPostsView(LoginRequiredMixin, ListView):
    """Display user's saved posts"""
    model = SavedPost
    template_name = 'core/saved_posts.html'
    context_object_name = 'saved_posts'
    paginate_by = 10

    def get_queryset(self):
        return SavedPost.objects.filter(
            user=self.request.user
        ).select_related(
            'post__user__profile'
        ).order_by('-created_at')
    

@require_POST
@login_required
def unsave_post(request, pk):
    """Remove a post from saved posts"""
    try:
        saved_post = SavedPost.objects.get(user=request.user, post_id=pk)
        saved_post.delete()
        return JsonResponse({'success': True})
    except SavedPost.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Post not found in saved items'})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


        
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


class ReportUserView(LoginRequiredMixin, View):
    """Report a user – sends notification to all admins"""
    
    def post(self, request, username):
        from django.contrib.auth import get_user_model
        from .models import Notification, Report
        from django.db.models import Q
        User = get_user_model()
        
        try:
            reported_user = User.objects.get(username=username)
        except User.DoesNotExist:
            return HttpResponse('<div class="p-3 bg-red-100 text-red-800 rounded-lg">User not found.</div>')
        
        if request.user == reported_user:
            return HttpResponse('<div class="p-3 bg-red-100 text-red-800 rounded-lg">You cannot report yourself.</div>')

        reason = request.POST.get('reason', 'other')
        description = request.POST.get('description', '')

        # Create the report
        report = Report.objects.create(
            reporter=request.user,
            reported_user=reported_user,
            report_type='user',
            reason=reason,
            description=description
        )

        # Get admin users
        admin_users = User.objects.filter(Q(is_superuser=True) | Q(is_staff=True))
        
        # Send notifications
        for admin in admin_users:
            Notification.objects.create(
                recipient=admin,
                actor=request.user,
                notification_type='report',
                text=f'User {request.user.username} reported user {reported_user.username} for: {reason}',
                url=f'/admin/core/report/{report.id}/change/'
            )

        # Return success message
        return HttpResponse('''
            <div class="p-3 bg-green-100 text-green-800 rounded-lg">
                <i class="fas fa-check-circle mr-2"></i>
                Report submitted successfully. Admin has been notified.
            </div>
        ''')
    

def report_post(request):
    if request.method == 'POST' and request.user.is_authenticated:
        import json
        data = json.loads(request.body)
        post_id = data.get('post_id')
        reason = data.get('reason')
        description = data.get('description', '')
        
        # Create notification for admin
        from .models import Notification
        from django.contrib.auth.models import User
        
        admins = User.objects.filter(is_staff=True)
        for admin in admins:
            Notification.objects.create(
                recipient=admin,
                actor=request.user,
                notification_type='report',
                text=f'Post #{post_id} reported for: {reason}',
                url=f'/admin/core/post/{post_id}/change/'
            )
        
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


class DeleteAccountView(LoginRequiredMixin, View):
    """View for deleting user account and all associated data"""
    
    def post(self, request):
        password = request.POST.get('password')
        user = request.user
        
        # Verify password
        if not authenticate(username=user.username, password=password):
            messages.error(request, "Invalid password. Account not deleted.")
            return redirect('profile-edit')
        
        # Store username for message
        username = user.username
        user_id = user.id
        
        try:
            # Log the deletion attempt
            print(f"Starting deletion process for user: {username} (ID: {user_id})")
            
            # Delete all user's notifications (as recipient or actor)
            Notification.objects.filter(recipient=user).delete()
            Notification.objects.filter(actor=user).delete()
            
            # Delete all user's messages and conversations
            # Get all conversations involving this user
            conversations = Conversation.objects.filter(participants=user)
            for conv in conversations:
                # Delete messages in this conversation
                Message.objects.filter(conversation=conv).delete()
            # Delete the conversations
            conversations.delete()
            
            # Delete all user's messages (as sender or recipient)
            Message.objects.filter(sender=user).delete()
            Message.objects.filter(recipient=user).delete()
            
            # Delete all user's posts, likes, comments
            Post.objects.filter(user=user).delete()
            Like.objects.filter(user=user).delete()
            Comment.objects.filter(user=user).delete()
            
            # Delete all user's stories
            Story.objects.filter(user=user).delete()
            
            # Delete all user's follows (as follower or following)
            Follow.objects.filter(follower=user).delete()
            Follow.objects.filter(following=user).delete()
            
            # Delete all user's saved posts
            SavedPost.objects.filter(user=user).delete()
            
            # Delete all user's blocks
            Block.objects.filter(blocker=user).delete()
            Block.objects.filter(blocked=user).delete()
            
            # Delete all user's reports
            Report.objects.filter(reporter=user).delete()
            Report.objects.filter(reported_user=user).delete()
            
            # Delete all user's announcement-related data
            
            # Delete announcements created by user
            Announcement.objects.filter(author=user).delete()
            
            # Delete user's announcement comments
            AnnouncementComment.objects.filter(user=user).delete()
            
            # Delete user's announcement likes
            AnnouncementLike.objects.filter(user=user).delete()
            
            # Delete user's announcement views
            AnnouncementView.objects.filter(user=user).delete()
            
            # Delete user's announcement permissions
            AnnouncementAuthorPermission.objects.filter(user=user).delete()
            
            # Delete user's profile
            if hasattr(user, 'profile'):
                user.profile.delete()
            
            # Finally, delete the user
            user.delete()
            
            # Logout the user
            logout(request)
            
            messages.success(request, f"Account '{username}' and all associated data has been permanently deleted.")
            print(f"Successfully deleted user: {username} and all associated data")
            
        except Exception as e:
            print(f"Error deleting account: {str(e)}")
            messages.error(request, f"Error deleting account: {str(e)}")
            return redirect('profile-edit')
        
        return redirect('index')


class DeleteAccountConfirmView(LoginRequiredMixin, TemplateView):
    """Confirmation page before deleting account"""
    template_name = 'core/delete_account_confirm.html'
    
               
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
            # Don't manually update count here - let the signal handle it
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
            # Don't manually update count here - let the signal handle it
            status = 'unliked'
        
        # Get updated post with correct count
        post.refresh_from_db()
        
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
        
        # Save the comment FIRST
        self.object = form.save()
        
        messages.success(self.request, 'Comment added successfully!')
        
        # Create notification AFTER comment is saved
        if post.user != self.request.user:
            NotificationService.create_comment_notification(
                actor=self.request.user,
                recipient=post.user,
                post=post,
                comment=self.object  # Now this exists
            )
        
        # Check if it's an HTMX request
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'core/includes/comment.html', {'comment': self.object})
        
        return redirect('post-detail', pk=post.id)

    def form_invalid(self, form):
        messages.error(self.request, 'Error adding comment. Please try again.')
        return redirect('post-detail', pk=self.kwargs.get('post_id'))


class CommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Comment
    template_name = 'core/comment_form.html'
    fields = ['content']
    pk_url_kwarg = 'pk'
    
    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.user or self.request.user.is_staff
    
    def form_valid(self, form):
        form.instance.is_edited = True
        messages.success(self.request, 'Comment updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('post-detail', args=[self.object.post.id])


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Comment
    template_name = 'core/comment_confirm_delete.html'
    pk_url_kwarg = 'pk'
    
    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.user or self.request.user.is_staff
    
    def get_success_url(self):
        messages.success(self.request, 'Comment deleted successfully!')
        return reverse('post-detail', args=[self.object.post.id])
    

class SearchView(LoginRequiredMixin, ListView):
    """Search for users and posts"""
    template_name = 'core/search.html'
    context_object_name = 'results'
    paginate_by = 20

    def get_queryset(self):
        query = self.request.GET.get('q', '').strip()
        
        if not query:
            return User.objects.none()
        
        # Search users (case-insensitive)
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(profile__bio__icontains=query)
        ).exclude(
            is_staff=True
        ).exclude(
            is_superuser=True
        ).select_related('profile').distinct()
        
        return users

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        query = self.request.GET.get('q', '')
        context['query'] = query
        context['users_count'] = self.get_queryset().count()
        
        # Also search posts (if you want)
        if query:
            from core.models import Post
            context['posts'] = Post.objects.filter(
                Q(content__icontains=query)
            ).select_related('user__profile')[:10]
        
        return context


class NotificationsView(LoginRequiredMixin, ListView):
    """User notifications view"""
    model = Notification
    template_name = 'core/notifications.html'
    context_object_name = 'notifications'
    paginate_by = 20

    def get_queryset(self):
        return Notification.objects.filter(
            recipient=self.request.user
        ).select_related(
            'actor__profile'
        ).order_by('-created_at')

    def post(self, request, *args, **kwargs):
        action = request.POST.get('action')
        
        if action == 'mark_all_read':
            Notification.objects.filter(
                recipient=request.user, 
                is_read=False
            ).update(is_read=True)
            messages.success(request, 'All notifications marked as read.')
            
        elif action == 'mark_read':
            notification_id = request.POST.get('notification_id')
            Notification.objects.filter(
                id=notification_id, 
                recipient=request.user
            ).update(is_read=True)
            
        return redirect('notifications')


class ChatView(LoginRequiredMixin, TemplateView):
    """Real-time chat interface"""
    template_name = 'core/chat.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get all conversations for user - based on messages
        from django.db.models import Q, Max
        
        # Get unique users that the current user has chatted with
        sent_messages_users = Message.objects.filter(
            sender=self.request.user
        ).values_list('recipient', flat=True).distinct()
        
        received_messages_users = Message.objects.filter(
            recipient=self.request.user
        ).values_list('sender', flat=True).distinct()
        
        # Combine and get unique user IDs
        chat_partner_ids = set(list(sent_messages_users) + list(received_messages_users))
        
        # Get the user objects for chat partners
        from django.contrib.auth.models import User
        chat_partners = User.objects.filter(id__in=chat_partner_ids)
        
        # Build conversation list with last message
        conversations = []
        for partner in chat_partners:
            last_message = Message.objects.filter(
                Q(sender=self.request.user, recipient=partner) |
                Q(sender=partner, recipient=self.request.user)
            ).order_by('-created_at').first()
            
            unread_count = Message.objects.filter(
                sender=partner,
                recipient=self.request.user,
                is_read=False
            ).count()
            
            conversations.append({
                'user': partner,
                'last_message': last_message,
                'unread_count': unread_count,
            })
        
        # Sort by last message time
        conversations.sort(key=lambda x: x['last_message'].created_at if x['last_message'] else timezone.datetime.min, reverse=True)
        
        context['conversations'] = conversations
        
        # If specific conversation is requested
        if 'username' in self.kwargs:
            other_user = get_object_or_404(User, username=self.kwargs['username'])
            
            # Get messages between the two users
            messages_qs = Message.objects.filter(
                Q(sender=self.request.user, recipient=other_user) |
                Q(sender=other_user, recipient=self.request.user)
            ).select_related(
                'sender__profile'
            ).order_by('created_at')
            
            # Mark messages as read
            messages_qs.filter(
                sender=other_user,
                recipient=self.request.user,
                is_read=False
            ).update(is_read=True, read_at=timezone.now())
            
            context['active_conversation'] = {
                'user': other_user,
                'messages': messages_qs[:50]
            }
            context['other_user'] = other_user
            context['messages'] = messages_qs[:50]
            
            # Create messages_json for the template
            import json
            from django.core.serializers.json import DjangoJSONEncoder
            
            messages_list = []
            for msg in messages_qs[:50]:
                messages_list.append({
                    'id': msg.id,
                    'content': msg.content,
                    'sender': msg.sender.username,
                    'sender_id': msg.sender.id,
                    'created_at': msg.created_at.isoformat(),
                    'is_read': msg.is_read,
                })
            
            context['messages_json'] = json.dumps(messages_list, cls=DjangoJSONEncoder)
        
        context['message_form'] = MessageForm()
        
        return context


class ExploreView(LoginRequiredMixin, ListView):
    """Explore trending posts and users"""
    template_name = 'core/explore.html'
    context_object_name = 'posts'
    paginate_by = 10

    def get_queryset(self):
        # Get trending posts (most liked in last 7 days)
        week_ago = timezone.now() - timezone.timedelta(days=7)
        
        return Post.objects.filter(
            created_at__gte=week_ago,
            privacy='public'
        ).select_related(
            'user__profile'
        ).prefetch_related(
            'likes', 
            'comments__user__profile'
        ).annotate(
            like_count=Count('likes')
        ).order_by('-like_count', '-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get suggested users
        context['suggested_users'] = UserService.get_suggested_users(
            self.request.user, limit=10
        )
        from .services import AnnouncementService
        context['can_create'] = AnnouncementService.can_create_announcement(self.request.user)
        return context


class StoryCreateView(LoginRequiredMixin, CreateView):
    """Create a new story"""
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


# ==================== ANNOUNCEMENT VIEWS ====================

class AnnouncementDetailView(LoginRequiredMixin, DetailView):
    """View a single announcement"""
    model = Announcement
    template_name = 'core/announcement_detail.html'
    context_object_name = 'announcement'
    slug_url_kwarg = 'slug'

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Track view
        if self.request.user.is_authenticated:
            from .models import AnnouncementView
            view, created = AnnouncementView.objects.get_or_create(
                user=self.request.user,
                announcement=obj,
                defaults={'ip_address': self.get_client_ip()}
            )
            if created:
                obj.views_count += 1
                obj.save(update_fields=['views_count'])
        
        return obj
    
    def get_client_ip(self):
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip

    def get_context_data(self, **kwargs):
        # Call the base implementation first to get the context
        context = super().get_context_data(**kwargs)
        
        # Add any additional context variables here
        context['now'] = timezone.now()
        
        # Debug info (you can remove this later)
        print(f"Current user: {self.request.user.username}")
        print(f"Comments: {self.object.comments.count()}")
        for comment in self.object.comments.all():
            print(f"Comment {comment.id} by {comment.user.username}")
        
        return context


class AnnouncementLikeToggleView(LoginRequiredMixin, View):
    """Toggle like on announcement"""
    
    def post(self, request, pk):
        from .models import Announcement, AnnouncementLike
        announcement = get_object_or_404(Announcement, pk=pk)
        
        like, created = AnnouncementLike.objects.get_or_create(
            user=request.user,
            announcement=announcement
        )
        
        if created:
            announcement.likes_count += 1
            announcement.save(update_fields=['likes_count'])
            status = 'liked'
        else:
            like.delete()
            announcement.likes_count -= 1
            announcement.save(update_fields=['likes_count'])
            status = 'unliked'
        
        return JsonResponse({
            'status': status,
            'likes_count': announcement.likes_count
        })


class AnnouncementCommentView(LoginRequiredMixin, CreateView):
    """Add comment to announcement"""
    model = AnnouncementComment
    fields = ['content']
    template_name = 'core/announcement_comment_form.html'
    
    def form_valid(self, form):
        from .models import Announcement
        announcement = get_object_or_404(Announcement, pk=self.kwargs['pk'])
        form.instance.user = self.request.user
        form.instance.announcement = announcement
        
        response = super().form_valid(form)
        
        # Update comment count
        announcement.comments_count = announcement.comments.count()
        announcement.save(update_fields=['comments_count'])
        
        if self.request.headers.get('HX-Request'):
            return render(self.request, 'core/includes/comment.html', {'comment': self.object})
        
        return redirect('announcement-detail', slug=announcement.slug)
    
    def get_success_url(self):
        return reverse('announcement-detail', args=[self.object.announcement.slug])


class AnnouncementCommentUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update a comment (only by author or admin)"""
    model = AnnouncementComment
    template_name = 'core/comment_form.html'
    fields = ['content']
    pk_url_kwarg = 'pk'
    
    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.user or self.request.user.is_staff
    
    def form_valid(self, form):
        form.instance.is_edited = True
        messages.success(self.request, 'Comment updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('announcement-detail', args=[self.object.announcement.slug])
    

class AnnouncementCommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete a comment (only by author or admin)"""
    model = AnnouncementComment
    template_name = 'core/comment_confirm_delete.html'
    pk_url_kwarg = 'pk'
    
    def test_func(self):
        comment = self.get_object()
        return self.request.user == comment.user or self.request.user.is_staff
    
    def get_success_url(self):
        messages.success(self.request, 'Comment deleted successfully!')
        return reverse('announcement-detail', args=[self.object.announcement.slug])
    
    def delete(self, request, *args, **kwargs):
        comment = self.get_object()
        announcement = comment.announcement
        response = super().delete(request, *args, **kwargs)
        
        # Update comment count
        announcement.comments_count = announcement.comments.count()
        announcement.save(update_fields=['comments_count'])
        
        if request.headers.get('HX-Request'):
            return HttpResponse(status=200, headers={'HX-Trigger': 'commentDeleted'})
        
        return response


class AnnouncementUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Update announcement (only for author or admin)"""
    model = Announcement
    template_name = 'core/announcement_form.html'
    fields = [
        'title', 'announcement_type', 'category', 'content', 'summary',
        'featured_image', 'attachment', 'external_link',
        'audience', 'target_department', 'target_batch',
        'event_start_date', 'event_end_date', 'deadline',
        'location', 'is_virtual', 'meeting_link',
        'is_pinned', 'is_important'
    ]
    pk_url_kwarg = 'pk'
    
    def test_func(self):
        announcement = self.get_object()
        return (self.request.user.is_staff or 
                announcement.author == self.request.user or
                AnnouncementService.can_create_announcement(self.request.user))
    
    def form_valid(self, form):
        messages.success(self.request, 'Announcement updated successfully!')
        return super().form_valid(form)
    
    def get_success_url(self):
        return reverse('announcement-detail', args=[self.object.slug])


class AnnouncementDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """Delete announcement (only for author or admin)"""
    model = Announcement
    template_name = 'core/announcement_confirm_delete.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('explore')
    
    def test_func(self):
        announcement = self.get_object()
        return self.request.user.is_staff or announcement.author == self.request.user
    
    def delete(self, request, *args, **kwargs):
        messages.success(self.request, 'Announcement deleted successfully!')
        return super().delete(request, *args, **kwargs)


class AnnouncementCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    """Create announcement (only for authorized users)"""
    model = Announcement
    template_name = 'core/announcement_form.html'
    fields = [
        'title', 'announcement_type', 'category', 'content', 'summary',
        'featured_image', 'attachment', 'external_link',
        'audience', 'target_department', 'target_batch',
        'event_start_date', 'event_end_date', 'deadline',
        'location', 'is_virtual', 'meeting_link',
        'is_pinned', 'is_important'
    ]
    
    def test_func(self):
        return AnnouncementService.can_create_announcement(self.request.user)
    
    def form_valid(self, form):
        form.instance.author = self.request.user
        if form.instance.audience == 'department' and not form.instance.target_department:
            form.instance.audience = 'general'
        response = super().form_valid(form)
        messages.success(self.request, 'Announcement created successfully!')
        return response
    
    def get_success_url(self):
        return reverse('announcement-detail', args=[self.object.slug])


@method_decorator(staff_member_required, name='dispatch')
class AdminAnnouncementPermissionsView(TemplateView):
    """Admin panel for managing announcement permissions"""
    template_name = 'core/admin/permissions.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from .models import AnnouncementAuthorPermission, Department
        context['users'] = User.objects.filter(is_active=True).exclude(is_superuser=True)
        context['departments'] = Department.objects.filter(is_active=True)
        context['permissions'] = AnnouncementAuthorPermission.objects.select_related('user', 'granted_by').all()
        return context
    
    def post(self, request):
        from .models import AnnouncementAuthorPermission, Department
        user_id = request.POST.get('user_id')
        user = get_object_or_404(User, id=user_id)
        
        permission, created = AnnouncementAuthorPermission.objects.get_or_create(user=user)
        
        permission.can_create_general = request.POST.get('can_create_general') == 'on'
        permission.can_create_departmental = request.POST.get('can_create_departmental') == 'on'
        permission.can_create_events = request.POST.get('can_create_events') == 'on'
        permission.can_create_notices = request.POST.get('can_create_notices') == 'on'
        permission.can_create_news = request.POST.get('can_create_news') == 'on'
        permission.granted_by = request.user
        
        # Handle departments
        permission.departments.clear()
        dept_ids = request.POST.getlist('departments')
        if dept_ids:
            permission.departments.add(*dept_ids)
        
        permission.save()
        
        messages.success(request, f'Permissions updated for {user.username}')
        return redirect('admin-announcement-permissions')


# Error handlers
def handler404(request, exception):
    return render(request, 'core/404.html', status=404)

def handler500(request):
    return render(request, 'core/500.html', status=500)