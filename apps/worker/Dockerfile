FROM node:18-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY src ./src

ENV REDIS_URL=redis://redis:6379

CMD ["npm", "start"]
