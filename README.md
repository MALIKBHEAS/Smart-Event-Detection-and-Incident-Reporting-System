Sentinel SOC - Smart Event Detection and Incident Reporting System
Sentinel SOC is an integrated, intelligent event detection and incident reporting system. The platform combines a responsive frontend with a robust backend to automatically detect anomalies or events (using AI/ML models such as YOLOv8) and facilitate immediate incident reporting and management.

🚀 Features
AI-Powered Event Detection: Utilizes YOLOv8 for real-time or video-based object and event detection.
Incident Reporting System: Allows SOC (Security Operations Center) operators to track, manage, and investigate events.
Microservices Architecture: Completely containerized setup using Docker and Docker Compose for easy deployment and scaling.
Modern Tech Stack:
Backend: Python 3.12, FastAPI, PostgreSQL, SQLAlchemy, Alembic, and YOLOv8.
Frontend: Node.js, React, Vite.
🛠️ Tech Stack
Backend
Framework: FastAPI (Python 3.12)
Database: PostgreSQL
ORM & Migrations: SQLAlchemy & Alembic
Machine Learning: YOLOv8 (Ultralytics) for video/camera stream inference
Formatting/Linting: Ruff, Black, isort, mypy
Frontend
Framework: React / Vite
Package Manager: npm
Infrastructure & Deployment
Docker & Docker Compose
⚙️ Prerequisites
Before you begin, ensure you have met the following requirements:

Docker & Docker Compose installed on your system.
Python 3.12 (if you want to run the backend locally without Docker).
Node.js v18+ (if you want to run the frontend locally without Docker).
Git for version control.
🐳 Quick Start (Using Docker)
The project includes a docker-compose.yml file with specific profiles for both development and production environments.

1. Clone the repository
git clone <your-repository-url>
cd sentinel-soc-gaps-closed
2. Environment Variables
Copy the .env.example file to create your local .env file:

cp .env.example .env
Make sure to update the environment variables in .env (like JWT secrets, Postgres credentials) if needed.

3. Run Development Environment
To run the application in development mode (with hot-reloading enabled for both frontend and backend):

docker compose --profile dev up --build
Backend API: http://localhost:8000
Frontend App: http://localhost:5173
Postgres Database: localhost:5432
4. Run Production Environment
To run the built, optimized containers for production without hot-reloading:

docker compose --profile prod up --build -d
Frontend App: http://localhost (Port 80)
Backend API: http://localhost:8000
💻 Local Development (Without Docker)
If you prefer to run the components directly on your host machine for debugging:

Backend Setup
Navigate to the backend directory.
Create and activate a virtual environment:
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
Install dependencies:
pip install -r requirements.txt # Or via poetry/pipenv if applicable
Run the backend server:
uvicorn main:app --reload --host 0.0.0.0 --port 8000
Frontend Setup
Navigate to the frontend directory.
Install Node dependencies:
npm install
Start the Vite development server:
npm run dev
🧪 Testing the AI Model
The project includes standalone test scripts to verify the YOLOv8 object detection capabilities using a webcam or a YouTube stream. Ensure you have the required dependencies and the model weights (yolov8n.pt) downloaded:

python test_yolo_camera.py (Tests YOLO inference via local webcam)
python test_yolo_youtube.py (Tests YOLO inference on a YouTube video stream)
📁 Project Structure
.
├── backend/               # FastAPI backend source code
├── docker/                # Dockerfiles for frontend and backend
├── frontend/              # React/Vite frontend source code
├── docker-compose.yml     # Docker Compose orchestration
├── pyproject.toml         # Python configurations (Ruff, MyPy, etc.)
├── yolov8n.pt             # YOLOv8 nano model weights
├── test_yolo_camera.py    # YOLO local webcam test script
└── test_yolo_youtube.py   # YOLO YouTube stream test script
🤝 Contributing
Fork the Project
Create your Feature Branch (git checkout -b feature/AmazingFeature)
Commit your Changes (git commit -m 'Add some AmazingFeature')
Push to the Branch (git push origin feature/AmazingFeature)
Open a Pull Request
