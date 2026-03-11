"""
Utility functions for the Campus Social Network application
"""
import re
import uuid
import hashlib
import random
import string
from datetime import datetime, timedelta
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def generate_unique_username(base):
    """
    Generate a unique username from a base string
    """
    import uuid
    return f"{base}_{uuid.uuid4().hex[:8]}"

def paginate_queryset(request, queryset, per_page=10, param_name='page'):
    """
    Utility function to paginate querysets
    Returns paginated queryset and paginator object
    """
    paginator = Paginator(queryset, per_page)
    page = request.GET.get(param_name, 1)
    
    try:
        paginated_qs = paginator.page(page)
    except PageNotAnInteger:
        paginated_qs = paginator.page(1)
    except EmptyPage:
        paginated_qs = paginator.page(paginator.num_pages)
    
    return paginated_qs

def get_client_ip(request):
    """
    Get client IP address from request
    Handles proxies and forwarded headers
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def validate_file_size(value, max_size_mb=10):
    """
    Validate file size is under max_size_mb
    """
    max_size = max_size_mb * 1024 * 1024
    if value.size > max_size:
        raise ValidationError(f'File size must be under {max_size_mb}MB')
    return value

def time_ago(timestamp):
    """
    Convert timestamp to human readable time ago
    """
    if not timestamp:
        return "unknown"
    
    now = timezone.now()
    
    if isinstance(timestamp, str):
        try:
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        except:
            return timestamp
    
    diff = now - timestamp
    
    if diff.days > 365:
        years = diff.days // 365
        return f"{years} year{'s' if years > 1 else ''} ago"
    elif diff.days > 30:
        months = diff.days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    elif diff.days > 7:
        weeks = diff.days // 7
        return f"{weeks} week{'s' if weeks > 1 else ''} ago"
    elif diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "just now"

def generate_otp(length=6):
    """
    Generate a numeric OTP of specified length
    """
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

def is_otp_valid(otp_sent_at, expiry_minutes=10):
    """
    Check if OTP is still valid (within expiry time)
    """
    if not otp_sent_at:
        return False
    expiry_time = otp_sent_at + timedelta(minutes=expiry_minutes)
    return timezone.now() <= expiry_time

def is_valid_university_email(email):
    """
    Simple validation for university emails
    Accepts most educational domains including .com
    """
    email_lower = email.lower()
    
    if '@' not in email_lower:
        return False
    
    domain = email_lower.split('@')[1]
    
    # List of valid educational domain patterns
    valid_patterns = [
        r'.*\.edu$',
        r'.*\.ac\.[a-z]{2}$',
        r'.*\.edu\.[a-z]{2}$',
        r'.*\.sch\.[a-z]{2}$',
    ]
    
    # Check against patterns
    import re
    for pattern in valid_patterns:
        if re.match(pattern, domain):
            return True
    
    # Accept domains containing these keywords (includes .com)
    educational_keywords = ['university', 'college', 'student', 'campus', 'academy']
    domain_lower = domain.lower()
    
    for keyword in educational_keywords:
        if keyword in domain_lower:
            return True
    
    # For specific universities, you can add them here
    allowed_domains = [
        'gmail.com',  # Remove this if you want only educational emails
        'yahoo.com',
        'hotmail.com',
    ]
    
    if domain in allowed_domains:
        return True
    
    return False

def send_otp_email(user, otp):
    """
    Send OTP verification email
    """
    subject = "Verify Your Email - Campus Network"
    
    context = {
        'user': user,
        'otp': otp,
        'site_url': settings.SITE_URL,
        'expiry_minutes': 10,
    }
    
    html_content = render_to_string('emails/otp_verification.html', context)
    text_content = strip_tags(html_content)
    
    send_mail(
        subject,
        text_content,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        html_message=html_content,
        fail_silently=False,
    )

def hash_token(token):
    """
    Hash a token for secure storage
    """
    return hashlib.sha256(token.encode()).hexdigest()

def create_unique_slug(instance, source_field, slug_field, separator='-'):
    """
    Create a unique slug for a model instance
    """
    slug = slugify(getattr(instance, source_field))
    unique_slug = slug
    counter = 1
    
    Model = instance.__class__
    while Model.objects.filter(**{slug_field: unique_slug}).exists():
        unique_slug = f"{slug}{separator}{counter}"
        counter += 1
    
    return unique_slug

def truncate_text(text, length=100, suffix='...'):
    """
    Truncate text to specified length
    """
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + suffix

def get_file_extension(filename):
    """
    Get file extension from filename
    """
    return filename.split('.')[-1].lower() if '.' in filename else ''

def is_image_file(filename):
    """
    Check if file is an image based on extension
    """
    image_extensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg']
    return get_file_extension(filename) in image_extensions

def is_video_file(filename):
    """
    Check if file is a video based on extension
    """
    video_extensions = ['mp4', 'mov', 'avi', 'mkv', 'webm', 'flv', 'wmv']
    return get_file_extension(filename) in video_extensions

def format_number(num):
    """
    Format large numbers with K, M, B suffixes
    """
    if num < 1000:
        return str(num)
    elif num < 1000000:
        return f"{num/1000:.1f}K"
    elif num < 1000000000:
        return f"{num/1000000:.1f}M"
    else:
        return f"{num/1000000000:.1f}B"

def get_trending_score(likes, comments, shares, age_hours):
    """
    Calculate trending score based on engagement and recency
    """
    engagement = likes + (comments * 2) + (shares * 3)
    recency_factor = 1 / (age_hours + 1)
    return engagement * recency_factor

def generate_random_color():
    """
    Generate a random hex color
    """
    return "#{:06x}".format(random.randint(0, 0xFFFFFF))

def chunk_list(lst, chunk_size):
    """
    Split a list into chunks of specified size
    """
    for i in range(0, len(lst), chunk_size):
        yield lst[i:i + chunk_size]

def extract_mentions(text):
    """
    Extract @mentions from text
    """
    mentions = re.findall(r'@(\w+)', text)
    return list(set(mentions))

def extract_hashtags(text):
    """
    Extract #hashtags from text
    """
    hashtags = re.findall(r'#(\w+)', text)
    return list(set(hashtags))

def sanitize_html(text):
    """
    Basic HTML sanitization
    """
    # Remove script tags and their content
    text = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
    # Remove other potentially dangerous tags
    text = re.sub(r'<(iframe|object|embed|form|input|button).*?>.*?</\1>', '', text, flags=re.DOTALL)
    return text

def calculate_age(birth_date):
    """
    Calculate age from birth date
    """
    if not birth_date:
        return None
    
    today = timezone.now().date()
    age = today.year - birth_date.year
    
    # Adjust if birthday hasn't occurred this year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    
    return age

def dict_to_query_params(params_dict):
    """
    Convert dictionary to URL query parameters
    """
    import urllib.parse
    return urllib.parse.urlencode(params_dict)

def get_user_agent(request):
    """
    Get user agent from request
    """
    return request.META.get('HTTP_USER_AGENT', '')

def is_mobile_device(request):
    """
    Check if request comes from mobile device
    """
    user_agent = get_user_agent(request).lower()
    mobile_keywords = ['mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 'windows phone']
    return any(keyword in user_agent for keyword in mobile_keywords)

def json_serializable(obj):
    """
    Convert object to JSON serializable format
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, timezone.datetime):
        return obj.isoformat()
    if isinstance(obj, timezone.timedelta):
        return str(obj)
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if isinstance(obj, set):
        return list(obj)
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def get_cached_or_set(cache_key, get_func, timeout=300):
    """
    Get from cache or set if not exists
    """
    from django.core.cache import cache
    
    data = cache.get(cache_key)
    if data is None:
        data = get_func()
        cache.set(cache_key, data, timeout)
    return data

def clear_model_cache(model_name):
    """
    Clear cache for a specific model
    """
    from django.core.cache import cache
    
    pattern = f"*{model_name.lower()}*"
    # This is cache backend dependent - works with redis
    try:
        keys = cache.keys(pattern)
        cache.delete_many(keys)
    except:
        # Fallback - clear all cache (not ideal)
        cache.clear()