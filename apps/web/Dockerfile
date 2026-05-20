FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci

FROM node:22-alpine AS builder
WORKDIR /app
ARG NEXT_PUBLIC_API_BASE_URL
ARG NEXT_PUBLIC_AEGISDESK_MODE=evaluation
ARG NEXT_PUBLIC_SHOW_EVALUATION_TOOLS=true
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}
ENV NEXT_PUBLIC_AEGISDESK_MODE=${NEXT_PUBLIC_AEGISDESK_MODE}
ENV NEXT_PUBLIC_SHOW_EVALUATION_TOOLS=${NEXT_PUBLIC_SHOW_EVALUATION_TOOLS}
ENV NEXT_OUTPUT_MODE=standalone
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV PORT=3000
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
RUN chown -R node:node /app
EXPOSE 3000
USER node
CMD ["node", "server.js"]
