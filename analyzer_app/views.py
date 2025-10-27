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
from django.utils.text import slugify
from django.urls import reverse
from django.core.mail import send_mail
import string
import random

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
    View para a página de criação de análises, com lógica completa para salvar no BD.
    """
    CriterionFormSet = formset_factory(CriterionForm, extra=1, can_delete=True)

    if request.method == 'POST':
        formset = CriterionFormSet(request.POST, prefix='criteria')

        if not formset.is_valid():
            messages.error(request, "Houve um erro nos critérios definidos. Por favor, verifique os campos.")
            return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

        valid_criteria = [form for form in formset.cleaned_data if form and not form.get('DELETE', False)]
        total_weight = sum(crit.get('weight', 0) for crit in valid_criteria)

        if total_weight > 1.0:
            messages.error(request, f"A soma dos pesos ({total_weight:.2f}) não pode ultrapassar 1.0.")
            return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': CriterionFormSet(request.POST, prefix='criteria')})

        if not valid_criteria:
             messages.error(request, "Defina pelo menos um critério para a análise.")
             return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

        alternatives_data = _parse_alternatives_from_post(request.POST)
        analysis_name = request.POST.get('analysis_name', 'analise-sem-nome')
        csv_content, error_message = _generate_complete_csv_string(valid_criteria, alternatives_data)
        
        if error_message:
            messages.error(request, error_message)
            return render(request, 'analyzer/analysis_creator.html', {'criteria_formset': formset})

        action = request.POST.get('action')
        if action == 'download':
            response = HttpResponse(csv_content, content_type='text/csv')
            response['Content-Disposition'] = f'attachment; filename="{slugify(analysis_name)}.csv"'
            return response

        elif action == 'analyze':
            # --- INÍCIO DA NOVA LÓGICA DE SALVAMENTO ---
            try:
                # 1. Cria o nome do arquivo, assim como na sua view de upload original
                username = slugify(request.user.username)
                filename_slug = slugify(analysis_name)
                new_filename = f"{username}-{filename_slug}.csv"
                file_path = os.path.join(settings.UPLOAD_ROOT, new_filename)

                # Garante que o diretório de upload exista
                os.makedirs(settings.UPLOAD_ROOT, exist_ok=True)

                # 2. Salva o conteúdo do CSV no arquivo físico
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)

                # 3. Cria o registro da Análise no banco de dados
                analysis = Analysis.objects.create(
                    name=new_filename,
                    description=f"Análise '{analysis_name}' criada pelo formulário web.",
                    user=request.user
                )

                # (Opcional, mas recomendado) Cria um log da análise
                AnalysisLog.objects.create(
                    action='INSERT',
                    analysis=analysis,
                    new_data=json.dumps({'name': new_filename, 'user': username})
                )

                # 4. Redireciona para a view de análise, como no fluxo original
                return redirect(reverse('analysis-view') + f'?analysis_id={analysis.id}')

            except Exception as e:
                messages.error(request, f"Ocorreu um erro ao salvar ou processar a análise: {e}")
            # --- FIM DA NOVA LÓGICA DE SALVAMENTO ---
            
    # Se GET, ou se o formset for inválido e não tratado acima, renderiza a página de criação
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
    Gera o CSV completo, incluindo a lógica para valores de string customizados.
    """
    try:
        # Mapa de desejabilidade para pontos (escala de 0 a 1)
        desirability_map = {
            'super_desejavel': 1.0,
            'desejavel': 0.75,
            'aceitavel': 0.5,
            'nao_desejavel': 0.1,
        }

        string_points_map = {}
        header = ['Modelo']
        pesos, tipos, funcoes, bom_values, neutro_values = ['PESO'], ['TIPO'], ['FUNCAO'], ['BOM'], ['NEUTRO']

        # Mapeia o índice original do formulário para o índice da coluna no CSV
        crit_col_map = {}
        current_col_idx = 1

        for i, crit in enumerate(criteria_data):
            crit_name = crit.get('name')
            crit_type = crit.get('criterion_type')
            
            crit_col_map[i] = {'name': crit_name, 'type': crit_type}

            header.append(crit_name)
            pesos.append(crit.get('weight', 0))
            tipos.append({'string': 'string', 'number': 'number', 'boolean': 'boolean'}.get(crit_type))
            
            if crit_type == 'number':
                funcoes.append(crit.get('proportionality'))
                bom_values.append(crit.get('good_value'))
                neutro_values.append(crit.get('neutral_value'))
            elif crit_type == 'string':
                header.append(f"Pontos_{crit_name}")
                pesos.append('')
                tipos.append('pts_string')
                funcoes.append('')
                bom_values.append('')
                neutro_values.append('')
                
                string_values_json = crit.get('string_values')
                if string_values_json:
                    string_values_list = json.loads(string_values_json)
                    string_points_map[i] = {item['value']: desirability_map.get(item['level'], 0) for item in string_values_list}
            else: # boolean
                funcoes.append('boolean')
                bom_values.append('')
                neutro_values.append('')

        # Monta as linhas das alternativas
        alternative_rows = []
        for alt_data in alternatives_data:
            row = [alt_data.get('name', '')]
            for i in range(len(criteria_data)):
                field_name = f'crit-{i}'
                value = alt_data.get(field_name, '')
                row.append(value)
                
                if criteria_data[i].get('criterion_type') == 'string':
                    points = string_points_map.get(i, {}).get(value, 0)
                    row.append(points)
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
    
