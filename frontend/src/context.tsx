import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { get, onUnauthorized, post, setCsrf } from "./api";
import type { Reference, SchoolClass, User } from "./types";

interface AppState {
  user: User | null;
  loading: boolean;
  reference: Reference | null;
  classes: SchoolClass[];
  classId: string | null;
  setClassId: (id: string | null) => void;
  setUser: (u: User | null) => void;
  reloadReference: () => Promise<void>;
  reloadClasses: () => Promise<SchoolClass[]>;
  logout: () => Promise<void>;
  toast: (message: string, kind?: "ok" | "error") => void;
  toasts: { id: number; message: string; kind: "ok" | "error" }[];
}

const Ctx = createContext<AppState | null>(null);

function storedClassId(): string | null {
  try {
    return localStorage.getItem("lp_class");
  } catch {
    return null;
  }
}

export function AppProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [reference, setReference] = useState<Reference | null>(null);
  const [classes, setClasses] = useState<SchoolClass[]>([]);
  const [classId, setClassIdState] = useState<string | null>(storedClassId());
  const [toasts, setToasts] = useState<{ id: number; message: string; kind: "ok" | "error" }[]>([]);

  const toast = useCallback((message: string, kind: "ok" | "error" = "ok") => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, message, kind }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), kind === "error" ? 7000 : 3500);
  }, []);

  const setClassId = useCallback((id: string | null) => {
    setClassIdState(id);
    try {
      if (id) localStorage.setItem("lp_class", id);
      else localStorage.removeItem("lp_class");
    } catch {
      /* Speicher nicht verfügbar */
    }
  }, []);

  const reloadReference = useCallback(async () => {
    setReference(await get<Reference>("/reference"));
  }, []);

  const reloadClasses = useCallback(async () => {
    const res = await get<{ items: SchoolClass[] }>("/classes");
    setClasses(res.items);
    setClassIdState((current) => {
      const valid = current && res.items.some((c) => c.id === current) ? current : res.items[0]?.id ?? null;
      try {
        if (valid) localStorage.setItem("lp_class", valid);
      } catch {
        /* ignorieren */
      }
      return valid;
    });
    return res.items;
  }, []);

  useEffect(() => {
    get<{ user: User; csrf_token: string }>("/auth/me")
      .then((r) => {
        setCsrf(r.csrf_token);
        setUser(r.user);
      })
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
    return onUnauthorized(() => setUser(null));
  }, []);

  useEffect(() => {
    if (user && !user.must_change_password) {
      reloadReference().catch(() => undefined);
      reloadClasses().catch(() => undefined);
    }
  }, [user, reloadReference, reloadClasses]);

  const logout = useCallback(async () => {
    try {
      await post("/auth/logout");
    } catch {
      /* Sitzung evtl. schon abgelaufen */
    }
    setCsrf(null);
    setUser(null);
    setClasses([]);
    setReference(null);
  }, []);

  return (
    <Ctx.Provider value={{ user, loading, reference, classes, classId, setClassId, setUser, reloadReference, reloadClasses, logout, toast, toasts }}>
      {children}
    </Ctx.Provider>
  );
}

export function useApp(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("AppProvider fehlt");
  return ctx;
}
