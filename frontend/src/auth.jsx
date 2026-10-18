import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import * as api from "./api.js";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  // undefined = still checking, null = signed out, object = signed in
  const [user, setUser] = useState(undefined);

  useEffect(() => {
    api.setUnauthorizedHandler(() => setUser(null));
    api
      .getMe()
      .then(setUser)
      .catch(() => setUser(null));
  }, []);

  const signOut = useCallback(async () => {
    try {
      await api.logout();
    } catch {
      /* ignore: we clear local state either way */
    }
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, signOut }), [user, signOut]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
