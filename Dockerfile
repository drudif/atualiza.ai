# Site read-only (Next.js) para Railway.
# O Railway detecta este Dockerfile na raiz e o usa — não precisa de Root
# Directory nem detecção automática. O scraper roda localmente; o banco vai
# embutido em app/data/feed.db (gerado por `pnpm bundle-db` antes do push).

FROM node:22-bookworm-slim

WORKDIR /app

RUN npm install -g pnpm@11.1.1

# 1. Dependências primeiro (camada cacheável)
COPY app/package.json app/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

# 2. Código do app + banco embutido (app/data/feed.db)
COPY app/ ./

# 3. Build de produção
RUN pnpm build

ENV NODE_ENV=production
EXPOSE 3000

# Railway injeta PORT; bind em 0.0.0.0 para aceitar tráfego externo
CMD ["sh", "-c", "pnpm start -- -H 0.0.0.0 -p ${PORT:-3000}"]
