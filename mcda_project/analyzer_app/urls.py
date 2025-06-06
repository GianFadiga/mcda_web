# analyzer_app/urls.py
from django.urls import path
from . import views
from .views import logout_view, home_redirect
from .views import user_logs_view, analysis_logs_view

urlpatterns = [
    path('upload/', views.upload_and_analyze, name='upload_form'),
    path('analysis/', views.analyze_data, name='analysis-view'),
    path('chart/<str:chart_id>/', views.chart_view, name='chart-view'),
    path('', home_redirect, name='home'),  # Alterado para a nova view de redirecionamento
    path('upload_form_root/', views.upload_and_analyze, name='upload_form_root'),
    path('user_logs/', user_logs_view, name='user_logs'),
    path('analysis_logs/', analysis_logs_view, name='analysis_logs'),
]