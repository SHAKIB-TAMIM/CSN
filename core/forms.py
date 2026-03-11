from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import FileExtensionValidator
from .models import Profile, Post, Comment, Story, Message, Department

class UniversityRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(widget=forms.PasswordInput, label="Password")
    password2 = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    
    class Meta:
        model = User
        fields = ['username', 'email']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("A user with this email already exists.")
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Passwords do not match.")
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        user.is_active = False
        if commit:
            user.save()
        return user


class EmailVerificationForm(forms.Form):
    otp = forms.CharField(max_length=6, min_length=6, label="OTP Code")
    
    def clean_otp(self):
        otp = self.cleaned_data.get('otp')
        if not otp.isdigit():
            raise forms.ValidationError("OTP must contain only digits.")
        return otp


class CompleteProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['bio', 'department', 'batch', 'student_id', 'location']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['department'].queryset = Department.objects.filter(is_active=True)
        self.fields['department'].required = True
        self.fields['batch'].required = True
        self.fields['student_id'].required = True


class UserUpdateForm(forms.ModelForm):
    """Form for updating user information"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )

    class Meta:
        model = User
        fields = ['email']


class ProfileUpdateForm(forms.ModelForm):
    """Enhanced profile update form"""
    profile_photo = forms.ImageField(
        required=False,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'image/*'
        })
    )
    cover_photo = forms.ImageField(
        required=False,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'image/*'
        })
    )
    bio = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Tell us about yourself...'
        })
    )
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'City, Country'
        })
    )
    birth_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    website = forms.URLField(
        required=False,
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://yourwebsite.com'
        })
    )
    
    # University fields
    department = forms.ModelChoiceField(
        queryset=Department.objects.filter(is_active=True),
        required=False,
        empty_label="Select Department",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    batch = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'e.g., 2024'
        })
    )
    student_id = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Student ID'
        })
    )

    class Meta:
        model = Profile
        fields = [
            'profile_photo', 'cover_photo', 'bio', 'location',
            'birth_date', 'website', 'facebook', 'twitter',
            'instagram', 'linkedin', 'department', 'batch', 'student_id'
        ]


# Update the PostForm class in core/forms.py

class PostForm(forms.ModelForm):
    """Enhanced post creation form with document support"""
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': "What's on your mind?",
            'maxlength': 5000
        })
    )
    image = forms.ImageField(
        required=False,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif', 'webp'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'image/*'
        })
    )
    video = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['mp4', 'mov', 'avi', 'webm', 'mkv'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'video/*'
        })
    )
    document = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['pdf', 'doc', 'docx', 'txt', 'ppt', 'pptx', 'xls', 'xlsx', 'csv', 'zip', 'rar'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': '.pdf,.doc,.docx,.txt,.ppt,.pptx,.xls,.xlsx,.csv,.zip,.rar'
        })
    )
    privacy = forms.ChoiceField(
        choices=Post.PRIVACY_CHOICES,
        initial='public',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )

    class Meta:
        model = Post
        fields = ['content', 'image', 'video', 'document', 'privacy']

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')
        document = cleaned_data.get('document')

        if not content and not image and not video and not document:
            raise forms.ValidationError(
                'Your post must contain either text, image, video, or document.'
            )

        # Count how many media files are uploaded
        media_count = sum(1 for x in [image, video, document] if x)
        
        if media_count > 1:
            raise forms.ValidationError(
                'You can only upload one media file (image/video/document) per post.'
            )

        # Validate file sizes
        if image and image.size > 10 * 1024 * 1024:  # 10MB
            raise forms.ValidationError('Image file size must be less than 10MB.')
        
        if video and video.size > 50 * 1024 * 1024:  # 50MB
            raise forms.ValidationError('Video file size must be less than 50MB.')
        
        if document and document.size > 20 * 1024 * 1024:  # 20MB
            raise forms.ValidationError('Document file size must be less than 20MB.')

        return cleaned_data


class CommentForm(forms.ModelForm):
    """Enhanced comment form"""
    content = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Write a comment...',
            'maxlength': 1000
        })
    )

    class Meta:
        model = Comment
        fields = ['content']


class MessageForm(forms.ModelForm):
    """Form for sending messages"""
    content = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Type your message...',
            'maxlength': 5000
        })
    )
    image = forms.ImageField(
        required=False,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'image/*'
        })
    )
    file = forms.FileField(
        required=False,
        widget=forms.FileInput(attrs={
            'class': 'form-control-file'
        })
    )

    class Meta:
        model = Message
        fields = ['content', 'image', 'file']

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        image = cleaned_data.get('image')
        file = cleaned_data.get('file')

        if not content and not image and not file:
            raise forms.ValidationError('Message must contain either text, image, or file.')

        return cleaned_data


class StoryForm(forms.ModelForm):
    """Form for creating stories"""
    image = forms.ImageField(
        required=True,
        validators=[FileExtensionValidator(['jpg', 'jpeg', 'png', 'gif'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'image/*'
        })
    )
    text = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Add a caption...',
            'maxlength': 100
        })
    )
    background_color = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'type': 'color',
            'value': '#000000'
        })
    )

    class Meta:
        model = Story
        fields = ['image', 'text', 'background_color']


class ContactForm(forms.Form):
    """Contact form for users to reach support"""
    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Your name'
        })
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'your@email.com'
        })
    )
    subject = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Subject'
        })
    )
    message = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 5,
            'placeholder': 'Your message...'
        })
    )