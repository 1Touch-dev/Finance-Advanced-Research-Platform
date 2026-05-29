FROM node:18

WORKDIR /app

COPY package.json ./
RUN npm install

COPY public ./public
COPY src ./src

ENV HOST=0.0.0.0
ENV PORT=3002
ENV BROWSER=none
ENV WATCHPACK_POLLING=true
ENV CHOKIDAR_USEPOLLING=true

EXPOSE 3002
CMD ["npm", "start"]
