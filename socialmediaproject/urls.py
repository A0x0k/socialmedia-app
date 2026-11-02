"""
URL configuration for socialmediaproject project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from posts.views import landing_page


def health_check(request):
    """Health check endpoint for container orchestration."""
    health = {'status': 'ok', 'checks': {}}

    # Database check
    try:
        connection.ensure_connection()
        health['checks']['database'] = 'ok'
    except Exception as e:
        health['checks']['database'] = str(e)
        health['status'] = 'degraded'

    # Cache check
    try:
        cache.ping() if hasattr(cache, 'ping') else cache.get('health_check')
        health['checks']['cache'] = 'ok'
    except Exception as e:
        health['checks']['cache'] = str(e)
        health['status'] = 'degraded'

    status_code = 200 if health['status'] == 'ok' else 503
    return JsonResponse(health, status=status_code)

urlpatterns = [
     path('i18n/', include('django.conf.urls.i18n')),
     path('admin/', admin.site.urls),
     path('', landing_page, name='landing'),
     path('health/', health_check, name='health_check'),
     path('feed/', include('posts.urls')),
     path('users/', include('users.urls')),
     path('notifications/', include('notifications.urls')),
     path('messages/', include('direct_messages.urls')),
     path('reports/', include('reports.urls')),
     path('search/', include('searchapp.urls')),
     # Password reset URLs
     path('password-reset/', auth_views.PasswordResetView.as_view(template_name='registration/password_reset.html'), name='password_reset'),
     path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='registration/password_reset_done.html'), name='password_reset_done'),
     path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='registration/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='registration/password_reset_complete.html'), name='password_reset_complete'),
    # API documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


# Custom error handlers
handler404 = 'handlers.handler404'
handler500 = 'handlers.handler500'
handler403 = 'handlers.handler403'
handler400 = 'handlers.handler400'
