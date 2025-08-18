# analyzer_app\forms.py
from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import UserCreationForm
from django.core.exceptions import ValidationError
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator

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

# SUBSTITUA A CLASSE CriterionForm INTEIRA POR ESTA
class CriterionForm(forms.Form):
    TYPE_CHOICES = [
        ('number', 'Numérico'),
        ('string', 'Texto'),
        ('boolean', 'Sim/Não'),
    ]
    PROPORTIONALITY_CHOICES = [
        ('proportional', 'Quanto mais, melhor'),
        ('i_proportional', 'Quanto menos, melhor'),
    ]

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
        label="Preferência (p/ números)",
        choices=PROPORTIONALITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    # CAMPO DE PESO ALTERADO AQUI
    weight = forms.FloatField(
        label="Importância (Peso)",
        min_value=0.01,
        max_value=1.0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Ex: 0.25',
            'step': '0.01'  # Define o incremento do campo no HTML
        }),
        validators=[MinValueValidator(0.01), MaxValueValidator(1.0)] # Validação no backend
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
    
    string_values = forms.CharField(widget=forms.HiddenInput(), required=False)