// Root providers, picked up by web/src/App.tsx (contract from UPS-001). Owner UPS-021.
import type { ReactNode } from "react";

import { AuthProvider } from "./auth";
import { NotificationsProvider } from "./notifications";

export default function Providers({ children }: { children: ReactNode }) {
  return (
    <AuthProvider>
      <NotificationsProvider>{children}</NotificationsProvider>
    </AuthProvider>
  );
}
