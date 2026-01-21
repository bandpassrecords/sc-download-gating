from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from django.core.signing import TimestampSigner
import secrets
from datetime import timedelta
import random


class UserProfile(models.Model):
    """Extended user profile model"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Public identifier - random unique ID for public URLs (keeps email private)
    public_id = models.CharField(max_length=32, unique=True, db_index=True, editable=False, null=True, blank=True)
    # Generated fake display name for privacy (based on first two letters of email)
    generated_display_name = models.CharField(max_length=100, blank=True, editable=False)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    
    # Privacy settings
    show_email = models.BooleanField(default=False)
    show_real_name = models.BooleanField(default=False)  # Default to False to use fake name for privacy

    # Notifications
    # If disabled, this overrides any per-gate email notification setting.
    notify_on_downloads = models.BooleanField(
        default=True,
        help_text="Send me an email when someone downloads a file from one of my gates.",
    )
    
    # Stats
    total_uploads = models.PositiveIntegerField(default=0)
    total_downloads = models.PositiveIntegerField(default=0)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
    
    def __str__(self):
        return f"{self.user.email}'s Profile"
    
    @staticmethod
    def generate_fake_display_name(email):
        """Generate a fake display name based on the first two letters of email"""
        if not email or len(email) < 2:
            return "Anonymous User"
        
        # Get first two letters (lowercase)
        first_letter = email[0].lower()
        second_letter = email[1].lower() if len(email) > 1 else 'a'
        
        # Word mappings for first letter (adjectives/nouns)
        first_words = {
            'a': ['Ancient', 'Amazing', 'Artistic', 'Aurora', 'Astral'],
            'b': ['Brilliant', 'Bold', 'Brave', 'Bright', 'Breezy'],
            'c': ['Creative', 'Clever', 'Cosmic', 'Crystal', 'Calm'],
            'd': ['Dynamic', 'Daring', 'Divine', 'Dazzling', 'Deep'],
            'e': ['Elegant', 'Epic', 'Ethereal', 'Energetic', 'Enchanted'],
            'f': ['Fantastic', 'Fierce', 'Floating', 'Frozen', 'Fiery'],
            'g': ['Guardian', 'Golden', 'Graceful', 'Glorious', 'Gentle'],
            'h': ['Heroic', 'Harmonious', 'Heavenly', 'Hidden', 'Humble'],
            'i': ['Infinite', 'Inspired', 'Icy', 'Illuminated', 'Intrepid'],
            'j': ['Jubilant', 'Jade', 'Journey', 'Jovial', 'Just'],
            'k': ['Keen', 'Kind', 'Knight', 'Kaleidoscope', 'Kinetic'],
            'l': ['Luminous', 'Legendary', 'Lively', 'Lucky', 'Lunar'],
            'm': ['Majestic', 'Mystic', 'Mighty', 'Melodic', 'Magical'],
            'n': ['Noble', 'Nebula', 'Natural', 'Nimble', 'Noble'],
            'o': ['Oceanic', 'Optimistic', 'Opulent', 'Original', 'Orbital'],
            'p': ['Powerful', 'Peaceful', 'Prismatic', 'Proud', 'Pure'],
            'q': ['Quiet', 'Quick', 'Quasar', 'Quaint', 'Quantum'],
            'r': ['Radiant', 'Rapid', 'Royal', 'Rustic', 'Rising'],
            's': ['Stellar', 'Swift', 'Sacred', 'Serene', 'Shining'],
            't': ['Titanic', 'Tranquil', 'Triumphant', 'Twilight', 'Thunder'],
            'u': ['Unique', 'Unstoppable', 'Ultimate', 'Universe', 'United'],
            'v': ['Valiant', 'Vibrant', 'Vast', 'Victorious', 'Vivid'],
            'w': ['Wise', 'Wild', 'Wondrous', 'Warm', 'Wandering'],
            'x': ['Xenial', 'Xenon', 'Xylophone', 'Xenial', 'Xenon'],
            'y': ['Youthful', 'Yearning', 'Yellow', 'Yonder', 'Yielding'],
            'z': ['Zealous', 'Zenith', 'Zephyr', 'Zestful', 'Zodiac'],
        }
        
        # Word mappings for second letter (nouns)
        second_words = {
            'a': ['Aurora', 'Angel', 'Apex', 'Artisan', 'Atlas'],
            'b': ['Beacon', 'Bard', 'Blade', 'Breeze', 'Bridge'],
            'c': ['Champion', 'Crystal', 'Comet', 'Crown', 'Cascade'],
            'd': ['Dragon', 'Dawn', 'Dream', 'Diamond', 'Destiny'],
            'e': ['Eagle', 'Echo', 'Empire', 'Essence', 'Eclipse'],
            'f': ['Flame', 'Falcon', 'Forest', 'Fortress', 'Fountain'],
            'g': ['Guardian', 'Gale', 'Gem', 'Glacier', 'Grove'],
            'h': ['Heights', 'Harbor', 'Horizon', 'Harmony', 'Haven'],
            'i': ['Island', 'Iris', 'Ivory', 'Inferno', 'Infinity'],
            'j': ['Jewel', 'Journey', 'Jungle', 'Jester', 'Jupiter'],
            'k': ['Keeper', 'Knight', 'Kingdom', 'Kite', 'Kraken'],
            'l': ['Light', 'Lion', 'Lagoon', 'Legend', 'Lighthouse'],
            'm': ['Mountain', 'Moon', 'Mist', 'Monarch', 'Mirage'],
            'n': ['Nexus', 'Night', 'Nova', 'Nest', 'Nymph'],
            'o': ['Oracle', 'Ocean', 'Oasis', 'Orbit', 'Owl'],
            'p': ['Phoenix', 'Peak', 'Pinnacle', 'Portal', 'Prism'],
            'q': ['Quest', 'Quill', 'Quartz', 'Quiver', 'Quarry'],
            'r': ['Rider', 'River', 'Realm', 'Ridge', 'Raven'],
            's': ['Star', 'Storm', 'Summit', 'Sage', 'Serpent'],
            't': ['Tower', 'Tide', 'Throne', 'Tiger', 'Temple'],
            'u': ['Unicorn', 'Unity', 'Umbra', 'Urchin', 'Utopia'],
            'v': ['Voyager', 'Valley', 'Vortex', 'Vanguard', 'Vista'],
            'w': ['Warrior', 'Wave', 'Wind', 'Wolf', 'Warden'],
            'x': ['Xenon', 'Xerox', 'Xyst', 'Xenial', 'Xenon'],
            'y': ['Yonder', 'Yarn', 'Yew', 'Yacht', 'Yin'],
            'z': ['Zenith', 'Zephyr', 'Zone', 'Zodiac', 'Zest'],
        }
        
        # Get words based on letters
        first_word_options = first_words.get(first_letter, ['Mysterious'])
        second_word_options = second_words.get(second_letter, ['User'])
        
        # Randomly select from options for variety
        first_word = random.choice(first_word_options)
        second_word = random.choice(second_word_options)
        
        return f"{first_word} {second_word}"
    
    @property
    def display_name(self):
        """Return the display name for the user (for public profiles)"""
        # Check if this is the deleted account user
        if self.user.username == 'deleted_account' or self.user.email == 'deleted@system.local':
            return 'Deleted Account'
        
        # If user wants to show real name AND has first_name and last_name, use real name
        if self.show_real_name and self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        
        # Otherwise, use generated fake display name for privacy
        if self.generated_display_name:
            return self.generated_display_name
        
        # Generate if not set (for existing users)
        if self.user.email:
            self.generated_display_name = self.generate_fake_display_name(self.user.email)
            self.save(update_fields=['generated_display_name'])
            return self.generated_display_name
        
        return "Anonymous User"
    
    def get_own_profile_display_name(self):
        """Return the display name for the logged-in user's own profile"""
        # For own profile: show first name + surname if set, otherwise email
        if self.user.first_name and self.user.last_name:
            return f"{self.user.first_name} {self.user.last_name}".strip()
        # Fallback to email if no first/last name
        return self.user.email if self.user.email else "User"
    
    @staticmethod
    def generate_public_id():
        """Generate a unique random public ID"""
        return secrets.token_urlsafe(24)  # 32 characters when URL-safe encoded
    
    def save(self, *args, **kwargs):
        """Override save to generate public_id and display name if they don't exist"""
        if not self.public_id:
            # Generate unique public_id
            max_attempts = 10
            for _ in range(max_attempts):
                public_id = self.generate_public_id()
                if not UserProfile.objects.filter(public_id=public_id).exists():
                    self.public_id = public_id
                    break
            else:
                # If we couldn't generate a unique ID after max attempts, raise error
                raise ValueError("Could not generate unique public_id")
        
        # Generate fake display name if not set
        if not self.generated_display_name and self.user.email:
            self.generated_display_name = self.generate_fake_display_name(self.user.email)
        
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create or update user profile when user is created or updated"""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save user profile when user is saved"""
    if hasattr(instance, 'profile'):
        instance.profile.save()
    else:
        UserProfile.objects.create(user=instance)


class EmailVerification(models.Model):
    """Model for email verification tokens"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='email_verification')
    token = models.CharField(max_length=64, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Email Verification"
        verbose_name_plural = "Email Verifications"
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Verification for {self.user.email} - {'Verified' if self.verified else 'Pending'}"
    
    @classmethod
    def generate_token(cls):
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)
    
    def is_expired(self):
        """Check if token has expired (10 minutes)"""
        if self.verified:
            return False
        expiration_time = self.created_at + timedelta(minutes=10)
        return timezone.now() > expiration_time
    
    def verify(self):
        """Mark email as verified"""
        self.verified = True
        self.verified_at = timezone.now()
        self.save()
        # Activate user account
        self.user.is_active = True
        self.user.save()
