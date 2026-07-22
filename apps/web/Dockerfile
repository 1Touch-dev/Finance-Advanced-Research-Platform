FROM node:18-alpine

WORKDIR /app

COPY package.json ./
RUN npm install

COPY pages ./pages
COPY src ./src
COPY lib ./lib
COPY tailwind.config.js postcss.config.js ./

ENV NEXT_PUBLIC_API_URL=http://localhost:3001
EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
