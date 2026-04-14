"""
API Views for Core app
"""
import os
import json
from django.http import JsonResponse
from django.views import View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator, EmptyPage
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.db.models import Prefetch

# Import services and models
from core.services import FeedService
from core.models import Notification, Message, Profile, Follow, SavedPost, Comment,Post




class APIFeedView(LoginRequiredMixin, View):
    def get(self, request):
        try:
            page = int(request.GET.get('page', 1))

            # Get saved post IDs for current user
            from core.models import SavedPost
            saved_post_ids = set(
                SavedPost.objects.filter(
                    user=request.user
                ).values_list('post_id', flat=True)
            )

            # Get feed posts - simplified without complex prefetch
            feed = FeedService.get_feed_queryset(request.user)

            paginator = Paginator(feed, 10)

            try:
                posts_page = paginator.page(page)
            except EmptyPage:
                return JsonResponse({'posts': [], 'has_next': False})

            data = []
            for post in posts_page:
                profile_photo_url = '/static/default.jpg'
                if post.user.profile.profile_photo:
                    profile_photo_url = post.user.profile.profile_photo.url

                post_data = {
                    'id': post.id,
                    'user': {
                        'username': post.user.username,
                        'profile_photo': profile_photo_url,
                    },
                    'content': post.content or '',
                    'created_at': post.created_at.isoformat(),
                    'likes_count': post.likes_count,
                    'comments_count': post.comments_count,
                    'is_liked': post.likes.filter(user=request.user).exists(),
                    'is_saved': post.id in saved_post_ids,
                    'privacy': post.privacy,
                    'is_edited': post.is_edited,
                }

                if post.image:
                    post_data['image'] = post.image.url

                if post.video:
                    post_data['video'] = post.video.url

                if post.document:
                    post_data['document'] = post.document.url
                    post_data['document_name'] = os.path.basename(post.document.name)
                    try:
                        post_data['document_size'] = post.document.size
                    except:
                        post_data['document_size'] = 0

                data.append(post_data)

            return JsonResponse({
                'posts': data,
                'has_next': posts_page.has_next(),
            })

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'error': str(e), 'posts': []}, status=500)
class APINotificationCountView(LoginRequiredMixin, View):
    """Get unread notification count"""

    def get(self, request):
        try:
            count = Notification.objects.filter(
                recipient=request.user, is_read=False
            ).count()

            return JsonResponse({'count': count})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


class APIMarkMessagesRead(LoginRequiredMixin, View):
    """Mark messages as read"""

    def post(self, request):
        try:
            data = json.loads(request.body)
            conversation_id = data.get('conversation_id')

            if conversation_id:
                updated = Message.objects.filter(
                    conversation_id=conversation_id,
                    recipient=request.user,
                    is_read=False
                ).update(is_read=True, read_at=timezone.now())

                return JsonResponse({
                    'success': True,
                    'marked_count': updated
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'No conversation_id provided'
                })
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class APIUploadChatFile(LoginRequiredMixin, View):
    def post(self, request):
        try:
            file = request.FILES.get('file')
            if not file:
                return JsonResponse({'success': False, 'error': 'No file provided'})

            # Determine if image or file
            is_image = file.content_type.startswith('image/')

            # Save to appropriate folder
            if is_image:
                path = default_storage.save(f'chat_images/{file.name}', ContentFile(file.read()))
            else:
                path = default_storage.save(f'chat_files/{file.name}', ContentFile(file.read()))

            url = default_storage.url(path)

            return JsonResponse({
                'success': True,
                'url': url,
                'is_image': is_image,
                'file_name': file.name
            })
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})




class APIHealthCheck(View):
    """Health check endpoint"""

    def get(self, request):
        try:
            # Check database
            db_status = self.check_database()

            return JsonResponse({
                'status': 'healthy' if db_status else 'degraded',
                'timestamp': timezone.now().isoformat(),
                'database': 'connected' if db_status else 'disconnected',
                'debug': settings.DEBUG,
            })
        except Exception as e:
            return JsonResponse({
                'status': 'unhealthy',
                'error': str(e)
            }, status=500)

    def check_database(self):
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                return True
        except:
            return False


@method_decorator(csrf_exempt, name='dispatch')
class APIUpdateProfilePhoto(LoginRequiredMixin, View):
    """Update profile photo"""

    def post(self, request):
        try:
            # Check if file was uploaded
            if 'file' not in request.FILES:
                return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)

            photo = request.FILES['file']

            # Validate file type
            if not photo.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'File must be an image'}, status=400)

            # Check file size (limit to 5MB)
            if photo.size > 5 * 1024 * 1024:
                return JsonResponse({'success': False, 'error': 'Image size must be less than 5MB'}, status=400)

            # Get user profile
            profile = request.user.profile

            # Delete old photo if it's not the default
            if profile.profile_photo and profile.profile_photo.name != 'default_profile.jpg':
                if os.path.isfile(profile.profile_photo.path):
                    os.remove(profile.profile_photo.path)

            # Save new photo
            profile.profile_photo = photo
            profile.save()

            # Return success response with new photo URL
            return JsonResponse({
                'success': True,
                'url': profile.profile_photo.url,
                'message': 'Profile photo updated successfully!'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


@method_decorator(csrf_exempt, name='dispatch')
class APIUpdateCoverPhoto(LoginRequiredMixin, View):
    """Update cover photo"""

    def post(self, request):
        try:
            # Check if file was uploaded
            if 'file' not in request.FILES:
                return JsonResponse({'success': False, 'error': 'No file provided'}, status=400)

            photo = request.FILES['file']

            # Validate file type
            if not photo.content_type.startswith('image/'):
                return JsonResponse({'success': False, 'error': 'File must be an image'}, status=400)

            # Check file size (limit to 10MB for cover)
            if photo.size > 10 * 1024 * 1024:
                return JsonResponse({'success': False, 'error': 'Image size must be less than 10MB'}, status=400)

            # Get user profile
            profile = request.user.profile

            # Delete old cover if it's not the default
            if profile.cover_photo and profile.cover_photo.name != 'default_cover.jpg':
                if os.path.isfile(profile.cover_photo.path):
                    os.remove(profile.cover_photo.path)

            # Save new cover
            profile.cover_photo = photo
            profile.save()

            # Return success response with new cover URL
            return JsonResponse({
                'success': True,
                'url': profile.cover_photo.url,
                'message': 'Cover photo updated successfully!'
            })

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class APIUserSuggestions(LoginRequiredMixin, View):
    """API endpoint for real-time user suggestions"""

    def get(self, request):
        query = request.GET.get('q', '').strip()

        # Return empty for queries with less than 1 character
        if len(query) < 1:
            return JsonResponse({'users': []})

        # Case-insensitive search using __icontains
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query)
        ).exclude(
            id=request.user.id
        ).exclude(
            is_staff=True
        ).exclude(
            is_superuser=True
        ).select_related('profile')[:10]

        data = []
        for user in users:
            data.append({
                'id': user.id,
                'username': user.username,
                'full_name': user.get_full_name(),
                'profile_photo': user.profile.profile_photo.url if user.profile.profile_photo else '/static/default.jpg',
                'followers_count': user.profile.followers_count,
                'is_following': Follow.objects.filter(follower=request.user, following=user).exists(),
            })

        return JsonResponse({'users': data})

class APIUnreadMessagesCount(LoginRequiredMixin, View):
    """Get unread messages count for the current user"""

    def get(self, request):
        from core.models import Message
        count = Message.objects.filter(
            recipient=request.user,
            is_read=False
        ).count()
        return JsonResponse({'count': count})