FROM node:22-alpine

WORKDIR /app

COPY . .

COPY package*.json ./

RUN npm install

EXPOSE 3000

CMD ["npm", "run", "dev"]
