# mcda_project\analyzer_app\views.py
import os
import json

from django.forms import formset_factory
from django.http import HttpResponse 
from .forms import CriterionForm 
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import (
    get_user_model,
    login as auth_login,
    logout,
    update_session_auth_hash,
)
import io      # <<< ADICIONE ESTA LINHA
import csv     # <<< ADICIONE ESTA LINHA
import tempfile
import re
from django.conf import settings
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
    
@login_required
def analysis_creator_view(request):
    """
    View para a página de criação de análises, com lógica de validação corrigida.
    """
    CriterionFormSet = formset_factory(CriterionForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = CriterionFormSet(request.POST, prefix='criteria')

        # A validação do formset agora funciona como um guarda inicial
        if not formset.is_valid():
            messages.error(request, "Houve um erro nos critérios definidos. Por favor, verifique os campos.")
            return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

        # Se o formset for válido, extraímos os dados e continuamos
        valid_criteria = [form for form in formset.cleaned_data if form and not form.get('DELETE', False)]
        
        total_weight = sum(crit.get('weight', 0) for crit in valid_criteria)
        if total_weight > 1.0:
            messages.error(request, f"A soma dos pesos ({total_weight:.2f}) não pode ultrapassar 1.0.")
            # Re-renderiza o formset com os dados preenchidos para o usuário corrigir
            return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': CriterionFormSet(request.POST, prefix='criteria')})

        if not valid_criteria:
             messages.error(request, "Defina pelo menos um critério para a análise.")
             return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

        # Parse dos dados das Alternativas (Etapa 2)
        alternatives_data = _parse_alternatives_from_post(request.POST)
        
        # Geração do CSV Completo
        analysis_name = request.POST.get('analysis_name', 'analise')
        csv_content, error_message = _generate_complete_csv_string(valid_criteria, alternatives_data)
        
        if error_message:
            messages.error(request, error_message)
            return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

        # Execução da Ação (Download ou Análise)
        action = request.POST.get('action')
        if action == 'download':
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{analysis_name}.csv"'
            return response

        elif action == 'analyze':
            try:
                with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.csv', encoding='utf-8') as temp_file:
                    temp_file.write(csv_content)
                    temp_file_path = temp_file.name
                
                analyzer = DataAnalyzer(temp_file_path)
                analyzer.load_and_prepare_data()
                analyzer.calculate_scores()
                
                podium_data = analyzer.get_podium_details()
                visualizations = analyzer.generate_visualizations()
                
                context = {
                    'podium_data': podium_data,
                    'visualizations': visualizations,
                    'has_results': True,
                    'file_name': analysis_name
                }
                return render(request, 'analyzer/main.html', context)
            except Exception as e:
                messages.error(request, f"Erro durante a análise: {e}")
            finally:
                if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                    os.remove(temp_file_path)
    
    # Se GET, renderiza a página de criação
    formset = CriterionFormSet(prefix='criteria')
    return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})


def _parse_alternatives_from_post(post_data):
    """
    Lê os dados brutos do request.POST e organiza os dados das alternativas.
    """
    alternatives = {}
    pattern = re.compile(r'alternative-(\d+)-(.+)')
    
    for key, value in post_data.items():
        match = pattern.match(key)
        if match:
            index, field = match.groups()
            if index not in alternatives:
                alternatives[index] = {}
            alternatives[index][field] = value
            
    return sorted(alternatives.values(), key=lambda x: x.get('name', ''))


def _generate_complete_csv_string(criteria_data, alternatives_data):
    """
    Gera o CSV completo com base nos critérios e nas alternativas.
    """
    try:
        header = ['Modelo'] + [c.get('name') for c in criteria_data]
        pesos = ['PESO'] + [c.get('weight', 0) for c in criteria_data]
        tipos = ['TIPO'] + [{'string': 'string', 'number': 'number', 'boolean': 'boolean'}.get(c.get('criterion_type')) for c in criteria_data]
        funcoes = ['FUNCAO'] + [c.get('proportionality') if c.get('criterion_type') == 'number' else '' for c in criteria_data]
        bom_values = ['BOM'] + [c.get('good_value') if c.get('criterion_type') == 'number' else '' for c in criteria_data]
        neutro_values = ['NEUTRO'] + [c.get('neutral_value') if c.get('criterion_type') == 'number' else '' for c in criteria_data]
        
        alternative_rows = []
        for alt_data in alternatives_data:
            row = [alt_data.get('name', '')]
            # Itera na ordem original dos critérios para preencher os valores
            for i in range(len(criteria_data)):
                field_name = f'crit-{i}'
                row.append(alt_data.get(field_name, ''))
            alternative_rows.append(row)

        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(header)
        writer.writerow(pesos)
        writer.writerow(tipos)
        writer.writerow(funcoes)
        writer.writerow(bom_values)
        writer.writerow(neutro_values)
        writer.writerows(alternative_rows)

        return output.getvalue(), None

    except Exception as e:
        return None, f"Erro ao gerar o CSV: {e}"