FROM node:20-alpine AS base
WORKDIR /app

FROM base AS deps
RUN apk add --no-cache libc6-compat openssl
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install --no-audit --no-fund

FROM base AS build
RUN apk add --no-cache libc6-compat openssl
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ ./
COPY prisma ./prisma
RUN npx prisma generate --schema=./prisma/schema.prisma --generator=client
RUN npx next build

FROM base AS runner
ENV NODE_ENV=production
RUN apk add --no-cache libc6-compat openssl
COPY --from=build /app/.next ./.next
COPY --from=build /app/public ./public
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.js ./next.config.js
COPY --from=build /app/prisma ./prisma
EXPOSE 3000
CMD ["npm", "run", "start"]
