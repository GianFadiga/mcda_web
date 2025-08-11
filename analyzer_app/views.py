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
    
# SUBSTITUA A VIEW analysis_creator_view
@login_required
def analysis_creator_view(request):
    """
    View para a página de criação de análises (planilhas).
    """
    CriterionFormSet = formset_factory(CriterionForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = CriterionFormSet(request.POST, prefix='criteria')
        if formset.is_valid():
            
            total_weight = sum(form.cleaned_data.get('weight', 0) for form in formset.cleaned_data if not form.get('DELETE', False))
            
            if total_weight > 1.0:
                messages.error(request, f"A soma dos pesos dos critérios ({total_weight:.2f}) não pode ultrapassar 1.0.")
                return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

            valid_forms_data = [form for form in formset.cleaned_data if not form.get('DELETE', False)]
            
            if not valid_forms_data:
                 messages.error(request, "Você precisa definir pelo menos um critério para a análise.")
                 return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

            csv_content, error_message = _generate_csv_string_from_formset(valid_forms_data)
            
            if error_message:
                messages.error(request, error_message)
                return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

            action = request.POST.get('action')

            if action == 'download':
                response = HttpResponse(csv_content, content_type='text/csv')
                response['Content-Disposition'] = 'attachment; filename="analise_customizada.csv"'
                return response

            elif action == 'analyze':
                # <<<< INÍCIO DO CÓDIGO QUE ESTAVA FALTANDO >>>>
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
                        'file_name': 'Análise Customizada'
                    }
                    return render(request, 'analyzer/main.html', context)
                
                except Exception as e:
                    messages.error(request, f"Erro durante a análise: {e}")
                
                finally:
                    if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                # <<<< FIM DO CÓDIGO QUE ESTAVA FALTANDO >>>>

    # Se GET ou se o formset for inválido, renderiza a página de criação
    formset = CriterionFormSet(prefix='criteria')
    return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})


# SUBSTITUA A FUNÇÃO _generate_csv_string_from_formset
def _generate_csv_string_from_formset(cleaned_data):
    """
    Pega os dados limpos de um formset e retorna o conteúdo de um CSV como string.
    """
    try:
        # Inicializa as linhas do CSV
        header = ['Modelo']
        pesos = ['PESO']
        tipos = ['TIPO']
        funcoes = ['FUNCAO']
        bom_values = ['BOM']
        neutro_values = ['NEUTRO']

        for form_data in cleaned_data:
            if not form_data: continue
            
            name = form_data.get('name')
            header.append(name)
            
            # Usa o valor numérico direto do formulário
            pesos.append(form_data.get('weight', 0))
            
            type_map = {'string': 'string', 'number': 'number', 'boolean': 'boolean'}
            tipos.append(type_map.get(form_data.get('criterion_type'), 'string'))

            if form_data.get('criterion_type') == 'number':
                funcoes.append(form_data.get('proportionality'))
                bom_values.append(form_data.get('good_value'))
                neutro_values.append(form_data.get('neutral_value'))
            else:
                funcoes.append('')
                bom_values.append('')
                neutro_values.append('')
        
        output = io.StringIO()
        writer = csv.writer(output)
        
        writer.writerow(header)
        writer.writerow(pesos)
        writer.writerow(tipos)
        writer.writerow(funcoes)
        writer.writerow(bom_values)
        writer.writerow(neutro_values)

        return output.getvalue(), None

    except Exception as e:
        return None, f"Erro ao gerar o CSV a partir dos dados do formulário: {e}"
