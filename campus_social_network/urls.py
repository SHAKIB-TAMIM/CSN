from django.contrib import admin
from django.urls import path,include
from django.contrib.auth import views as auth_views
from core import views as user_views
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path
import debug_toolbar
from core.views import CustomConfirmEmailView

urlpatterns = [
    path('__debug__/', include(debug_toolbar.urls)), 
    path('admin/', admin.site.urls),
    path('accounts/confirm-email/<str:key>/', CustomConfirmEmailView.as_view(), name='account_confirm_email'),
    path('', include('core.urls')),
]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

