import { createContext, useContext, ReactNode, useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/api/client';

type User = {
  id: number;
  name: string;
  email: string;
  role: string;
  avatar?: string;
};

type AuthContextType = {
  user: User | undefined;
  isLoading: boolean;
  error: Error | null;
  logout: () => void;
  refetch: () => void;
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient();

  const { data: user, isLoading, error, refetch } = useQuery({
    queryKey: ['auth', 'me'],
    queryFn: () => api.auth.me(),
    staleTime: 1000 * 60 * 5,
    retry: false,
  });

  const logoutMutation = useMutation({
    mutationFn: () => api.auth.logout(),
    onSuccess: () => {
      queryClient.setQueryData(['auth', 'me'], null);
      queryClient.invalidateQueries();
    },
  });

  const logout = () => {
    logoutMutation.mutate();
  };

  return (
    <AuthContext.Provider value={{ user, isLoading, error, logout, refetch }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuthContext() {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuthContext must be used within an AuthProvider');
  }
  return context;
}
