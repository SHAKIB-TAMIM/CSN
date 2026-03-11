from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Profile, Post, Comment
from faker import Faker
import random

class Command(BaseCommand):
    help = 'Initialize database with sample data'
    
    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=50, help='Number of users to create')
        parser.add_argument('--posts', type=int, default=200, help='Number of posts to create')
    
    def handle(self, *args, **options):
        fake = Faker()
        
        # Create users
        self.stdout.write('Creating users...')
        users = []
        for i in range(options['users']):
            username = fake.user_name() + str(i)
            email = fake.email()
            password = 'password123'
            
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=fake.first_name(),
                last_name=fake.last_name()
            )
            
            # Update profile
            profile = user.profile
            profile.bio = fake.text(max_nb_chars=200)
            profile.location = fake.city()
            profile.birth_date = fake.date_of_birth(minimum_age=18, maximum_age=30)
            profile.website = fake.url()
            profile.save()
            
            users.append(user)
            self.stdout.write(f'  Created user: {username}')
        
        # Create follow relationships
        self.stdout.write('Creating follow relationships...')
        for user in users:
            # Follow random users
            to_follow = random.sample(users, random.randint(5, 20))
            for follow_user in to_follow:
                if user != follow_user:
                    user.following.get_or_create(following=follow_user)
        
        # Create posts
        self.stdout.write('Creating posts...')
        for i in range(options['posts']):
            user = random.choice(users)
            post = Post.objects.create(
                user=user,
                content=fake.text(max_nb_chars=500),
                privacy=random.choice(['public', 'followers', 'private'])
            )
            
            # Add likes
            for _ in range(random.randint(0, 30)):
                liker = random.choice(users)
                if liker != user:
                    post.likes.get_or_create(user=liker)
            
            # Add comments
            for _ in range(random.randint(0, 10)):
                commenter = random.choice(users)
                Comment.objects.create(
                    user=commenter,
                    post=post,
                    content=fake.text(max_nb_chars=100)
                )
            
            self.stdout.write(f'  Created post {i+1}/{options["posts"]}')
        
        self.stdout.write(self.style.SUCCESS('Successfully initialized database!'))