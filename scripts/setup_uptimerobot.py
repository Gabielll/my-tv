#!/usr/bin/env python3
"""
UptimeRobot Setup Script

Automatically creates monitors for all Render services to keep them alive.
Requires UptimeRobot API key and service URLs.
"""

import requests
import json
import sys
import os
from typing import List, Dict

class UptimeRobotSetup:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.uptimerobot.com/v2"
        self.headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Cache-Control": "no-cache"
        }
    
    def create_monitor(self, friendly_name: str, url: str) -> Dict:
        """Create a new HTTP monitor"""
        data = {
            "api_key": self.api_key,
            "format": "json",
            "type": 1,  # HTTP(s)
            "friendly_name": friendly_name,
            "url": url,
            "interval": 300,  # 5 minutes
            "timeout": 30,
            "keyword_type": 0,  # Not checking for keyword
            "http_method": 1,  # GET
            "http_auth_type": 0,  # No authentication
        }
        
        response = requests.post(
            f"{self.base_url}/newMonitor",
            headers=self.headers,
            data=data
        )
        
        return response.json()
    
    def get_monitors(self) -> Dict:
        """Get all existing monitors"""
        data = {
            "api_key": self.api_key,
            "format": "json"
        }
        
        response = requests.post(
            f"{self.base_url}/getMonitors",
            headers=self.headers,
            data=data
        )
        
        return response.json()
    
    def setup_all_monitors(self, base_urls: Dict[str, str]) -> List[Dict]:
        """Setup monitors for all services"""
        results = []
        
        services = [
            ("Media Server - Admin UI", "admin-ui", "/health"),
            ("Media Server - Stream API", "stream-api", "/health"),
            ("Media Server - Media Manager", "media-manager", "/health"),
            ("Media Server - Metadata Enricher", "metadata-enricher", "/health"),
            ("Media Server - Normalization Worker", "normalization-worker", "/health"),
            ("Media Server - Scene Analyzer", "scene-analyzer", "/health"),
            ("Media Server - Scheduler AI", "scheduler-ai", "/health"),
        ]
        
        for friendly_name, service_key, health_path in services:
            if service_key in base_urls:
                url = base_urls[service_key] + health_path
                print(f"Creating monitor for {friendly_name}: {url}")
                
                result = self.create_monitor(friendly_name, url)
                results.append({
                    "service": service_key,
                    "friendly_name": friendly_name,
                    "url": url,
                    "result": result
                })
                
                if result.get("stat") == "ok":
                    print(f"✅ Monitor created successfully for {service_key}")
                else:
                    print(f"❌ Failed to create monitor for {service_key}: {result}")
            else:
                print(f"⚠️  No URL provided for {service_key}")
        
        return results

def main():
    """Main function"""
    print("🤖 UptimeRobot Setup Script")
    print("=" * 50)
    
    # Get API key
    api_key = os.getenv("UPTIMEROBOT_API_KEY")
    if not api_key:
        print("❌ UPTIMEROBOT_API_KEY environment variable not set")
        print("\nTo get your API key:")
        print("1. Go to https://uptimerobot.com/")
        print("2. Login to your account")
        print("3. Go to Settings > API Settings")
        print("4. Copy your Main API Key")
        print("5. Set environment variable: export UPTIMEROBOT_API_KEY=your_key")
        sys.exit(1)
    
    # Get service URLs
    print("\n📋 Enter your Render service URLs:")
    print("(You can find these in your Render dashboard)")
    print()
    
    base_urls = {}
    services = [
        ("admin-ui", "Admin UI"),
        ("stream-api", "Stream API"),
        ("media-manager", "Media Manager"),
        ("metadata-enricher", "Metadata Enricher"),
        ("normalization-worker", "Normalization Worker"),
        ("scene-analyzer", "Scene Analyzer"),
        ("scheduler-ai", "Scheduler AI"),
    ]
    
    for service_key, service_name in services:
        while True:
            url = input(f"{service_name} URL (https://...onrender.com): ").strip()
            if url:
                if not url.startswith("https://"):
                    url = "https://" + url
                if url.endswith("/"):
                    url = url[:-1]
                base_urls[service_key] = url
                break
            else:
                skip = input(f"Skip {service_name}? (y/N): ").strip().lower()
                if skip == 'y':
                    break
    
    if not base_urls:
        print("❌ No service URLs provided")
        sys.exit(1)
    
    # Setup UptimeRobot
    uptimerobot = UptimeRobotSetup(api_key)
    
    print(f"\n🚀 Setting up monitors for {len(base_urls)} services...")
    results = uptimerobot.setup_all_monitors(base_urls)
    
    # Summary
    print("\n📊 Setup Summary:")
    print("=" * 50)
    
    successful = 0
    failed = 0
    
    for result in results:
        status = "✅" if result["result"].get("stat") == "ok" else "❌"
        print(f"{status} {result['friendly_name']}")
        if result["result"].get("stat") == "ok":
            successful += 1
        else:
            failed += 1
            print(f"   Error: {result['result'].get('error', {}).get('message', 'Unknown error')}")
    
    print(f"\n🎯 Results: {successful} successful, {failed} failed")
    
    if successful > 0:
        print("\n🎉 UptimeRobot monitors created successfully!")
        print("Your services will now be pinged every 5 minutes to keep them alive.")
        print("\nNext steps:")
        print("1. Check your UptimeRobot dashboard: https://uptimerobot.com/dashboard")
        print("2. Configure alert contacts if desired")
        print("3. Monitor your services for the next few hours to ensure they stay online")
    
    if failed > 0:
        print(f"\n⚠️  {failed} monitors failed to create. Please check the errors above.")
        print("You can run this script again or create the monitors manually.")

if __name__ == "__main__":
    main()