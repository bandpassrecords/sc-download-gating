from django.urls import path
from . import views

app_name = 'macros'

urlpatterns = [
    # Macro browsing
    path('', views.macro_list, name='macro_list'),
    path('macro/<uuid:macro_id>/', views.macro_detail, name='macro_detail'),
    path('share/<str:secret_token>/', views.macro_detail_by_secret, name='macro_detail_by_secret'),
    path('popular/', views.popular_macros, name='popular_macros'),
    
    # Key Commands file management
    path('upload/', views.upload_keycommands, name='upload_keycommands'),
    path('upload/select-macros/', views.select_macros_upload, name='select_macros_upload'),
    path('upload/save-macros/', views.save_selected_macros, name='save_selected_macros'),
    # Macro management
    path('edit/<uuid:macro_id>/', views.edit_macro, name='edit_macro'),
    
    # Cart/Staging area
    path('cart/', views.view_cart, name='view_cart'),
    path('cart/add/<uuid:macro_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/remove/<uuid:macro_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/clear/', views.clear_cart, name='clear_cart'),
    path('cart/upload-and-download/', views.upload_and_download, name='upload_and_download'),
    
    # Order history
    path('orders/', views.order_history, name='order_history'),
    path('orders/<uuid:order_id>/add-to-cart/', views.add_order_to_cart, name='add_order_to_cart'),
    
    # AJAX endpoints
    path('favorite/<uuid:macro_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('toggle-visibility/<uuid:macro_id>/', views.toggle_visibility, name='toggle_visibility'),
    path('generate-secret-link/<uuid:macro_id>/', views.generate_secret_link, name='generate_secret_link'),
] 