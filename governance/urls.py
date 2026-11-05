from django.urls import path
from . import views

app_name = 'governance'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('profile/', views.governance_profile, name='profile'),
    path('calculate-score/', views.calculate_score, name='calculate_score'),
]