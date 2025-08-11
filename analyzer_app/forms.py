# analyzer_app\forms.py
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError

User = get_user_model()

class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'autofocus': True,
            'class': 'form-control',
            'placeholder': 'exemplo@email.com',
        })
    )
    
    password = forms.CharField(
        label="Senha",
        strip=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Digite sua senha',
            'id': 'password-input'
        })
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(username=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError("Email ou senha inválidos.")
        return self.cleaned_data

    def get_user(self):
        return getattr(self, 'user_cache', None)


class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        label='Email',
        widget=forms.EmailInput(attrs={
            'placeholder': 'seu@email.com'
        }),
        help_text="Um email válido para recuperação de conta"
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'Escolha um nome de usuário'}),
        }
        help_texts = {
            'username': '150 caracteres ou menos. Letras, números e @/./+/-/_ apenas.',
        }

    def clean_email(self):
        email = self.cleaned_data.get('email').lower()
        if User.objects.filter(email=email).exists():
            raise ValidationError("Este email já está cadastrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email'].lower()
        if commit:
            user.save()
        return user
    
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Travar o campo de email (tanto visual quanto funcionalmente)
        self.fields['email'].disabled = True

    def clean_username(self):
        username = self.cleaned_data.get('username')
        qs = User.objects.filter(username=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este nome de usuário já está em uso.")
        return username

# ADICIONE A NOVA CLASSE DE FORMULÁRIO ABAIXO
class CriterionForm(forms.Form):
    # Dicionários de escolhas para os dropdowns
    TYPE_CHOICES = [
        ('number', 'Numérico'),
        ('string', 'Texto'),
        ('boolean', 'Sim/Não'),
    ]
    PROPORTIONALITY_CHOICES = [
        ('proportional', 'Quanto mais, melhor'),
        ('i_proportional', 'Quanto menos, melhor'),
    ]
    WEIGHT_CHOICES = [(i, f'{i} Estrela{"s" if i > 1 else ""}') for i in range(1, 6)] # 1 a 5 estrelas

    # Campos do formulário
    name = forms.CharField(
        label="Nome do Critério",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: Preço (R$)'})
    )
    criterion_type = forms.ChoiceField(
        label="Tipo",
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    proportionality = forms.ChoiceField(
        label="Preferência (para números)",
        choices=PROPORTIONALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False # Opcional, pois só se aplica a números
    )
    weight = forms.ChoiceField(
        label="Importância",
        choices=WEIGHT_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    good_value = forms.CharField(
        label="Valor Bom",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 60000'}),
        required=False
    )
    neutral_value = forms.CharField(
        label="Valor Neutro",
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ex: 85000'}),
        required=False
    )
