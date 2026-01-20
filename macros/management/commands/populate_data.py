from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from macros.models import CubaseVersion
from accounts.models import UserProfile


class Command(BaseCommand):
    help = 'Populate the database with initial data'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing data before populating',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write('Clearing existing data...')
            CubaseVersion.objects.all().delete()

        self.stdout.write('Creating Cubase versions...')
        self.create_cubase_versions()
        
        self.stdout.write('Creating sample users...')
        self.create_sample_users()
        
        self.stdout.write(
            self.style.SUCCESS('Successfully populated database with initial data')
        )

    def create_cubase_versions(self):
        """Create Cubase major versions from 4 to 15, plus Unspecified"""
        # Remove "Cubase 4" if it exists (we only want "Cubase 4 or older")
        CubaseVersion.objects.filter(version='Cubase 4').delete()
        
        versions = []
        
        # Add "Unspecified" as the default option (with major=0 so it sorts last)
        versions.append({
            'version': 'Unspecified',
            'major': 0,
        })
        
        # Add "Cubase 4 or older" option
        versions.append({
            'version': 'Cubase 4 or older',
            'major': 4,
        })
        
        # Generate major versions 5-15 (4 is covered by "4 or older")
        for major in range(5, 16):  # 5 to 15 inclusive
            versions.append({
                'version': f'Cubase {major}',
                'major': major,
            })
        
        # Sort by major version (descending), but keep Unspecified at the beginning
        versions.sort(key=lambda x: (x['major'] != 0, -x['major'] if x['major'] != 0 else 0))

        for version_data in versions:
            version, created = CubaseVersion.objects.get_or_create(
                version=version_data['version'],
                defaults={
                    'major_version': version_data['major'],
                }
            )
            if created:
                self.stdout.write(f'  Created: {version.version}')
            else:
                self.stdout.write(f'  Already exists: {version.version}')

    # Categories are no longer used - removed create_categories method

    def create_sample_users(self):
        """Create sample users for demonstration"""
        sample_users = [
            {
                'username': 'john_producer',
                'email': 'john@example.com',
                'first_name': 'John',
                'last_name': 'Producer',
                'bio': 'Electronic music producer specializing in techno and house music.',
                'location': 'Berlin, Germany',
                'preferred_cubase_version': 'Cubase 13'
            },
            {
                'username': 'sarah_composer',
                'email': 'sarah@example.com',
                'first_name': 'Sarah',
                'last_name': 'Composer',
                'bio': 'Film composer with 10+ years of experience in orchestral arrangements.',
                'location': 'Los Angeles, CA',
                'preferred_cubase_version': 'Cubase 12'
            },
            {
                'username': 'mike_engineer',
                'email': 'mike@example.com',
                'first_name': 'Mike',
                'last_name': 'Engineer',
                'bio': 'Audio engineer working with various genres from rock to jazz.',
                'location': 'Nashville, TN',
                'preferred_cubase_version': 'Cubase 13'
            },
        ]

        for user_data in sample_users:
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults={
                    'email': user_data['email'],
                    'first_name': user_data['first_name'],
                    'last_name': user_data['last_name'],
                }
            )
            
            if created:
                user.set_password('samplepass123')
                user.save()
                
                # Create or update profile
                profile, profile_created = UserProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'bio': user_data['bio'],
                        'location': user_data['location'],
                        'preferred_cubase_version': user_data['preferred_cubase_version'],
                        'show_real_name': True,
                        'email_notifications': True,
                    }
                )
                
                self.stdout.write(f'  Created user: {user.username}')
            else:
                self.stdout.write(f'  User already exists: {user.username}') 