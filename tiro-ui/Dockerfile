FROM node:22-alpine
WORKDIR /app
COPY . .
# For v1, serve static files — actual AFFiNE build requires its custom bundler.
# This placeholder serves the public directory for development purposes.
RUN npm install -g serve
EXPOSE 3000
CMD ["serve", "-s", "packages/frontend/core/public", "-l", "3000"]
