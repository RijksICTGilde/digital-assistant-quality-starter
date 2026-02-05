#!/usr/bin/env python3
"""
Start script for Gemeente AI Assistant Backend
"""

import os
import sys
import uvicorn
from pathlib import Path

# Add the app directory to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

def main():
    """Main entry point"""
    
    # Check if .env file exists
    env_file = current_dir / ".env"
    if not env_file.exists():
        env_example = current_dir / ".env.example"
        if env_example.exists():
            print("❌ .env file not found!")
            print("📋 Please copy .env.example to .env and configure your settings:")
            print(f"   cp {env_example} {env_file}")
            print("\n🔑 Don't forget to set your GREENPT_API_KEY!")
            return 1
    
    # Check if GreenPT API key is set
    from dotenv import load_dotenv
    load_dotenv(env_file)
    
    if not os.getenv("GREENPT_API_KEY"):
        print("❌ GREENPT_API_KEY is not set!")
        print("🔑 Please add your GreenPT API key to the .env file")
        return 1
    
    # Start the server
    print("🚀 Starting Gemeente AI Assistant Backend...")
    print("📍 API will be available at: http://localhost:8000")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔍 Health Check: http://localhost:8000/api/health")
    print("\n✨ Ready to help Nederlandse gemeentes with AI! ✨\n")
    
    try:
        loop = os.getenv("UVICORN_LOOP")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            reload_dirs=[str(current_dir / "app")],
            log_level="info",
            loop=loop,
        )
    except KeyboardInterrupt:
        print("\n👋 Gemeente AI Assistant Backend stopped")
        return 0
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
