# Setup Guide

## Prerequisites
* Docker
* Node.js
* Python

## Step-by-Step Setup
1. Clone the repository: `git clone https://github.com/your-username/hospital_management_system.git`
2. Change into the project directory: `cd hospital_management_system`
3. Create a new file for environment variables: `cp .env.example .env`
4. Update the environment variables as needed
5. Build the Docker images: `docker-compose build`
6. Start the application: `docker-compose up -d`

## Environment Variables
* `DB_HOST`: Database host
* `DB_PORT`: Database port
* `DB_USERNAME`: Database username
* `DB_PASSWORD`: Database password
* `DB_NAME`: Database name
* `JWT_SECRET`: JWT secret key
* `ADMIN_USERNAME`: Admin username
* `ADMIN_PASSWORD`: Admin password

## Running Tests Locally
1. Install the required dependencies: `pip install -r requirements.txt`
2. Run the tests: `pytest`