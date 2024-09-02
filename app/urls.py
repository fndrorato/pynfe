from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('api/v1/', include('nota_fiscal.urls')),    
    path('admin/', admin.site.urls),
]
