document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('registerForm');
  const submitBtn = document.getElementById('submitBtn');

  // Password strength indicator
  const passwordInput = document.getElementById('password');
  const strengthIndicator = document.getElementById('passwordStrength');
  
  passwordInput.addEventListener('input', (e) => {
    const password = e.target.value;
    let strength = 0;
    
    if (password.length >= 6) strength++;
    if (password.length >= 10) strength++;
    if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength++;
    if (/\d/.test(password)) strength++;
    if (/[^a-zA-Z\d]/.test(password)) strength++;

    const strengths = ['Weak', 'Fair', 'Good', 'Strong', 'Very Strong'];
    const colors = ['#dc3545', '#ffc107', '#17a2b8', '#28a745', '#28a745'];
    
    strengthIndicator.textContent = `Password Strength: ${strengths[strength]}`;
    strengthIndicator.style.color = colors[strength];
  });

  // Form submission
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    const formData = {
      name: document.getElementById('name').value.trim(),
      email: document.getElementById('email').value.trim(),
      password: document.getElementById('password').value,
      department: document.getElementById('department')?.value,
      phoneNumber: document.getElementById('phoneNumber')?.value
    };

    // Disable submit button
    submitBtn.disabled = true;
    submitBtn.textContent = 'Registering...';

    try {
      const result = await authManager.register(formData);
      
      showNotification(result.message || 'Registration successful!', 'success');
      
      setTimeout(() => {
        window.location.href = '/dashboard.html';
      }, 1500);
    } catch (error) {
      showNotification(error.message || 'Registration failed', 'error');
      submitBtn.disabled = false;
      submitBtn.textContent = 'Register';
    }
  });
});

function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  setTimeout(() => {
    notification.classList.add('show');
  }, 10);

  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}
