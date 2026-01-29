FROM nginx:1.27-alpine

# Remove default configuration
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom configuration
COPY ./docker/production/nginx/nginx.conf /etc/nginx/conf.d/kore.conf

# Create directories for static and media files
RUN mkdir -p /static /media && \
    chmod -R 755 /static /media

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost/api/v1/health/ || exit 1

# Expose port
EXPOSE 80

# Run Nginx
CMD ["nginx", "-g", "daemon off;"]
