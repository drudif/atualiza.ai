import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Não roda ESLint no build (evita falha por dep de lint). Type-check segue ativo.
  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
