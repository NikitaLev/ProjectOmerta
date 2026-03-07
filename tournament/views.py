from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegistrationForm


def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт для {username} успешно создан! Теперь вы можете войти.')
            return redirect('home')  # вместо 'login' # пока редирект на главную, потом сделаем страницу входа
    else:
        form = UserRegistrationForm()
    
    return render(request, 'tournament/register.html', {'form': form})

def home(request):
    return render(request, 'tournament/home.html')