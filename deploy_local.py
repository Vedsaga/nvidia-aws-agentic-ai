#!/usr/bin/env python3
"""
Kāraka RAG System - Local Development Deployment
Consolidated script for local setup with hardware validation

Usage:
    python deploy_local.py                    # Full setup with checks
    python deploy_local.py --lightweight      # Lightweight mode (no Docker)
    python deploy_local.py --destroy          # Cleanup all local resources
"""

import os
import sys
import subprocess
import shutil
import argparse
from pathlib import Path

# Colors
class Colors:
    BLUE = '\033[0;34m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    RED = '\033[0;31m'
    NC = '\033[0m'

def print_header(msg):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.NC}")
    print(f"{Colors.BLUE}{msg}{Colors.NC}")
    print(f"{Colors.BLUE}{'='*60}{Colors.NC}\n")

def print_step(msg):
    print(f"{Colors.GREEN}▶ {msg}{Colors.NC}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.NC}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.NC}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.NC}")

def error_exit(msg):
    print_error(msg)
    sys.exit(1)

def run_command(cmd, check=True, timeout=None):
    """Run shell command"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        if check and result.returncode != 0:
            print_error(f"Command failed: {cmd}")
            print_error(result.stderr)
            return False
        return result
    except subprocess.TimeoutExpired:
        print_error(f"Command timed out: {cmd}")
        return False
    except Exception as e:
        print_error(f"Command error: {e}")
        return False

def destroy_local():
    """Destroy local development environment"""
    print_header("Destroying Local Development Environment")
    
    print("This will STOP and REMOVE:")
    print("  - Docker containers (Neo4j, NIM models)")
    print("  - Docker volumes (Neo4j data)")
    print("  - Virtual environment")
    print("  - Model cache")
    
    confirm = input("\nAre you sure? Type 'YES' to confirm: ")
    
    if confirm != "YES":
        print_warning("Destroy cancelled")
        sys.exit(0)
    
    print_step("Stopping Docker services...")
    run_command("docker compose -f docker-compose.local.yml down -v", check=False)
    print_success("Docker services stopped")
    
    print_step("Removing virtual environment...")
    if os.path.exists("venv"):
        shutil.rmtree("venv")
    print_success("Virtual environment removed")
    
    print_step("Cleaning model cache...")
    for cache_dir in ["model_cache", "nim_cache"]:
        if os.path.exists(cache_dir):
            shutil.rmtree(cache_dir)
    print_success("Model cache cleaned")
    
    print_success("Local environment destroyed!")
    sys.exit(0)

def check_hardware():
    """Check hardware requirements"""
    print_header("Step 1: Hardware Requirements Check")
    
    has_issues = False
    
    # Check CPU
    print_step("Checking CPU...")
    result = run_command("nproc")
    if result:
        cpu_cores = int(result.stdout.strip())
        if cpu_cores < 4:
            print_warning(f"CPU: {cpu_cores} cores (minimum 4 recommended)")
            has_issues = True
        else:
            print_success(f"CPU: {cpu_cores} cores")
    
    # Check RAM
    print_step("Checking RAM...")
    result = run_command("free -g | awk '/^Mem:/{print $2}'")
    if result:
        ram_gb = int(result.stdout.strip())
        if ram_gb < 8:
            print_warning(f"RAM: {ram_gb}GB (minimum 8GB recommended)")
            has_issues = True
        else:
            print_success(f"RAM: {ram_gb}GB")
    
    # Check disk space
    print_step("Checking disk space...")
    result = run_command("df -BG . | awk 'NR==2 {print $4}' | sed 's/G//'")
    if result:
        disk_gb = int(result.stdout.strip())
        if disk_gb < 20:
            print_warning(f"Disk: {disk_gb}GB free (minimum 20GB recommended)")
            has_issues = True
        else:
            print_success(f"Disk: {disk_gb}GB free")
    
    # Check GPU
    print_step("Checking GPU...")
    result = run_command("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader", check=False)
    if result and result.returncode == 0:
        gpu_info = result.stdout.strip().split('\n')[0]
        print_success(f"GPU: {gpu_info}")
    else:
        print_warning("GPU: Not detected (will use CPU - slower)")
    
    if has_issues:
        print_warning("\nHardware requirements not fully met")
        print_warning("Consider using --lightweight mode for lower resource usage")
        response = input("\nContinue anyway? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)

def check_software(lightweight):
    """Check software requirements"""
    print_header("Step 2: Software Requirements Check")
    
    missing = False
    
    # Check Python
    print_step("Checking Python...")
    result = run_command("python3 --version")
    if result:
        print_success(f"Python: {result.stdout.strip()}")
    else:
        print_error("Python 3 not found")
        missing = True
    
    # Check Docker (only if not lightweight)
    if not lightweight:
        print_step("Checking Docker...")
        result = run_command("docker --version", check=False)
        if result and result.returncode == 0:
            print_success(f"Docker: {result.stdout.strip()}")
            
            # Check if Docker is running
            result = run_command("docker ps", check=False)
            if result and result.returncode == 0:
                print_success("Docker daemon: Running")
            else:
                print_error("Docker daemon: Not running")
                print_warning("Please start Docker Desktop or Docker daemon")
                missing = True
        else:
            print_error("Docker not found")
            print_warning("Install from: https://docs.docker.com/get-docker/")
            missing = True
    
    # Check pip
    print_step("Checking pip...")
    result = run_command("python3 -m pip --version")
    if result:
        print_success("pip: Available")
    else:
        print_error("pip not found")
        missing = True
    
    if missing:
        error_exit("Missing required software. Please install and try again.")

def setup_venv():
    """Setup virtual environment"""
    print_header("Step 3: Python Virtual Environment Setup")
    
    if os.path.exists("venv"):
        print_success("Virtual environment already exists")
    else:
        print_step("Creating virtual environment...")
        run_command("python3 -m venv venv")
        print_success("Virtual environment created")
    
    print_step("Upgrading pip...")
    run_command("venv/bin/pip install --upgrade pip -q")
    print_success("pip upgraded")

def install_dependencies(lightweight):
    """Install dependencies"""
    print_header("Step 4: Installing Dependencies")
    
    req_file = "requirements.lightweight.txt" if lightweight else "requirements.local.txt"
    
    if not os.path.exists(req_file):
        print_warning(f"{req_file} not found, using requirements.txt")
        req_file = "requirements.txt"
    
    print_step(f"Installing from {req_file}...")
    run_command(f"venv/bin/pip install -r {req_file} -q")
    print_success("Dependencies installed")

def setup_environment(lightweight):
    """Setup environment configuration"""
    print_header("Step 5: Environment Configuration")
    
    env_file = ".env.lightweight" if lightweight else ".env.local"
    
    if os.path.exists(env_file):
        print_success(f"Environment file exists: {env_file}")
    else:
        if os.path.exists(".env.example"):
            print_step(f"Creating {env_file} from .env.example...")
            shutil.copy(".env.example", env_file)
            print_success(f"Environment file created: {env_file}")
        else:
            print_warning(f"{env_file} not found, please create it manually")
    
    # Copy to .env for active use
    if os.path.exists(env_file):
        shutil.copy(env_file, ".env")
        print_success("Active environment: .env")

def start_docker_services():
    """Start Docker services"""
    print_header("Step 6: Starting Docker Services")
    
    print_step("Creating cache directories...")
    os.makedirs("nim_cache", exist_ok=True)
    os.makedirs("model_cache", exist_ok=True)
    print_success("Cache directories created")
    
    print_step("Starting Docker Compose services...")
    run_command("docker compose -f docker-compose.local.yml up -d")
    print_success("Docker services started")
    
    print_step("Waiting for services to initialize (30 seconds)...")
    import time
    time.sleep(30)
    
    # Check service health
    print_step("Checking service health...")
    
    services = {
        "Neo4j": "http://localhost:7474",
        "Nemotron Model": "http://localhost:8000/v1/models",
        "Embedding Model": "http://localhost:8001/v1/models"
    }
    
    for name, url in services.items():
        result = run_command(f"curl -s {url} > /dev/null 2>&1", check=False)
        if result and result.returncode == 0:
            print_success(f"{name}: Running")
        else:
            print_warning(f"{name}: Not ready yet (may need more time)")

def setup_lightweight():
    """Setup lightweight mode"""
    print_header("Step 6: Lightweight Mode Setup")
    
    print_step("Creating model cache directory...")
    os.makedirs("model_cache", exist_ok=True)
    print_success("Model cache created")
    
    print_warning("Lightweight mode uses local Python models")
    print_warning("First run will download models (~500MB)")
    print_warning("Subsequent runs will use cached models")

def display_summary(lightweight):
    """Display setup summary"""
    print_header("Setup Complete!")
    
    print(f"Environment: {'Lightweight' if lightweight else 'Full Docker'}")
    result = run_command("venv/bin/python --version")
    if result:
        print(f"Python: {result.stdout.strip()}")
    print("Virtual Environment: venv/")
    print()
    
    if lightweight:
        print("🚀 Next Steps:")
        print("  1. Start the API server:")
        print("     source venv/bin/activate")
        print("     python lightweight_api.py")
        print()
        print("  2. Test the setup:")
        print("     python test_e2e.py --mode local")
        print()
        print("  3. Access API docs:")
        print("     http://localhost:8080/docs")
    else:
        print("🚀 Services:")
        print("  • Neo4j Browser:    http://localhost:7474")
        print("  • Nemotron API:     http://localhost:8000")
        print("  • Embedding API:    http://localhost:8001")
        print()
        print("  Credentials:")
        print("    Neo4j - neo4j/hackathon2025")
        print()
        print("🚀 Next Steps:")
        print("  1. Wait for models to load (check logs):")
        print("     docker compose -f docker-compose.local.yml logs -f")
        print()
        print("  2. Test the setup:")
        print("     python test_e2e.py --mode local")
        print()
        print("🛑 To stop services:")
        print("  docker compose -f docker-compose.local.yml down")
    
    print()
    print("🗑️  To destroy this environment:")
    print("  python deploy_local.py --destroy")

def main():
    parser = argparse.ArgumentParser(description='Deploy Kāraka RAG System locally')
    parser.add_argument('--lightweight', action='store_true',
                       help='Lightweight mode (no Docker)')
    parser.add_argument('--destroy', action='store_true',
                       help='Destroy all local resources')
    
    args = parser.parse_args()
    
    if args.destroy:
        destroy_local()
    
    print_header("Kāraka RAG System - Local Development Setup")
    print(f"Mode: {'Lightweight (No Docker)' if args.lightweight else 'Full (Docker + NIM)'}\n")
    
    # Run checks
    check_hardware()
    check_software(args.lightweight)
    
    # Setup environment
    setup_venv()
    install_dependencies(args.lightweight)
    setup_environment(args.lightweight)
    
    # Start services based on mode
    if args.lightweight:
        setup_lightweight()
    else:
        start_docker_services()
    
    # Display summary
    display_summary(args.lightweight)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nSetup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
