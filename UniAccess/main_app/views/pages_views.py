from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from ..forms import CustomUserCreationForm


def home(request):
    return render(request, 'home.html')

def signup_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # or your home page
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})


def Profile(request):
    return render(request, 'home.html')


