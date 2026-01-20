from django.urls import path

from . import views

app_name = "gates"

urlpatterns = [
    path("", views.browse, name="browse"),
    path("my/", views.my_tracks, name="my_tracks"),
    path("new/", views.create_track, name="create_track"),
    path("t/<str:public_id>/edit/", views.edit_track, name="edit_track"),
    path("t/<str:public_id>/", views.gate, name="gate"),
    path("t/<str:public_id>/download/", views.download, name="download"),
    path("t/<str:public_id>/soundcloud/connect/", views.soundcloud_connect, name="soundcloud_connect"),
    path("t/<str:public_id>/soundcloud/like/", views.soundcloud_like, name="soundcloud_like"),
    path("t/<str:public_id>/soundcloud/follow/", views.soundcloud_follow, name="soundcloud_follow"),
    path("t/<str:public_id>/soundcloud/comment/", views.soundcloud_comment, name="soundcloud_comment"),
    path("soundcloud/callback/", views.soundcloud_callback, name="soundcloud_callback"),
]

