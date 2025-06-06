# mcda_project/urls.py
from django.contrib import admin
from django.urls import path, include
from analyzer_app import views as analyzer_views  # Importe suas views
from analyzer_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Rotas de autenticação - view personalizada
    path('login/', analyzer_views.login_view, name='login'),
    path('logout/', analyzer_views.logout_view, name='logout'),
    path('register/', analyzer_views.register, name='register'),
    path('logs/', include('analyzer_app.urls')),  # Inclui rotas de logs
    path('profile/', views.profile_view, name='profile'),
    path('my-analyses/', views.user_analyses_view, name='user_analyses'),
    
    # Inclui rotas da sua aplicação
    path('', include('analyzer_app.urls')),
]