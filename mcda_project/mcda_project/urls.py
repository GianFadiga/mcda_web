# mcda_project/urls.py
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('analyzer_app/', include('analyzer_app.urls')),
    path('', include('analyzer_app.urls')),  # Para acessar a raiz
]