FROM node:20-slim

WORKDIR /app

# Install basic dependencies
COPY package.json package-lock.json* ./
RUN npm ci --only=production

# Copy app source
COPY . .

# Set production environment
ENV NODE_ENV=production
ENV PORT=3000

EXPOSE 3000

CMD ["node", "src/server.js"]
