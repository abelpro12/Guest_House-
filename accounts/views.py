from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .forms import LoginForm, CustomUserCreationForm
from .models import CustomUser
from properties.models import PropertyStaff

def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard:index')
        
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            user = authenticate(request, username=username, password=password)
            if user:
                if not user.is_active:
                    messages.error(request, 'Account is deactivated.')
                else:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                    return redirect('dashboard:index')
            else:
                messages.error(request, 'Invalid username or password.')
    else:
        form = LoginForm()
        
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.info(request, 'You have been logged out.')
    return redirect('accounts:login')

@login_required
def profile_view(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.phone_number = request.POST.get('phone_number', user.phone_number)
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html')

@login_required
def change_password_view(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def investors_list(request):
    """Lists all registered Property Investors for Super Admin."""
    if not request.user.is_admin:
        messages.error(request, "Permission denied. Super Admin only.")
        return redirect('dashboard:index')

    investors = CustomUser.objects.filter(role='investor').prefetch_related('owned_properties')
    return render(request, 'accounts/investor_list.html', {'investors': investors})


@login_required
def create_investor(request):
    """Allows Super Admin to register a new Property Investor (Guest House Owner)."""
    if not request.user.is_admin:
        messages.error(request, "Permission denied. Super Admin only.")
        return redirect('dashboard:index')

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        email = request.POST.get('email', '')
        first_name = request.POST.get('first_name', '')
        last_name = request.POST.get('last_name', '')
        phone_number = request.POST.get('phone_number', '')

        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, f"Username '{username}' already exists.")
            return redirect('accounts:investors')

        investor = CustomUser.objects.create_user(
            username=username,
            password=password,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone_number,
            role='investor'
        )

        messages.success(request, f"Successfully created Investor Account '{username}' ({investor.get_full_name() or username})!")
        return redirect('accounts:investors')

    return redirect('accounts:investors')


@login_required
def edit_user_account(request, user_id):
    """Allows Super Admin (or Investor for staff) to modify user profile details, roles, and reset passwords."""
    target_user = get_object_or_404(CustomUser, id=user_id)

    # Permission check: Super Admin or Investor editing staff
    if not request.user.is_admin:
        if request.user.is_investor and target_user.role == 'receptionist':
            has_permission = PropertyStaff.objects.filter(property__investor=request.user, user=target_user).exists()
            if not has_permission:
                messages.error(request, "Permission denied.")
                return redirect('dashboard:index')
        else:
            messages.error(request, "Permission denied.")
            return redirect('dashboard:index')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'update_profile':
            target_user.first_name = request.POST.get('first_name', target_user.first_name)
            target_user.last_name = request.POST.get('last_name', target_user.last_name)
            target_user.email = request.POST.get('email', target_user.email)
            target_user.phone_number = request.POST.get('phone_number', target_user.phone_number)
            
            if request.user.is_admin and request.POST.get('role'):
                target_user.role = request.POST.get('role')

            target_user.save()
            messages.success(request, f"Updated profile details for {target_user.username}.")

        elif action == 'reset_password':
            new_password = request.POST.get('new_password')
            if new_password:
                target_user.set_password(new_password)
                target_user.save()
                messages.success(request, f"Password successfully reset for user '{target_user.username}'.")
            else:
                messages.error(request, "New password cannot be blank.")

        elif action == 'toggle_active':
            target_user.is_active = not target_user.is_active
            target_user.save()
            status_text = "Activated" if target_user.is_active else "Deactivated"
            messages.success(request, f"Account for {target_user.username} is now {status_text}.")

        return redirect('accounts:edit_user', user_id=target_user.id)

    return render(request, 'accounts/edit_user.html', {'target_user': target_user})
