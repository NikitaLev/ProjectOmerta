from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from ..models import HostApplication
from ..forms import HostApplicationForm

@login_required
def apply_host(request):
    # Проверяем, не подавал ли уже заявку
    existing_application = HostApplication.objects.filter(user=request.user).first()
    
    if existing_application:
        if existing_application.status == 'pending':
            messages.info(request, 'Вы уже подали заявку. Ожидайте рассмотрения.')
        elif existing_application.status == 'approved':
            messages.success(request, 'Вы уже являетесь ведущим!')
        elif existing_application.status == 'rejected':
            messages.warning(request, 'Ваша заявка была отклонена. Вы можете подать новую.')
            existing_application.delete()
    
    if request.method == 'POST':
        form = HostApplicationForm(request.POST)
        if form.is_valid():
            application = form.save(commit=False)
            application.user = request.user
            application.save()
            messages.success(request, 'Заявка успешно отправлена! Ожидайте рассмотрения.')
            return redirect('profile')
    else:
        form = HostApplicationForm()
    
    return render(request, 'tournament/apply_host.html', {'form': form})
