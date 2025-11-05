# Personal Media Server

This project is a personal media server designed to simulate 24/7 TV channels using an on-demand streaming model.

## Running the Project

To run the project, you will need Docker and Docker Compose installed.

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    ```
2.  **Navigate to the project directory:**
    ```bash
    cd <project-directory>
    ```
3.  **Run the services:**
    ```bash
    docker-compose up -d
    ```

This will start all the services in the background. You can view the logs for a specific service using the following command:

```bash
docker-compose logs -f <service-name>
```

To stop the services, run:

```bash
docker-compose down

## Documentation

For detailed instructions on how to set up, use, and deploy the project, please refer to the following guides:

*   **[GUIDE.md](GUIDE.md):** A comprehensive guide to setting up the project locally, understanding its features, and day-to-day usage.
*   **[DEPLOY_GUIDE.md](DEPLOY_GUIDE.md):** Step-by-step instructions for deploying the project to Render's free tier.
```
