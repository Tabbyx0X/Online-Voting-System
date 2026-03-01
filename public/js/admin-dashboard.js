document.addEventListener('DOMContentLoaded', async () => {
  if (!authManager.isAuthenticated()) {
    window.location.href = '/login.html';
    return;
  }

  try {
    const user = await authManager.getCurrentUser();
    
    if (user.data.role !== 'admin') {
      window.location.href = '/dashboard.html';
      return;
    }

    // Load system-wide statistics
    await loadSystemStats();
    await loadAllUsers();
  } catch (error) {
    console.error('Error loading admin dashboard:', error);
    showNotification('Error loading dashboard', 'error');
  }
});

async function loadSystemStats() {
  try {
    const usersResponse = await fetch('/api/users?limit=1000', {
      headers: authManager.getAuthHeaders()
    });
    const usersResult = await usersResponse.json();
    
    if (usersResult.success) {
      const totalUsers = usersResult.pagination.total;
      const totalStudents = usersResult.data.filter(u => u.role === 'student').length;
      const totalTeachers = usersResult.data.filter(u => u.role === 'teacher').length;
      
      document.getElementById('totalUsers').textContent = totalUsers;
      document.getElementById('totalStudents').textContent = totalStudents;
      document.getElementById('totalTeachers').textContent = totalTeachers;
    }
  } catch (error) {
    console.error('Error loading stats:', error);
  }
}

async function loadAllUsers() {
  try {
    const response = await fetch('/api/users?page=1&limit=50', {
      headers: authManager.getAuthHeaders()
    });
    
    const result = await response.json();
    
    if (result.success) {
      const usersContainer = document.getElementById('recentUsers');
      usersContainer.innerHTML = result.data.slice(0, 10).map(user => `
        <div class="user-item">
          <span>${user.name} (${user.role})</span>
          <span>${user.email}</span>
        </div>
      `).join('');
    }
  } catch (error) {
    console.error('Error loading users:', error);
  }
}

function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  document.body.appendChild(notification);
  setTimeout(() => notification.classList.add('show'), 10);
  setTimeout(() => {
    notification.classList.remove('show');
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}
