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
    path('creator/', views.analysis_creator_view, name='analysis_creator'),
    path('password_reset/', views.password_reset_request, name='password_reset_request'),
    path('tutorial/', views.tutorial_view, name='tutorial'),
    path('analysis/<int:analysis_id>/download_csv/', views.download_analysis_csv, name='download_csv'),
]