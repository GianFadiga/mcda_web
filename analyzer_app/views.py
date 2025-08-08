# analyzer_app/views.py
from django.shortcuts import render, redirect
from django.core.files.storage import FileSystemStorage
from django.contrib.auth.decorators import login_required
from .forms import UploadFileForm, UserRegistrationForm
from .analysis_utils import DataAnalyzer  # Importamos a classe principal
import os

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')
    else:
        form = UserRegistrationForm()
    return render(request, 'analyzer/register.html', {'form': form})

@login_required
def main_view(request):
    return render(request, 'analyzer/main.html')

@login_required
def upload_file(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = request.FILES['file']
            fs = FileSystemStorage()
            # Garante um nome de arquivo único para evitar conflitos
            filename = fs.save(uploaded_file.name, uploaded_file)
            file_path = fs.path(filename)
            
            try:
                # --- INÍCIO DA LÓGICA DE ANÁLISE ---
                analyzer = DataAnalyzer(file_path)
                analyzer.load_and_prepare_data()
                analyzer.calculate_scores()
                
                # Gera as visualizações
                visualizations = analyzer.generate_visualizations()
                
                # Gera os dados do pódio (TOP 3)
                podium_data = analyzer.get_podium_details() # << NOVA FUNÇÃO

                # Prepara o contexto para o template
                context = {
                    'form': form,
                    'visualizations': visualizations,
                    'podium_data': podium_data, # << NOVO CONTEXTO
                    'has_results': True
                }
                # --- FIM DA LÓGICA DE ANÁLISE ---

            except Exception as e:
                # Em caso de erro na análise, exibe uma mensagem
                context = {
                    'form': form,
                    'error_message': f"Ocorreu um erro ao analisar o arquivo: {e}",
                    'has_results': False
                }
            finally:
                # Deleta o arquivo após a análise
                if os.path.exists(file_path):
                    os.remove(file_path)

            return render(request, 'analyzer/main.html', context)
    else:
        form = UploadFileForm()
    return render(request, 'analyzer/main.html', {'form': form, 'has_results': False})