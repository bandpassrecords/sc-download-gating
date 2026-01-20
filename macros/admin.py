from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import (
    CubaseVersion, Macro, 
    MacroVote, MacroFavorite, MacroCollection, MacroDownload,
    DownloadOrder, DownloadOrderItem
)


@admin.register(CubaseVersion)
class CubaseVersionAdmin(admin.ModelAdmin):
    list_display = ['version', 'major_version', 'created_at']
    list_filter = ['major_version', 'created_at']
    search_fields = ['version']
    ordering = ['-major_version']


class MacroVoteInline(admin.TabularInline):
    model = MacroVote
    extra = 0
    readonly_fields = ['user', 'rating', 'created_at']
    raw_id_fields = ['user']


@admin.register(Macro)
class MacroAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'get_user', 'is_private', 
        'get_average_rating', 'vote_count', 'download_count'
    ]
    list_filter = ['is_private', 'created_at', 'cubase_version']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = [
        'id', 'download_count', 'created_at', 'updated_at',
        'get_average_rating', 'vote_count'
    ]
    raw_id_fields = ['user']
    inlines = [MacroVoteInline]
    
    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'cubase_version', 'name', 'description')
        }),
        ('Settings', {
            'fields': ('key_binding', 'is_private')
        }),
        ('XML Snippets', {
            'fields': ('xml_snippet', 'reference_snippet'),
            'classes': ('collapse',),
            'description': 'XML snippets stored in database (not files)'
        }),
        ('Statistics', {
            'fields': ('get_average_rating', 'vote_count', 'download_count'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_user(self, obj):
        return obj.user.username
    get_user.short_description = 'User'
    get_user.admin_order_field = 'user__username'
    
    def get_average_rating(self, obj):
        avg = obj.average_rating
        if avg > 0:
            return f"{avg:.1f} ⭐"
        return "No ratings"
    get_average_rating.short_description = 'Avg Rating'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            'user', 'cubase_version'
        ).prefetch_related('votes')


@admin.register(MacroVote)
class MacroVoteAdmin(admin.ModelAdmin):
    list_display = ['macro', 'user', 'rating', 'created_at']
    list_filter = ['rating', 'created_at']
    search_fields = ['macro__name', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['macro', 'user']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('macro', 'user')


@admin.register(MacroFavorite)
class MacroFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'macro', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'macro__name']
    readonly_fields = ['created_at']
    raw_id_fields = ['user', 'macro']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user', 'macro')


@admin.register(MacroCollection)
class MacroCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'get_macro_count', 'is_private', 'created_at']
    list_filter = ['is_private', 'created_at']
    search_fields = ['name', 'user__username', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at']
    raw_id_fields = ['user']
    filter_horizontal = ['macros']
    
    fieldsets = (
        (None, {
            'fields': ('id', 'user', 'name', 'description')
        }),
        ('Settings', {
            'fields': ('is_private',)
        }),
        ('Macros', {
            'fields': ('macros',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_macro_count(self, obj):
        return obj.macros.count()
    get_macro_count.short_description = 'Macros Count'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(DownloadOrder)
class DownloadOrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'macros_count', 'downloaded_at', 'ip_address')
    list_filter = ('downloaded_at',)
    search_fields = ('user__username', 'id')
    readonly_fields = ('id', 'downloaded_at')
    date_hierarchy = 'downloaded_at'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(DownloadOrderItem)
class DownloadOrderItemAdmin(admin.ModelAdmin):
    list_display = ('order', 'macro_name', 'macro_author', 'macro')
    list_filter = ('order__downloaded_at',)
    search_fields = ('macro_name', 'macro_author', 'order__id')
    readonly_fields = ('order', 'macro', 'macro_name', 'macro_author')


@admin.register(MacroDownload)
class MacroDownloadAdmin(admin.ModelAdmin):
    list_display = ['macro', 'get_user_display', 'ip_address', 'order', 'downloaded_at']
    list_filter = ['downloaded_at', 'order']
    search_fields = ['macro__name', 'user__username', 'ip_address', 'order__id']
    readonly_fields = ['downloaded_at']
    raw_id_fields = ['macro', 'user', 'order']
    
    def get_user_display(self, obj):
        if obj.user:
            return obj.user.username
        return f"Anonymous ({obj.ip_address})"
    get_user_display.short_description = 'User'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('macro', 'user', 'order')


# Admin site customization
admin.site.site_header = "Cubase Macros Admin"
admin.site.site_title = "Cubase Macros Admin Portal"
admin.site.index_title = "Welcome to Cubase Macros Administration"
