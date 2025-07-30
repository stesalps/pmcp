#!/usr/bin/env python3
"""
Google Manus System - Deployment Automation

Automated deployment script for the Google Manus System with support for
different environments (local, cloud, production) and deployment strategies.
"""

import os
import sys
import json
import subprocess
import argparse
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
import time
import logging

# Deployment Configuration
class DeploymentConfig:
    """Deployment configuration management"""
    
    ENVIRONMENTS = {
        "local": {
            "description": "Local development environment",
            "requirements": ["python>=3.8", "pip", "git"],
            "services": ["jupyter", "api_server"],
            "ports": {"api": 8000, "jupyter": 8888}
        },
        "colab": {
            "description": "Google Colab environment",
            "requirements": ["google-colab", "ipywidgets"],
            "services": ["jupyter", "api_server", "frp"],
            "ports": {"api": 8000, "frp": 7000}
        },
        "cloud": {
            "description": "Cloud deployment (AWS/GCP/Azure)",
            "requirements": ["docker", "docker-compose"],
            "services": ["api_server", "nginx", "redis"],
            "ports": {"api": 8000, "nginx": 80, "redis": 6379}
        },
        "production": {
            "description": "Production environment",
            "requirements": ["docker", "kubernetes", "helm"],
            "services": ["api_server", "nginx", "redis", "monitoring"],
            "ports": {"api": 8000, "nginx": 80, "redis": 6379, "monitoring": 9090}
        }
    }
    
    DEFAULT_CONFIG = {
        "environment": "local",
        "version": "1.0.0",
        "debug": False,
        "log_level": "INFO",
        "database_url": "sqlite:///manus.db",
        "redis_url": "redis://localhost:6379",
        "secret_key": "change-me-in-production"
    }

