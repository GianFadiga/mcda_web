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
# Corrigindo os imports para usar os nomes corretos dos seus formulários
from .forms import (
    CustomUserCreationForm,
    EmailAuthenticationForm,
    UserUpdateForm,
)
from .models import Analysis, AnalysisLog, UserLog
from django.template.exceptions import TemplateDoesNotExist
User = get_user_model()


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
        # Redireciona para a view que vai de fato analisar e mostrar os dados
        return redirect(reverse('analysis-view') + f'?analysis_id={analysis.id}')

    # Esta view agora só mostra o formulário de upload
    return render(request, 'analyzer/main.html')

@login_required
def analyze_data(request):
    analysis_id = request.GET.get('analysis_id')
    if not analysis_id:
        return redirect('upload_form_root') # Use o nome correto da sua URL de upload

    analysis = get_object_or_404(Analysis, id=analysis_id)
    file_path = os.path.join(settings.UPLOAD_ROOT, analysis.name)

    if not os.path.exists(file_path):
        messages.error(request, "Arquivo da análise não encontrado.")
        return redirect('upload_form_root') # Use o nome correto da sua URL de upload

    try:
        analyzer = DataAnalyzer(file_path)
        analyzer.load_and_prepare_data()
        analyzer.calculate_scores()
        
        # Gera as visualizações (gráficos)
        charts = analyzer.generate_visualizations()
        
        # <<-- INÍCIO DA NOVA LÓGICA DO PÓDIO -->>
        # Pega os detalhes dos 3 melhores para o pódio
        podium_data = analyzer.get_podium_details()
        # <<-- FIM DA NOVA LÓGICA DO PÓDIO -->>

        # Prepara o contexto para enviar ao template
        context = {
            'visualizations': charts,
            'podium_data': podium_data, # <<-- NOVO DADO PARA O TEMPLATE
            'has_results': True, # Flag para o template saber que há resultados
            'file_name': analysis.name,
            'analysis': analysis,
        }
        
        # Renderiza a página principal de resultados
        return render(request, 'analyzer/main.html', context)

    except Exception as e:
        # Lida com possíveis erros durante a análise
        messages.error(request, f"Ocorreu um erro ao processar seu arquivo: {e}")
        return redirect('upload_form_root') # Use o nome correto da sua URL de upload


# ===============================================================
#  RESTANTE DAS SUAS VIEWS ORIGINAIS (SEM ALTERAÇÕES)
# ===============================================================

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

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            response = redirect('login')
            response.set_cookie('show_register_toast', 'true', max_age=5, path='/')
            return response
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
    return redirect('upload_form_root') # Use o nome correto da sua URL de upload

def login_view(request):
    if request.user.is_authenticated:
        response = redirect('upload_form_root') 
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

# ... (suas outras views como user_logs_view, profile_view, etc. continuam aqui)
@login_required
def user_logs_view(request):
    logs = UserLog.objects.order_by('-timestamp')
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'analyzer/user_logs.html', {'page_obj': page_obj})

@login_required
def analysis_logs_view(request):
    logs = AnalysisLog.objects.order_by('-timestamp')
    paginator = Paginator(logs, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'analyzer/analysis_logs.html', {'page_obj': page_obj})

@login_required
def user_analyses_view(request):
    user = request.user
    analyses = Analysis.objects.filter(user=user)
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
    
# ADICIONE A NOVA VIEW ABAIXO
@login_required
def analysis_creator_view(request):
    """
    View para a página de criação de análises (planilhas).
    """
    # Cria uma 'fábrica' de formsets a partir do nosso CriterionForm
    # extra=1 significa que sempre começaremos com 1 formulário em branco
    CriterionFormSet = formset_factory(CriterionForm, extra=1)

    if request.method == 'POST':
        # Se o formulário for enviado, preenche o formset com os dados
        formset = CriterionFormSet(request.POST, prefix='criteria')
        if formset.is_valid():
            # Por enquanto, vamos apenas confirmar que recebemos os dados
            print("Formset válido!")
            print(formset.cleaned_data)
            
            # NO PRÓXIMO PASSO, A LÓGICA DE ANALISAR/BAIXAR ENTRARÁ AQUI
            return HttpResponse("Formulário enviado com sucesso! Verifique o console do servidor.")
        # Se o formset for inválido, ele será re-renderizado com os erros
    else:
        # Se for a primeira vez na página (GET), cria um formset em branco
        formset = CriterionFormSet(prefix='criteria')

    context = {
        'criteria_formset': formset
    }
    return render(request, 'analyzer/analysis_creator.html', context)