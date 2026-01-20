from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import os


class CubaseVersion(models.Model):
    """Model for tracking Cubase versions - only major version is stored"""
    version = models.CharField(max_length=50, unique=True)
    major_version = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Order: Unspecified (major=0) first, then others by version descending
        # We'll use custom ordering in forms/views to put Unspecified first
        ordering = ['-major_version']
    
    def __str__(self):
        return self.version


class Macro(models.Model):
    """Model for individual macros/commands"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='macros')
    cubase_version = models.ForeignKey(CubaseVersion, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    key_binding = models.CharField(max_length=100, blank=True)  # For storing key combinations
    commands_json = models.JSONField(default=list, blank=True)  # Store the actual commands that make up this macro
    xml_snippet = models.TextField(blank=True)  # Store the macro definition XML snippet (from <list name="Macros">)
    reference_snippet = models.TextField(blank=True)  # Store the macro reference XML snippet (for <list name="Commands">)
    is_private = models.BooleanField(default=True)  # True = private, False = public (default to private for safety)
    secret_token = models.CharField(max_length=32, unique=True, null=True, blank=True, db_index=True)  # Secret token for sharing private macros
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # For tracking popularity
    download_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} by {self.user.username}"
    
    def get_absolute_url(self):
        return f'/macros/{self.id}/'
    
    @property
    def average_rating(self):
        """Calculate average rating from votes"""
        votes = self.votes.all()
        if votes:
            return sum(vote.rating for vote in votes) / len(votes)
        return 0
    
    @property
    def vote_count(self):
        """Get total number of votes"""
        return self.votes.count()
    
    @property
    def commands(self):
        """Get the list of commands that make up this macro"""
        return self.commands_json or []
    
    @property  
    def commands_count(self):
        """Get the number of commands in this macro"""
        return len(self.commands_json) if self.commands_json else 0
    
    def generate_secret_token(self):
        """Generate a unique secret token for sharing private macros"""
        import secrets
        token = secrets.token_urlsafe(24)  # 24 bytes = 32 characters in URL-safe base64
        # Ensure uniqueness
        while Macro.objects.filter(secret_token=token).exists():
            token = secrets.token_urlsafe(24)
        self.secret_token = token
        self.save(update_fields=['secret_token'])
        return token
    
    def get_secret_link(self, request=None):
        """Get the secret sharing link for this macro"""
        if not self.secret_token:
            self.generate_secret_token()
        if request:
            return request.build_absolute_uri(f'/macros/share/{self.secret_token}/')
        return f'/macros/share/{self.secret_token}/'


class MacroVote(models.Model):
    """Model for macro voting/rating system"""
    RATING_CHOICES = [
        (1, '1 Star'),
        (2, '2 Stars'),
        (3, '3 Stars'),
        (4, '4 Stars'),
        (5, '5 Stars'),
    ]
    
    macro = models.ForeignKey(Macro, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.PositiveIntegerField(
        choices=RATING_CHOICES,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['macro', 'user']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} rated {self.macro.name}: {self.rating} stars"


class MacroFavorite(models.Model):
    """Model for user favorites"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_macros')
    macro = models.ForeignKey(Macro, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'macro']
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.username} favorited {self.macro.name}"


class MacroCollection(models.Model):
    """Model for user-created macro collections"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='macro_collections')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    macros = models.ManyToManyField(Macro, related_name='collections', blank=True)
    is_private = models.BooleanField(default=True)  # True = private, False = public (default to private for safety)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['user', 'name']
    
    def __str__(self):
        return f"{self.name} by {self.user.username}"
    
    def get_absolute_url(self):
        return f'/macros/collections/{self.id}/'


class DownloadOrder(models.Model):
    """Model for tracking download orders - groups multiple macro downloads together"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='download_orders')
    downloaded_at = models.DateTimeField(auto_now_add=True)
    macros_count = models.PositiveIntegerField(default=0)  # Number of macros in this order
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        ordering = ['-downloaded_at']
        verbose_name = 'Download Order'
        verbose_name_plural = 'Download Orders'
    
    def __str__(self):
        return f"Order {self.id} by {self.user.username} - {self.macros_count} macro(s) on {self.downloaded_at.strftime('%Y-%m-%d %H:%M')}"
    
    def get_macros(self):
        """Get all macros in this order"""
        return self.order_items.select_related('macro', 'macro__user').all()


class DownloadOrderItem(models.Model):
    """Model for individual macros in a download order"""
    order = models.ForeignKey(DownloadOrder, on_delete=models.CASCADE, related_name='order_items')
    macro = models.ForeignKey(Macro, on_delete=models.SET_NULL, null=True, related_name='order_items')
    macro_name = models.CharField(max_length=500)  # Store name in case macro is deleted
    macro_author = models.CharField(max_length=150, blank=True)  # Store author username in case macro is deleted
    
    class Meta:
        ordering = ['macro_name']
        verbose_name = 'Order Item'
        verbose_name_plural = 'Order Items'
    
    def __str__(self):
        return f"{self.macro_name} in order {self.order.id}"


class MacroDownload(models.Model):
    """Model for tracking macro downloads"""
    macro = models.ForeignKey(Macro, on_delete=models.CASCADE, related_name='downloads')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    ip_address = models.GenericIPAddressField()
    downloaded_at = models.DateTimeField(auto_now_add=True)
    order = models.ForeignKey(DownloadOrder, on_delete=models.SET_NULL, null=True, blank=True, related_name='downloads')
    
    class Meta:
        ordering = ['-downloaded_at']
    
    def __str__(self):
        user_str = self.user.username if self.user else f"Anonymous ({self.ip_address})"
        return f"{user_str} downloaded {self.macro.name}"