def password_reset_request(request):
    if request.method == 'POST':
        email = request.POST.get('email')

        # 1. Encontra o usuário pelo e-mail (ignorando maiúsculas/minúsculas)
        user = User.objects.filter(email__iexact=email).first()

        # 2. Se o usuário existir...
        if user:
            try:
                # 3. Gera uma senha temporária (ex: "aB7kPqZ9rX")
                temp_password = ''.join(random.choices(string.ascii_letters + string.digits, k=10))

                # 4. Define a nova senha (o Django vai fazer o hash automaticamente)
                user.set_password(temp_password)
                user.save()

                # 5. Prepara o e-mail
                subject = '[MCDA] Sua nova senha de acesso'
                message = (
                    f"Olá, {user.first_name or user.username},\n\n"
                    f"Recebemos uma solicitação de redefinição de senha para sua conta.\n\n"
                    f"Sua nova senha temporária é: {temp_password}\n\n"
                    f"Por favor, use esta senha para logar. Recomendamos que você "
                    f"a altere imediatamente na sua página de Perfil.\n\n"
                    f"Atenciosamente,\n"
                    f"Equipe do Projeto MCDA"
                )

                # O e-mail do remetente (que configuramos no settings.py)
                from_email = settings.DEFAULT_FROM_EMAIL

                # 6. DISPARA O E-MAIL (Usando o SendGrid)
                send_mail(subject, message, from_email, [user.email])

                messages.success(request, 'Se o e-mail estiver cadastrado, uma nova senha foi enviada.')

            except Exception as e:
                # Se o e-mail falhar, não quebre o app. Apenas avise no log do Render.
                print(f"ERRO AO ENVIAR E-MAIL DE RESET: {e}")
                messages.error(request, 'Houve um erro ao processar sua solicitação. Tente novamente mais tarde.')

        else:
            # Se o e-mail NÃO existir, mostramos a *mesma* mensagem de sucesso.
            # Isso é uma prática de segurança para não revelar quais e-mails estão cadastrados.
            messages.success(request, 'Se o e-mail estiver cadastrado, uma nova senha foi enviada.')

        # 7. Sempre redireciona para o login
        return redirect('login')

    # Se for um GET (primeira vez na página), apenas mostre o formulário
    return render(request, 'analyzer/password_reset_form.html')

@login_required
def tutorial_view(request):
    """
    Renderiza a página estática de tutorial.
    """
    # (Opcional) Você pode preparar o link do arquivo aqui
    context = {
        'download_file_name': 'arquivo_base.csv' # O nome do seu arquivo
    }
    return render(request, 'analyzer/tutorial.html', context)