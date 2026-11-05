"""
URL patterns for cam_generator app.
"""

from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index_view'),
    path('preview/', views.preview_cam_view, name='preview_cam_view'),
    path('download/', views.download_cam_view, name='download_cam_view'),
    path('preset/<str:preset_id>/', views.preset_view, name='preset_view'),
]

