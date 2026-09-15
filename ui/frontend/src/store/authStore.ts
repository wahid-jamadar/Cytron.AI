import { create } from 'zustand';

export interface UserPreferences {
  preferred_provider: string;
  preferred_language: string;
  ui_theme: string;
  timezone: string;
  avatar_url: string | null;
}

export interface UserProfile {
  id: number;
  email: string;
  first_name: string;
  last_name: string;
  roles: string[];
  preferences?: UserPreferences;
}

interface AuthState {
  user: UserProfile | null;
  accessToken: string | null;
  refreshToken: string | null;
  isImpersonating: boolean;
  adminAccessToken: string | null;
  adminUser: UserProfile | null;
  
  login: (user: UserProfile, access: string, refresh: string) => void;
  logout: () => void;
  updatePreferences: (prefs: Partial<UserPreferences>) => void;
  startImpersonation: (user: UserProfile, targetAccess: string) => void;
  stopImpersonation: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: JSON.parse(localStorage.getItem('eto_user') || 'null'),
  accessToken: localStorage.getItem('eto_access') || null,
  refreshToken: localStorage.getItem('eto_refresh') || null,
  isImpersonating: localStorage.getItem('eto_is_impersonating') === 'true',
  adminAccessToken: localStorage.getItem('eto_admin_access') || null,
  adminUser: JSON.parse(localStorage.getItem('eto_admin_user') || 'null'),

  login: (user, access, refresh) => {
    localStorage.setItem('eto_user', JSON.stringify(user));
    localStorage.setItem('eto_access', access);
    localStorage.setItem('eto_refresh', refresh);
    set({ user, accessToken: access, refreshToken: refresh });
  },

  logout: () => {
    localStorage.removeItem('eto_user');
    localStorage.removeItem('eto_access');
    localStorage.removeItem('eto_refresh');
    localStorage.removeItem('eto_is_impersonating');
    localStorage.removeItem('eto_admin_access');
    localStorage.removeItem('eto_admin_user');
    set({
      user: null,
      accessToken: null,
      refreshToken: null,
      isImpersonating: false,
      adminAccessToken: null,
      adminUser: null
    });
  },

  updatePreferences: (prefs) => {
    set((state) => {
      if (!state.user) return state;
      const updatedUser = {
        ...state.user,
        preferences: {
          ...state.user.preferences,
          ...prefs
        } as UserPreferences
      };
      localStorage.setItem('eto_user', JSON.stringify(updatedUser));
      return { user: updatedUser };
    });
  },

  startImpersonation: (targetUser, targetAccess) => {
    set((state) => {
      // Save original admin details first if not already impersonating
      const adminAccess = state.accessToken;
      const adminUserObj = state.user;
      
      localStorage.setItem('eto_admin_access', adminAccess || '');
      localStorage.setItem('eto_admin_user', JSON.stringify(adminUserObj));
      localStorage.setItem('eto_is_impersonating', 'true');
      localStorage.setItem('eto_user', JSON.stringify(targetUser));
      localStorage.setItem('eto_access', targetAccess);
      
      return {
        user: targetUser,
        accessToken: targetAccess,
        isImpersonating: true,
        adminAccessToken: adminAccess,
        adminUser: adminUserObj
      };
    });
  },

  stopImpersonation: () => {
    set((state) => {
      const adminAccess = state.adminAccessToken;
      const adminUserObj = state.adminUser;
      
      localStorage.removeItem('eto_admin_access');
      localStorage.removeItem('eto_admin_user');
      localStorage.removeItem('eto_is_impersonating');
      
      if (adminUserObj && adminAccess) {
        localStorage.setItem('eto_user', JSON.stringify(adminUserObj));
        localStorage.setItem('eto_access', adminAccess);
        return {
          user: adminUserObj,
          accessToken: adminAccess,
          isImpersonating: false,
          adminAccessToken: null,
          adminUser: null
        };
      }
      
      // Fallback if no admin data
      localStorage.removeItem('eto_user');
      localStorage.removeItem('eto_access');
      return {
        user: null,
        accessToken: null,
        isImpersonating: false,
        adminAccessToken: null,
        adminUser: null
      };
    });
  }
}));
export default useAuthStore;
