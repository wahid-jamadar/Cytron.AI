import useAuthStore from './authStore';

const BASE_URL = window.location.origin;

interface FetchOptions extends RequestInit {
  json?: any;
}

export async function apiFetch(endpoint: string, options: FetchOptions = {}): Promise<any> {
  const { accessToken, refreshToken, login, logout } = useAuthStore.getState();

  const headers = new Headers(options.headers || {});
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }

  if (options.json) {
    headers.set('Content-Type', 'application/json');
    options.body = JSON.stringify(options.json);
  }

  const url = endpoint.startsWith('http') ? endpoint : `${BASE_URL}${endpoint}`;
  
  try {
    let response = await fetch(url, { ...options, headers });

    // Handle 401 Unauthorized: Attempt token refresh
    if (response.status === 401 && refreshToken) {
      const refreshResp = await fetch(`${BASE_URL}/api/auth/refresh`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: refreshToken })
      });

      if (refreshResp.ok) {
        const refreshData = await refreshResp.json();
        const { user } = useAuthStore.getState();
        if (user) {
          login(user, refreshData.access_token, refreshData.refresh_token);
          // Retry original request with new access token
          headers.set('Authorization', `Bearer ${refreshData.access_token}`);
          response = await fetch(url, { ...options, headers });
        }
      } else {
        // Refresh token failed -> Force logout
        logout();
        window.location.href = '/#/login';
        throw new Error('Session expired');
      }
    }

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.detail || `Request failed: ${response.status}`);
    }

    return response.json().catch(() => ({}));
  } catch (error) {
    console.error('API Error:', error);
    throw error;
  }
}
