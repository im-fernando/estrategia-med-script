import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Estrategia Med - Questoes",
  description: "Banco de questoes de medicina com filtros avancados",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="pt-BR" className="antialiased">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
