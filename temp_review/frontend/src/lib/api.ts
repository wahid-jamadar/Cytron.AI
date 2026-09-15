[
  "import axios from 'axios';\n\nconst api = axios.create({\n  baseURL: import.meta.env.VITE_API_URL,\n  headers: {\n    'Content-Type': 'application/json'\n  }\n});\n\napi.interceptors.request.use((config) => {\n  const token = localStorage.getItem('token');\n  if (token) {\n    config.headers['Authorization'] = `Bearer ${token}`;\n  }\n  return config;\n});\n\nexport default api;"
]