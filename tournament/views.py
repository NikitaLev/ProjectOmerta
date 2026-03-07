from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import UserRegistrationForm
from django.contrib.auth.decorators import login_required

@login_required
def profile(request):
    user = request.user
    context = {
        'user': user,
        'role_display': dict(user.ROLE_CHOICES).get(user.role, 'Игрок'),
        'is_host': user.role == 'host' and user.is_approved_host,
    }
    return render(request, 'tournament/profile.html', context)

def register(request):
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            username = form.cleaned_data.get('username')
            messages.success(request, f'Аккаунт для {username} успешно создан! Теперь вы можете войти.')
            return redirect('login')  # Перенаправляем на страницу входа
    else:
        form = UserRegistrationForm()
    
    return render(request, 'tournament/register.html', {'form': form})

def home(request):
    return render(request, 'tournament/home.html')