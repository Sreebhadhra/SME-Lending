"""
URL configuration for govcred_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views


urlpatterns = [

    # Admin
    path('admin/', admin.site.urls),

    # Core Pages
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('about/', TemplateView.as_view(template_name='about.html'), name='about'),

    # Auth
    path('accounts/', include('django.contrib.auth.urls')),

    # ADD THIS LINE
    path('logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),

    # Apps
    path('dashboard/', include('governance.urls')),
    path('loans/', include('loans.urls')),
]

# Static + Media during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)


# Admin Branding (keep this at bottom)
admin.site.site_header = "GovCred Administration | XYZ Capital"
admin.site.site_title = "GovCred Admin Portal"
admin.site.index_title = "Governance-Linked Green Lending Platform"



