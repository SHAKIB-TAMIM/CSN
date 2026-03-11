from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import FileExtensionValidator
from .models import Profile, Post, Comment, Story, Message


class UserRegistrationForm(UserCreationForm):
    """Enhanced user registration form"""
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email'
        })
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Choose a username'
        })
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Create a password'
        })
    )
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    )

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('This email is already registered.')
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        if commit:
            user.save()
        return user


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

    class Meta:
        model = Profile
        fields = [
            'profile_photo', 'cover_photo', 'bio', 'location',
            'birth_date', 'website', 'facebook', 'twitter',
            'instagram', 'linkedin'
        ]


class PostForm(forms.ModelForm):
    """Enhanced post creation form"""
    content = forms.CharField(
        required=True,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': "What's on your mind?",
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
    video = forms.FileField(
        required=False,
        validators=[FileExtensionValidator(['mp4', 'mov', 'avi', 'webm'])],
        widget=forms.FileInput(attrs={
            'class': 'form-control-file',
            'accept': 'video/*'
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
        fields = ['content', 'image', 'video', 'privacy']

    def clean(self):
        cleaned_data = super().clean()
        content = cleaned_data.get('content')
        image = cleaned_data.get('image')
        video = cleaned_data.get('video')

        if not content and not image and not video:
            raise forms.ValidationError(
                'Your post must contain either text, image, or video.'
            )

        if image and video:
            raise forms.ValidationError(
                'You cannot upload both image and video in the same post.'
            )

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