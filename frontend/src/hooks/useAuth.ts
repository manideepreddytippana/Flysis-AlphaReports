import { useEffect, useMemo } from "react";
import { useNavigate } from "react-router";
import { LOGIN_PATH } from "@/const";
import { useAuthContext } from "@/providers/auth";

type UseAuthOptions = {
  redirectOnUnauthenticated?: boolean;
  redirectPath?: string;
};

export function useAuth(options?: UseAuthOptions) {
  const { redirectOnUnauthenticated = false, redirectPath = LOGIN_PATH } =
    options ?? {};

  const navigate = useNavigate();
  const authContext = useAuthContext();

  useEffect(() => {
    if (
      redirectOnUnauthenticated &&
      !authContext.isLoading &&
      !authContext.user
    ) {
      const currentPath = window.location.pathname;
      if (currentPath !== redirectPath) {
        navigate(redirectPath);
      }
    }
  }, [
    redirectOnUnauthenticated,
    authContext.isLoading,
    authContext.user,
    navigate,
    redirectPath,
  ]);

  return useMemo(
    () => ({
      ...authContext,
    }),
    [authContext]
  );
}
