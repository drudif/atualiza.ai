import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Creative AI Feed",
  description: "Curadoria semanal de conteúdo avançado sobre IA generativa e criativa",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <head>
        <link rel="preconnect" href="https://api.fontshare.com" />
        <link
          rel="stylesheet"
          href="https://api.fontshare.com/v2/css?f[]=satoshi@900,700,500&display=swap"
        />
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Courier+Prime:ital,wght@0,400;0,700;1,400&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-paper text-ink min-h-screen">{children}</body>
    </html>
  );
}
