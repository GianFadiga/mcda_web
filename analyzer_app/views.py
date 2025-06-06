# mcda_project\analyzer_app\views.py
import os
import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login as auth_login,
    logout,
    update_session_auth_hash,
)
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
    resolve_url,
)
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify

from .analysis_utils import DataAnalyzer
from .forms import (
    CustomUserCreationForm,
    EmailAuthenticationForm,
    UserUpdateForm,
)
from .models import Analysis, AnalysisLog, UserLog
from django.template.exceptions import TemplateDoesNotExist
User = get_user_model()


from .forms import CustomUserCreationForm, EmailAuthenticationForm

@login_required
def upload_and_analyze(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']

        os.makedirs(settings.UPLOAD_ROOT, exist_ok=True)

        username = slugify(request.user.username)
        filename = slugify(os.path.splitext(uploaded_file.name)[0])
        ext = os.path.splitext(uploaded_file.name)[1]
        new_filename = f"{username}-{filename}{ext}"
        file_path = os.path.join(settings.UPLOAD_ROOT, new_filename)

        with open(file_path, 'wb+') as destination:
            for chunk in uploaded_file.chunks():
                destination.write(chunk)

        # Cria o registro Analysis
        analysis = Analysis.objects.create(
            name=new_filename,
            description=f"Análise do arquivo {new_filename} enviada pelo usuário {username}",
            user=request.user
        )

        AnalysisLog.objects.create(
            action='INSERT',
            analysis=analysis,
            old_data='',
            new_data=json.dumps({
                'filename': new_filename,
                'user': username,
                'timestamp': timezone.now().isoformat()
            })
        )

        return redirect(reverse('analysis-view') + f'?analysis_id={analysis.id}')

    return render(request, 'analyzer/upload_form.html')

@login_required
def analyze_data(request):
    analysis_id = request.GET.get('analysis_id')
    if not analysis_id:
        return redirect('upload_form_root')

    analysis = get_object_or_404(Analysis, id=analysis_id)

    file_path = os.path.join(settings.UPLOAD_ROOT, analysis.name)

    if not os.path.exists(file_path):
        messages.error(request, "Arquivo da análise não encontrado.")
        return redirect('upload_form_root')

    try:
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        charts = analyzer.generate_visualizations()

        current_timestamp = timezone.now()
        plotly_js = '<script src="https://cdn.plot.ly/plotly-latest.min.js"></script>' if charts else ''

        return render(request, 'analyzer/main_direct.html', {
            'plotly_js': plotly_js,
            'total_score_chart': charts.get('total_score', ''),
            'numeric_charts': [(k.replace('numeric_', ''), v) for k, v in charts.items() if k.startswith('numeric_')],
            'string_charts': [(k.replace('string_', ''), v) for k, v in charts.items() if k.startswith('string_')],
            'boolean_charts': [(k.replace('boolean_', ''), v) for k, v in charts.items() if k.startswith('boolean_')],
            'file_name': analysis.name,
            'title_color': 'white',
            'current_timestamp': current_timestamp,
            'analysis': analysis,
        })
    except TemplateDoesNotExist:
        response = redirect('upload_form_root')
        response.set_cookie('show_analysis_error_toast', 'true', max_age=5, path='/')
        return response
    except Exception as e:
        response = redirect('upload_form_root')
        response.set_cookie('show_analysis_error_toast', 'true', max_age=5, path='/')
        return response

@login_required
def chart_view(request, chart_id):
    analysis_id = request.GET.get('analysis_id')
    if not analysis_id:
        return HttpResponse("<div>Análise não especificada</div>")
    
    analysis = get_object_or_404(Analysis, id=analysis_id)
    file_path = os.path.join(settings.UPLOAD_ROOT, analysis.name)
    
    try:
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        charts = analyzer.generate_visualizations()
        
        return HttpResponse(charts.get(chart_id, "<div>Gráfico não encontrado</div>"))
    except Exception as e:
        return HttpResponse(f"<div>Erro ao carregar gráfico: {str(e)}</div>")

# Sistema de Login

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            response = redirect('login')
            response.set_cookie('show_register_toast', 'true', max_age=5, path='/')
            return response
        else:
            pass
    else:
        form = CustomUserCreationForm()
    return render(request, 'analyzer/register.html', {'form': form})

def logout_view(request):
    logout(request)
    response = redirect('login')
    response.set_cookie('show_logout_toast', 'true', max_age=5)
    return response

def home_redirect(request):
    if not request.user.is_authenticated:
        return redirect('login')
    return redirect('upload_form_root')

def login_view(request):
    if request.user.is_authenticated:
        response = redirect('upload_form_root')  # Redirecione para a home ou dashboard
        response.set_cookie('already_logged_in_toast', 'true', max_age=5, path='/')
        return response

    if request.method == 'POST':
        form = EmailAuthenticationForm(request.POST, request=request)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            next_url = request.POST.get('next')
            response = redirect(resolve_url(next_url or 'upload_form_root'))
            response.set_cookie('show_login_toast', 'true', max_age=5, path='/')
            return response
    else:
        form = EmailAuthenticationForm(request=request)
    
    return render(request, 'analyzer/login.html', {
        'form': form,
        'next': request.GET.get('next', '')
    })

def user_logs_view(request):
    logs = UserLog.objects.order_by('-timestamp')
    paginator = Paginator(logs, 20)  # 20 logs por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'analyzer/user_logs.html', {'page_obj': page_obj})

def analysis_logs_view(request):
    logs = AnalysisLog.objects.order_by('-timestamp')
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'analyzer/analysis_logs.html', {'page_obj': page_obj})

@login_required
def user_analyses_view(request):
    user = request.user
    analyses = Analysis.objects.filter(user=user)  # ajuste caso tenha outro campo de relação
    return render(request, 'analyzer/user_analyses.html', {'analyses': analyses})

@login_required
def profile_view(request):
    user = request.user
    user_form = UserUpdateForm(request.POST or None, instance=user)

    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = PasswordChangeForm(user, request.POST)
    else:
        password_form = PasswordChangeForm(user)

    if request.method == 'POST':
        if user_form.is_valid():
            if 'change_password' in request.POST:
                if password_form.is_valid():
                    user_form.save()
                    user = password_form.save()
                    update_session_auth_hash(request, user)
                    response = redirect('profile')
                    response.set_cookie('show_profile_password_toast', 'true', max_age=5, path='/')
                    return response
            else:
                user_form.save()
                response = redirect('profile')
                response.set_cookie('show_profile_updated_toast', 'true', max_age=5, path='/')
                return response

    return render(request, 'analyzer/profile.html', {
        'user_form': user_form,
        'password_form': password_form,
        'change_password': 'change_password' in request.POST,
    })