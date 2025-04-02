# analyzer_app/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('upload/', views.upload_and_analyze, name='upload_form'),
    path('analysis/', views.analyze_data, name='analysis-view'),
    path('chart/<str:chart_id>/', views.chart_view, name='chart-view'),
    path('', views.upload_and_analyze, name='upload_form_root'),  # Para mapear a raiz da app
]