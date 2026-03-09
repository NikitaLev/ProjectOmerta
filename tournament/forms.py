from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import User
from .models import HostApplication
from .models import Tournament
from django.utils import timezone

class UserRegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'})
    )
    player_nickname = forms.CharField(
        required=False,
        label='Никнейм в мафии',
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Как к вам обращаться в игре'})
    )
    password1 = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )
    password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Повторите пароль'})
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'player_nickname', 'password1', 'password2')
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.player_nickname = self.cleaned_data['player_nickname']
        user.role = 'player'
        if commit:
            user.save()
        return user
    
class HostApplicationForm(forms.ModelForm):
    class Meta:
        model = HostApplication
        fields = ['full_name', 'email', 'phone', 'experience', 'reason']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Иванов Иван Иванович'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'your@email.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+7 (999) 123-45-67'}),
            'experience': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Расскажите о своем опыте ведения турниров...'}),
            'reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Почему вы хотите стать ведущим?'}),
        }

class TournamentCreateForm(forms.ModelForm):
    class Meta:
        model = Tournament
        fields = ['name', 'description', 'start_date', 'max_players', 'total_games', 'rules']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Название турнира'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Описание турнира (необязательно)'
            }),
            'start_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local',
                'value': timezone.now().strftime('%Y-%m-%dT%H:%M')
            }),
            'max_players': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 2,
                'max': 20,
                'value': 10
            }),
            'total_games': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20,
                'value': 10
            }),
            'rules': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'name': 'Название турнира',
            'description': 'Описание',
            'start_date': 'Дата и время начала',
            'max_players': 'Максимальное количество игроков',
            'total_games': 'Количество игр в турнире',
            'rules': 'Правила турнира',
        }
