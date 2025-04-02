# analyzer_app/views.py
from django.shortcuts import render, redirect
from django.http import HttpResponse
from .analysis_utils import DataAnalyzer
import os
from django.conf import settings
from django.urls import reverse

def upload_and_analyze(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        # Salva o arquivo temporariamente
        file_path = os.path.join(settings.MEDIA_ROOT, uploaded_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Redireciona para a página de análise
        return redirect('analysis-main')
    
    return render(request, 'analyzer/upload_form.html')

def upload_and_analyze(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        
        # Cria o diretório se não existir
        os.makedirs(settings.UPLOAD_ROOT, exist_ok=True)
        
        # Salva o arquivo na pasta uploads
        file_path = os.path.join(settings.UPLOAD_ROOT, uploaded_file.name)
        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)
        
        # Redireciona para a página de análise com o nome do arquivo
        return redirect(reverse('analysis-view') + f'?file={uploaded_file.name}')
    
    return render(request, 'analyzer/upload_form.html')

def analyze_data(request):
    # Obtém o nome do arquivo da query string
    file_name = request.GET.get('file')
    if not file_name:
        return HttpResponse(reverse('upload-view'))
    
    # Caminho completo do arquivo
    file_path = os.path.join(settings.UPLOAD_ROOT, file_name)
    
    if not os.path.exists(file_path):
        return HttpResponse(reverse('upload-view'))
    
    try:
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        charts = analyzer.generate_visualizations()
        
        plotly_js = '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>' if charts else ''
        
        return render(request, 'analyzer/main_direct.html', {
            'plotly_js': plotly_js,
            'total_score_chart': charts.get('total_score', ''),
            'numeric_charts': [(k.replace('numeric_', ''), v) for k, v in charts.items() if k.startswith('numeric_')],
            'string_charts': [(k.replace('string_', ''), v) for k, v in charts.items() if k.startswith('string_')],
            'boolean_charts': [(k.replace('boolean_', ''), v) for k, v in charts.items() if k.startswith('boolean_')],
            'file_name': file_name,
        })
    except Exception as e:
        return render(request, 'analyzer/error.html', {
            'error_message': f"Erro ao analisar o arquivo: {str(e)}"
        })

def chart_view(request, chart_id):
    file_name = request.GET.get('file')
    if not file_name:
        return HttpResponse("<div>Arquivo não especificado</div>")
    
    file_path = os.path.join(settings.UPLOAD_ROOT, file_name)
    
    try:
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        charts = analyzer.generate_visualizations()
        
        return HttpResponse(charts.get(chart_id, "<div>Gráfico não encontrado</div>"))
    except Exception as e:
        return HttpResponse(f"<div>Erro ao carregar gráfico: {str(e)}</div>")

def chart_view(request, chart_id):
    """View que retorna um gráfico individual para ser exibido no iframe."""
    file_path = os.path.join(settings.MEDIA_ROOT, 'base_eletronicos_2.csv')  # Ajuste conforme necessário
    
    try:
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        charts = analyzer.generate_visualizations()
        
        return HttpResponse(charts.get(chart_id, "<div>Gráfico não encontrado</div>"))
    except Exception as e:
        return HttpResponse(f"<div>Erro ao carregar gráfico: {str(e)}</div>")