# Use the official NGINX base image
FROM nginx:alpine

# Set working directory
WORKDIR /usr/share/nginx/html

# Remove default NGINX content
RUN rm -rf ./*

# Copy static website files into the container
COPY . .

# Expose port 80
EXPOSE 80

# Start NGINX server
CMD ["nginx", "-g", "daemon off;"]

