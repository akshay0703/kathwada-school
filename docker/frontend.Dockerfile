FROM node:20-alpine AS base
ARG APP_DIR
WORKDIR /app

COPY package.json package-lock.json* ./
COPY apps/${APP_DIR}/package.json ./apps/${APP_DIR}/package.json
COPY packages ./packages
RUN npm install

COPY . .

WORKDIR /app/apps/${APP_DIR}
RUN npm run build

EXPOSE 3000
CMD ["npm", "run", "start"]
