from django.urls import path
from . import views

app_name = 'loans'

urlpatterns = [
    # Loan user side
    path('', views.loan_list, name='list'),
    path('apply/', views.loan_apply, name='apply'),
    path('success/<int:loan_id>/', views.loan_success, name='success'),
    path('<int:pk>/', views.loan_detail, name='detail'),
]
