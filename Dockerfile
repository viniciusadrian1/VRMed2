# A chave OpenAI entra somente no contêiner em execução, nunca no build.
FROM node:22-bookworm-slim AS dependencias
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

FROM dependencias AS compilacao
ARG NEXT_PUBLIC_SITE_URL=https://2.28.109.190
ENV NEXT_TELEMETRY_DISABLED=1
ENV VRMED_STANDALONE=1
ENV NEXT_PUBLIC_SITE_URL=${NEXT_PUBLIC_SITE_URL}
COPY . .
RUN npm run lint && npm run verify:core && npm run build && npm run typecheck

FROM node:22-bookworm-slim AS execucao
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=3000
ENV HOSTNAME=0.0.0.0
RUN groupadd --gid 1001 vrmed && useradd --uid 1001 --gid 1001 --no-create-home vrmed
COPY --from=compilacao --chown=1001:1001 /app/.next/standalone ./
COPY --from=compilacao --chown=1001:1001 /app/.next/static ./.next/static
COPY --from=compilacao --chown=1001:1001 /app/public ./public
USER 1001:1001
EXPOSE 3000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD node -e "fetch('http://127.0.0.1:3000/').then(r=>{if(!r.ok)process.exit(1)}).catch(()=>process.exit(1))"
CMD ["node", "server.js"]
