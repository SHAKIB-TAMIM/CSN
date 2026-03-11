from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from core.models import Post, SiteStatistic, Announcement

class Command(BaseCommand):
    help = 'Update site statistics with real data'

    def handle(self, *args, **options):
        self.stdout.write("Updating statistics...")
        
        # Calculate real statistics
        stats = {
            'active_users': {
                'value': User.objects.filter(is_active=True).count(),
                'display': 'Active Students',
                'icon': 'fas fa-users'
            },
            'total_posts': {
                'value': Post.objects.count(),
                'display': 'Posts Shared',
                'icon': 'fas fa-file-alt'
            },
            'total_campuses': {
                'value': 150,  # You can make this dynamic too
                'display': 'Campuses',
                'icon': 'fas fa-university'
            },
            'daily_posts': {
                'value': Post.objects.filter(created_at__date=timezone.now().date()).count(),
                'display': 'Daily Posts',
                'icon': 'fas fa-pen'
            },
            'active_community': {
                'value': '24/7',
                'display': 'Active Community',
                'icon': 'fas fa-clock'
            }
        }
        
        # Update or create statistics
        for key, data in stats.items():
            stat, created = SiteStatistic.objects.update_or_create(
                name=key,
                defaults={
                    'value': data['value'],
                    'display_name': data['display'],
                    'icon': data['icon']
                }
            )
            self.stdout.write(f"  {'Created' if created else 'Updated'} {key}: {data['value']}")
        
        self.stdout.write(self.style.SUCCESS("Statistics updated successfully!"))