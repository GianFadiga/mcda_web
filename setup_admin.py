import os
import django
from django.core.exceptions import ImproperlyConfigured

# --- Configuração Importante ---
# Substitua 'seu_projeto.settings' pelo caminho correto 
# para o seu arquivo settings.py. 
# (Ex: 'mcda.settings' ou 'backend.settings')
#
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mcda_project.settings') 
# -------------------------------

try:
    django.setup()
except ImproperlyConfigured:
    print("Erro: Não foi possível carregar as configurações do Django.")
    print(f"Verifique se 'DJANGO_SETTINGS_MODULE' está configurado corretamente ('{os.environ.get('DJANGO_SETTINGS_MODULE')}')")
    exit(1)

from django.contrib.auth import get_user_model

# Pega o modelo de Usuário (seja o padrão ou um customizado)
User = get_user_model()

# Pega os dados das variáveis de ambiente
username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if not all([username, email, password]):
    print('Variáveis de ambiente (DJANGO_SUPERUSER_...) não configuradas. Admin não será criado.')
else:
    # Verifica se o usuário já existe
    if not User.objects.filter(username=username).exists():
        try:
            print(f"Criando superusuário: {username}")
            User.objects.create_superuser(username=username, email=email, password=password)
            print("Superusuário criado com sucesso.")
        except Exception as e:
            print(f"Erro ao criar superusuário: {e}")
    else:
        print(f"Superusuário '{username}' já existe. Nenhuma ação necessária.")