class DeploymentManager:
    """Main deployment manager"""
    
    def __init__(self, environment: str = "local", config_file: Optional[str] = None):
        self.environment = environment
        self.config = DeploymentConfig.DEFAULT_CONFIG.copy()
        self.config["environment"] = environment
        
        if config_file and Path(config_file).exists():
            self.load_config(config_file)
        
        self.setup_logging()
        self.project_root = Path(__file__).parent
        self.deployment_dir = self.project_root / "deployment"
        self.deployment_dir.mkdir(exist_ok=True)
    
    def setup_logging(self):
        """Setup logging for deployment"""
        log_level = getattr(logging, self.config.get("log_level", "INFO"))
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(self.project_root / "deployment.log")
            ]
        )
        self.logger = logging.getLogger("deployment")
    
    def load_config(self, config_file: str):
        """Load configuration from file"""
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
                self.config.update(file_config)
            self.logger.info(f"Loaded configuration from {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load config from {config_file}: {e}")
    
    def save_config(self, config_file: str):
        """Save current configuration to file"""
        try:
            with open(config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.logger.info(f"Saved configuration to {config_file}")
        except Exception as e:
            self.logger.error(f"Failed to save config to {config_file}: {e}")
    
    def check_requirements(self) -> bool:
        """Check if all requirements are met"""
        env_config = DeploymentConfig.ENVIRONMENTS.get(self.environment, {})\n        requirements = env_config.get("requirements", [])\n        \n        self.logger.info(f"Checking requirements for {self.environment} environment...")\n        \n        missing_requirements = []\n        \n        for requirement in requirements:\n            if "python" in requirement:\n                # Check Python version\n                version_required = requirement.split(">=")[1] if ">=" in requirement else "3.8"\n                if not self._check_python_version(version_required):\n                    missing_requirements.append(requirement)\n            elif requirement in ["pip", "git", "docker", "docker-compose", "kubectl", "helm"]:\n                # Check command availability\n                if not self._check_command(requirement):\n                    missing_requirements.append(requirement)\n            elif requirement == "google-colab":\n                # Check if running in Colab\n                if "google.colab" not in sys.modules:\n                    missing_requirements.append(requirement)\n        \n        if missing_requirements:\n            self.logger.error(f"Missing requirements: {missing_requirements}")\n            return False\n        \n        self.logger.info("All requirements satisfied ✅")\n        return True\n    \n    def _check_python_version(self, required_version: str) -> bool:\n        """Check Python version"""\n        import sys\n        current_version = sys.version_info\n        required_parts = required_version.split(".")\n        \n        try:\n            required_major = int(required_parts[0])\n            required_minor = int(required_parts[1]) if len(required_parts) > 1 else 0\n            \n            return (current_version.major > required_major or \n                   (current_version.major == required_major and current_version.minor >= required_minor))\n        except ValueError:\n            return False\n    \n    def _check_command(self, command: str) -> bool:\n        """Check if command is available"""\n        try:\n            subprocess.run([command, "--version"], \n                         capture_output=True, check=True, timeout=10)\n            return True\n        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):\n            return False\n    \n    def install_dependencies(self) -> bool:\n        """Install Python dependencies"""\n        self.logger.info("Installing Python dependencies...")\n        \n        requirements_file = self.project_root / "requirements.txt"\n        if not requirements_file.exists():\n            self.logger.info("Creating requirements.txt...")\n            self._create_requirements_file(requirements_file)\n        \n        try:\n            subprocess.run([\n                sys.executable, "-m", "pip", "install", "-r", str(requirements_file)\n            ], check=True, timeout=300)\n            \n            self.logger.info("Dependencies installed successfully ✅")\n            return True\n        except subprocess.CalledProcessError as e:\n            self.logger.error(f"Failed to install dependencies: {e}")\n            return False\n    \n    def _create_requirements_file(self, requirements_file: Path):\n        """Create requirements.txt file"""\n        base_requirements = [\n            "fastapi>=0.104.0",\n            "uvicorn[standard]>=0.24.0",\n            "aiohttp>=3.9.0",\n            "aiofiles>=23.2.1",\n            "websockets>=12.0",\n            "requests>=2.31.0",\n            "beautifulsoup4>=4.12.0",\n            "nest-asyncio>=1.5.8",\n            "pydantic>=2.5.0",\n            "python-multipart>=0.0.6"\n        ]\n        \n        if self.environment == "colab":\n            base_requirements.extend([\n                "ipywidgets>=8.1.0",\n                "google-colab"\n            ])\n        elif self.environment in ["cloud", "production"]:\n            base_requirements.extend([\n                "redis>=5.0.0",\n                "psycopg2-binary>=2.9.0",\n                "gunicorn>=21.2.0"\n            ])\n        \n        with open(requirements_file, 'w') as f:\n            f.write("\\n".join(base_requirements))\n    \n    def create_docker_files(self):\n        """Create Docker configuration files"""\n        if self.environment not in ["cloud", "production"]:\n            return\n        \n        self.logger.info("Creating Docker configuration...")\n        \n        # Dockerfile\n        dockerfile_content = f'''\nFROM python:3.11-slim\n\nWORKDIR /app\n\n# Install system dependencies\nRUN apt-get update && apt-get install -y \\\n    git \\\n    curl \\\n    && rm -rf /var/lib/apt/lists/*\n\n# Copy requirements and install Python dependencies\nCOPY requirements.txt .\nRUN pip install --no-cache-dir -r requirements.txt\n\n# Copy application code\nCOPY . .\n\n# Create necessary directories\nRUN mkdir -p /app/data /app/logs /app/sites\n\n# Expose port\nEXPOSE 8000\n\n# Set environment variables\nENV PYTHONPATH=/app\nENV ENVIRONMENT={self.environment}\n\n# Run the application\nCMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]\n'''\n        \n        dockerfile_path = self.deployment_dir / "Dockerfile"\n        with open(dockerfile_path, 'w') as f:\n            f.write(dockerfile_content)\n        \n        # Docker Compose\n        compose_content = f'''\nversion: '3.8'\n\nservices:\n  manus-api:\n    build: .\n    ports:\n      - "8000:8000"\n    environment:\n      - ENVIRONMENT={self.environment}\n      - DATABASE_URL={self.config.get("database_url")}\n      - REDIS_URL={self.config.get("redis_url")}\n    volumes:\n      - ./data:/app/data\n      - ./logs:/app/logs\n      - ./sites:/app/sites\n    depends_on:\n      - redis\n    restart: unless-stopped\n\n  redis:\n    image: redis:7-alpine\n    ports:\n      - "6379:6379"\n    volumes:\n      - redis_data:/data\n    restart: unless-stopped\n\n  nginx:\n    image: nginx:alpine\n    ports:\n      - "80:80"\n      - "443:443"\n    volumes:\n      - ./nginx.conf:/etc/nginx/nginx.conf\n      - ./sites:/var/www/html\n    depends_on:\n      - manus-api\n    restart: unless-stopped\n\nvolumes:\n  redis_data:\n'''\n        \n        compose_path = self.deployment_dir / "docker-compose.yml"\n        with open(compose_path, 'w') as f:\n            f.write(compose_content)\n        \n        # Nginx configuration\n        nginx_content = '''\nevents {\n    worker_connections 1024;\n}\n\nhttp {\n    upstream manus_api {\n        server manus-api:8000;\n    }\n\n    server {\n        listen 80;\n        server_name localhost;\n\n        # API proxy\n        location /api/ {\n            proxy_pass http://manus_api;\n            proxy_set_header Host $host;\n            proxy_set_header X-Real-IP $remote_addr;\n            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n            proxy_set_header X-Forwarded-Proto $scheme;\n        }\n\n        # WebSocket proxy\n        location /ws {\n            proxy_pass http://manus_api;\n            proxy_http_version 1.1;\n            proxy_set_header Upgrade $http_upgrade;\n            proxy_set_header Connection "upgrade";\n            proxy_set_header Host $host;\n        }\n\n        # Static sites\n        location /sites/ {\n            alias /var/www/html/;\n            try_files $uri $uri/ =404;\n        }\n\n        # Health check\n        location /health {\n            proxy_pass http://manus_api/health;\n        }\n    }\n}\n'''\n        \n        nginx_path = self.deployment_dir / "nginx.conf"\n        with open(nginx_path, 'w') as f:\n            f.write(nginx_content)\n        \n        self.logger.info("Docker configuration created ✅")\n    \n    def create_systemd_service(self):\n        """Create systemd service file for local deployment"""\n        if self.environment != "local":\n            return\n        \n        service_content = f'''\n[Unit]\nDescription=Google Manus System API Server\nAfter=network.target\n\n[Service]\nType=simple\nUser=manus\nWorkingDirectory={self.project_root}\nEnvironment=PYTHONPATH={self.project_root}\nExecStart={sys.executable} -m uvicorn main:app --host 0.0.0.0 --port 8000\nRestart=always\nRestartSec=10\n\n[Install]\nWantedBy=multi-user.target\n'''\n        \n        service_path = self.deployment_dir / "manus-system.service"\n        with open(service_path, 'w') as f:\n            f.write(service_content)\n        \n        self.logger.info(f"Systemd service file created: {service_path}")\n        self.logger.info("To install: sudo cp manus-system.service /etc/systemd/system/")\n        self.logger.info("Then run: sudo systemctl enable manus-system && sudo systemctl start manus-system")\n    \n    def create_startup_script(self):\n        """Create startup script"""\n        script_content = f'''\n#!/bin/bash\n\n# Google Manus System Startup Script\n# Environment: {self.environment}\n\nset -e\n\necho "🚀 Starting Google Manus System ({self.environment})..."\n\n# Change to project directory\ncd "{self.project_root}"\n\n# Activate virtual environment if it exists\nif [ -d "venv" ]; then\n    echo "📦 Activating virtual environment..."\n    source venv/bin/activate\nfi\n\n# Install/update dependencies\necho "📥 Installing dependencies..."\npip install -r requirements.txt\n\n# Run database migrations if needed\nif [ -f "migrate.py" ]; then\n    echo "🗄️ Running database migrations..."\n    python migrate.py\nfi\n\n# Start the appropriate services based on environment\ncase "{self.environment}" in\n    "local")\n        echo "🖥️ Starting local development server..."\n        python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload\n        ;;\n    "colab")\n        echo "📓 Starting Colab environment..."\n        python -c "from Google_Manus_System import launch_gui; launch_gui()"\n        ;;\n    "cloud"|"production")\n        echo "☁️ Starting containerized services..."\n        docker-compose up -d\n        ;;\n    *)\n        echo "❌ Unknown environment: {self.environment}"\n        exit 1\n        ;;\nesac\n\necho "✅ Google Manus System started successfully!"\n'''\n        \n        script_path = self.deployment_dir / "start.sh"\n        with open(script_path, 'w') as f:\n            f.write(script_content)\n        \n        # Make executable\n        os.chmod(script_path, 0o755)\n        \n        self.logger.info(f"Startup script created: {script_path}")\n    \n    def create_environment_file(self):\n        """Create environment configuration file"""\n        env_content = f'''\n# Google Manus System Environment Configuration\n# Environment: {self.environment}\n\nENVIRONMENT={self.environment}\nDEBUG={str(self.config.get("debug", False)).lower()}\nLOG_LEVEL={self.config.get("log_level", "INFO")}\n\n# Database\nDATABASE_URL={self.config.get("database_url", "sqlite:///manus.db")}\n\n# Redis\nREDIS_URL={self.config.get("redis_url", "redis://localhost:6379")}\n\n# Security\nSECRET_KEY={self.config.get("secret_key", "change-me-in-production")}\n\n# API Configuration\nAPI_HOST=0.0.0.0\nAPI_PORT=8000\n\n# Model Configuration\nDEFAULT_MODEL_TYPE=auto\nGOOGLE_MODEL_NAME=google/gemini-2.5-pro\nOLLAMA_MODEL_NAME=qwen2.5-coder:7b\n\n# Deployment\nMAX_WORKERS=4\nTIMEOUT=30\n'''\n        \n        env_path = self.deployment_dir / ".env"\n        with open(env_path, 'w') as f:\n            f.write(env_content)\n        \n        self.logger.info(f"Environment file created: {env_path}")\n    \n    def deploy(self) -> bool:\n        """Execute deployment"""\n        self.logger.info(f"🚀 Starting deployment for {self.environment} environment...")\n        \n        # Check requirements\n        if not self.check_requirements():\n            self.logger.error("Requirements check failed. Aborting deployment.")\n            return False\n        \n        # Install dependencies\n        if not self.install_dependencies():\n            self.logger.error("Dependency installation failed. Aborting deployment.")\n            return False\n        \n        # Create configuration files\n        self.create_environment_file()\n        self.create_startup_script()\n        \n        if self.environment in ["cloud", "production"]:\n            self.create_docker_files()\n        elif self.environment == "local":\n            self.create_systemd_service()\n        \n        # Save deployment configuration\n        deployment_config = {\n            "environment": self.environment,\n            "deployed_at": time.time(),\n            "version": self.config.get("version", "1.0.0"),\n            "config": self.config\n        }\n        \n        config_path = self.deployment_dir / "deployment_config.json"\n        with open(config_path, 'w') as f:\n            json.dump(deployment_config, f, indent=2)\n        \n        self.logger.info("✅ Deployment completed successfully!")\n        self.logger.info(f"📁 Deployment files created in: {self.deployment_dir}")\n        \n        # Print next steps\n        self._print_next_steps()\n        \n        return True\n    \n    def _print_next_steps(self):\n        """Print next steps for the user"""\n        print("\\n" + "="*60)\n        print("🎯 NEXT STEPS")\n        print("="*60)\n        \n        if self.environment == "local":\n            print("\\n🖥️ Local Development:")\n            print(f"   1. cd {self.deployment_dir}")\n            print("   2. ./start.sh")\n            print("   3. Open http://localhost:8000 in your browser")\n            \n        elif self.environment == "colab":\n            print("\\n📓 Google Colab:")\n            print("   1. Upload the notebook to Google Colab")\n            print("   2. Run all cells in order")\n            print("   3. Use the GUI interface or API endpoints")\n            \n        elif self.environment in ["cloud", "production"]:\n            print("\\n☁️ Cloud/Production Deployment:")\n            print(f"   1. cd {self.deployment_dir}")\n            print("   2. docker-compose up -d")\n            print("   3. Configure your domain/load balancer")\n            print("   4. Set up SSL certificates")\n            print("   5. Configure monitoring and backups")\n        \n        print("\\n📚 Documentation:")\n        print("   • API docs: http://your-domain/docs")\n        print("   • Health check: http://your-domain/health")\n        print("   • WebSocket: ws://your-domain/ws")\n        \n        print("\\n🔧 Management Commands:")\n        print("   • View logs: docker-compose logs -f (cloud/production)")\n        print("   • Restart: docker-compose restart (cloud/production)")\n        print("   • Update: git pull && docker-compose up -d --build")\n        \n        print("\\n" + "="*60)\n\ndef main():\n    """Main deployment function"""\n    parser = argparse.ArgumentParser(description="Google Manus System Deployment")\n    parser.add_argument(\n        "environment", \n        choices=list(DeploymentConfig.ENVIRONMENTS.keys()),\n        help="Deployment environment"\n    )\n    parser.add_argument(\n        "--config", \n        help="Configuration file path"\n    )\n    parser.add_argument(\n        "--dry-run", \n        action="store_true",\n        help="Show what would be deployed without actually deploying"\n    )\n    \n    args = parser.parse_args()\n    \n    # Print environment info\n    env_info = DeploymentConfig.ENVIRONMENTS[args.environment]\n    print(f"🌍 Environment: {args.environment}")\n    print(f"📝 Description: {env_info['description']}")\n    print(f"🔧 Services: {', '.join(env_info['services'])}")\n    \n    if args.dry_run:\n        print("\\n🔍 DRY RUN MODE - No changes will be made")\n        return\n    \n    # Create deployment manager and deploy\n    manager = DeploymentManager(args.environment, args.config)\n    success = manager.deploy()\n    \n    if success:\n        print("\\n🎉 Deployment completed successfully!")\n        sys.exit(0)\n    else:\n        print("\\n❌ Deployment failed!")\n        sys.exit(1)\n\nif __name__ == "__main__":\n    main()