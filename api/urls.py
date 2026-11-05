from django.urls import path
from . import views

urlpatterns = [
    # Example test endpoint
    path('test/', views.test_api, name='test_api'),
]