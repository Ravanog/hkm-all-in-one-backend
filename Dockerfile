FROM node:18-slim
RUN apt-get update && apt-get install -y python3 python3-pip && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY package*.json ./
COPY requirements.txt ./
RUN npm install
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt
COPY . .
EXPOSE 8080
CMD ["npm", "start"]
