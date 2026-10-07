// Root providers, picked up by web/src/App.tsx (contract from UPS-001). Owner UPS-004.
import type { ReactNode } from "react";

import { AuthProvider } from "./auth";

export default function Providers({ children }: { children: ReactNode }) {
  return <AuthProvider>{children}</AuthProvider>;
}
