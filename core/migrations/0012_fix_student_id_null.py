from django.db import migrations, models
from django.utils import timezone

def set_default_student_ids(apps, schema_editor):
    Profile = apps.get_model('core', 'Profile')
    for profile in Profile.objects.filter(student_id__isnull=True):
        # Generate a temporary unique student ID
        profile.student_id = f"TEMP_{profile.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        profile.save()
    
    # Also handle empty strings
    for profile in Profile.objects.filter(student_id=''):
        profile.student_id = f"TEMP_{profile.user.id}_{timezone.now().strftime('%Y%m%d%H%M%S')}"
        profile.save()

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0011_profile_email_verification_otp_and_more'),  # Use your actual last migration
    ]

    operations = [
        # First, remove the unique constraint temporarily
        migrations.AlterField(
            model_name='profile',
            name='student_id',
            field=models.CharField(max_length=50, blank=True, null=True, unique=False),
        ),
        # Run the data migration
        migrations.RunPython(set_default_student_ids),
        # Now make it unique and required
        migrations.AlterField(
            model_name='profile',
            name='student_id',
            field=models.CharField(max_length=50, unique=True, null=False, blank=False),
        ),
    ]