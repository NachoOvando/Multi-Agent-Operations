import type { Metadata } from "next";
import "./globals.css";

// TODO: layout real (nav por dominio, selector de operador) una vez que el
// backend (apps/api) tenga endpoints reales para autenticar/rutear.
export const metadata: Metadata = {
  title: "Agentes operativos",
  description: "Compras / Almacén / Planificación",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="es">
      <body>{children}</body>
    </html>
  );
}
