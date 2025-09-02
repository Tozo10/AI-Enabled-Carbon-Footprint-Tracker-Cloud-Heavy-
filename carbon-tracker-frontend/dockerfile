# ---- Stage 1: Build the Vite App ----
# Use an official Node.js image
FROM node:20-alpine AS builder

# Set the working directory
WORKDIR /app

# Copy package.json and package-lock.json (or yarn.lock)
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy the rest of the application files
COPY . .

# Build the project for production
RUN npm run build


# ---- Stage 2: Serve the App with Nginx ----
# Use a lightweight Nginx image
FROM nginx:stable-alpine

# Copy the built assets from the 'builder' stage
# Note: Vite builds to a 'dist' folder by default
COPY --from=builder /app/dist /usr/share/nginx/html

# Expose port 80
EXPOSE 80

# Start Nginx when the container launches
CMD ["nginx", "-g", "daemon off;"]