from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from ..forms import ProfileForm
from ..models import Profile


def home(request):
    return render(request, 'home.html')



@login_required
def view_Profile(request):
    return render(request, 'Profile.html')


@login_required
def edit_profile(request):
    profile, created = Profile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            return redirect('Profile')
    else:
        form = ProfileForm(instance=profile)

    return render(request, 'profile_edit.html', {'form': form})


