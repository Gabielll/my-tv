#!/usr/bin/env python3
"""
Deployment Verification Script

Tests all deployed services to ensure they're working correctly.
Checks health endpoints, database connectivity, and basic functionality.
"""

import requests
import json
import sys
import time
from typing import Dict, List, Tuple
from urllib.parse import urljoin

class DeploymentVerifier:
    def __init__(self, service_urls: Dict[str, str]):
        self.service_urls = service_urls
        self.results = []
    
    def test_health_endpoint(self, service_name: str, base_url: str) -> Tuple[bool, Dict]:
        """Test health endpoint of a service"""
        try:
            health_url = urljoin(base_url, "/health")
            response = requests.get(health_url, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                return True, {
                    "status": "healthy",
                    "response_time": response.elapsed.total_seconds(),
                    "data": data
                }
            else:
                return False, {
                    "status": "unhealthy",
                    "status_code": response.status_code,
                    "response": response.text[:200]
                }
        except requests.exceptions.Timeout:
            return False, {"status": "timeout", "error": "Request timed out after 30 seconds"}
        except requests.exceptions.ConnectionError:
            return False, {"status": "connection_error", "error": "Could not connect to service"}
        except Exception as e:
            return False, {"status": "error", "error": str(e)}
    
    def test_admin_ui_functionality(self, base_url: str) -> Tuple[bool, Dict]:
        """Test admin UI specific functionality"""
        try:
            # Test main page
            response = requests.get(base_url, timeout=30)
            if response.status_code != 200:
                return False, {"error": f"Main page returned {response.status_code}"}
            
            # Test if it's serving HTML
            if "text/html" not in response.headers.get("content-type", ""):
                return False, {"error": "Main page not serving HTML"}
            
            return True, {"status": "functional", "content_type": response.headers.get("content-type")}
        except Exception as e:
            return False, {"error": str(e)}
    
    def test_stream_api_functionality(self, base_url: str) -> Tuple[bool, Dict]:
        """Test stream API specific functionality"""
        try:
            # Test streams endpoint
            streams_url = urljoin(base_url, "/streams")
            response = requests.get(streams_url, timeout=30)
            
            # Should return JSON (even if empty)
            if response.status_code == 200:
                data = response.json()
                return True, {"status": "functional", "streams_count": len(data)}
            else:
                return False, {"error": f"Streams endpoint returned {response.status_code}"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def verify_all_services(self) -> Dict:
        """Verify all services"""
        print("🔍 Starting deployment verification...")
        print("=" * 60)
        
        overall_status = True
        service_results = {}
        
        for service_name, base_url in self.service_urls.items():
            print(f"\n🧪 Testing {service_name}...")
            print(f"   URL: {base_url}")
            
            # Test health endpoint
            health_ok, health_result = self.test_health_endpoint(service_name, base_url)
            
            result = {
                "url": base_url,
                "health": health_result,
                "functional": None
            }
            
            if health_ok:
                print(f"   ✅ Health check: OK ({health_result.get('response_time', 0):.2f}s)")
                
                # Test service-specific functionality
                if service_name == "admin-ui":
                    func_ok, func_result = self.test_admin_ui_functionality(base_url)
                    result["functional"] = func_result
                    if func_ok:
                        print(f"   ✅ Functionality: OK")
                    else:
                        print(f"   ❌ Functionality: {func_result.get('error', 'Failed')}")
                        overall_status = False
                
                elif service_name == "stream-api":
                    func_ok, func_result = self.test_stream_api_functionality(base_url)
                    result["functional"] = func_result
                    if func_ok:
                        print(f"   ✅ Functionality: OK ({func_result.get('streams_count', 0)} streams)")
                    else:
                        print(f"   ❌ Functionality: {func_result.get('error', 'Failed')}")
                        overall_status = False
                
                else:
                    # For worker services, health check is sufficient
                    print(f"   ✅ Worker service: OK")
            else:
                print(f"   ❌ Health check: {health_result.get('error', 'Failed')}")
                overall_status = False
            
            service_results[service_name] = result
        
        return {
            "overall_status": overall_status,
            "services": service_results,
            "timestamp": time.time()
        }
    
    def generate_report(self, results: Dict) -> str:
        """Generate a detailed report"""
        report = []
        report.append("📋 DEPLOYMENT VERIFICATION REPORT")
        report.append("=" * 60)
        report.append(f"Timestamp: {time.ctime(results['timestamp'])}")
        report.append(f"Overall Status: {'✅ PASS' if results['overall_status'] else '❌ FAIL'}")
        report.append("")
        
        # Service details
        for service_name, service_result in results["services"].items():
            report.append(f"🔧 {service_name.upper()}")
            report.append(f"   URL: {service_result['url']}")
            
            # Health status
            health = service_result["health"]
            if health.get("status") == "healthy":
                report.append(f"   Health: ✅ OK ({health.get('response_time', 0):.2f}s)")
                if "data" in health:
                    data = health["data"]
                    report.append(f"   Service: {data.get('service', 'unknown')}")
                    report.append(f"   Version: {data.get('version', 'unknown')}")
                    report.append(f"   Uptime: {data.get('uptime', 0):.1f}s")
            else:
                report.append(f"   Health: ❌ {health.get('error', 'Failed')}")
            
            # Functional status
            if service_result["functional"]:
                func = service_result["functional"]
                if "error" in func:
                    report.append(f"   Function: ❌ {func['error']}")
                else:
                    report.append(f"   Function: ✅ OK")
            
            report.append("")
        
        # Recommendations
        report.append("💡 RECOMMENDATIONS")
        report.append("-" * 30)
        
        failed_services = [name for name, result in results["services"].items() 
                          if result["health"].get("status") != "healthy"]
        
        if failed_services:
            report.append("❌ Failed services detected:")
            for service in failed_services:
                report.append(f"   - {service}: Check logs in Render dashboard")
            report.append("")
            report.append("🔧 Troubleshooting steps:")
            report.append("   1. Check environment variables in Render dashboard")
            report.append("   2. Verify external service connectivity (DB, Queue, APIs)")
            report.append("   3. Check service logs for specific errors")
            report.append("   4. Ensure all dependencies are properly configured")
        else:
            report.append("✅ All services are healthy!")
            report.append("")
            report.append("🎯 Next steps:")
            report.append("   1. Set up UptimeRobot monitors to keep services alive")
            report.append("   2. Test complete file processing pipeline")
            report.append("   3. Monitor resource usage and limits")
            report.append("   4. Configure alerting for production monitoring")
        
        return "\n".join(report)

def main():
    """Main function"""
    print("🚀 Render Deployment Verification")
    print("=" * 50)
    
    # Get service URLs
    print("📋 Enter your deployed service URLs:")
    print("(You can find these in your Render dashboard)")
    print()
    
    service_urls = {}
    services = [
        ("admin-ui", "Admin UI", True),
        ("stream-api", "Stream API", True),
        ("media-manager", "Media Manager", False),
        ("metadata-enricher", "Metadata Enricher", False),
        ("normalization-worker", "Normalization Worker", False),
        ("scene-analyzer", "Scene Analyzer", False),
        ("scheduler-ai", "Scheduler AI", False),
    ]
    
    for service_key, service_name, required in services:
        while True:
            url = input(f"{service_name} URL (https://...onrender.com): ").strip()
            if url:
                if not url.startswith("https://"):
                    url = "https://" + url
                if url.endswith("/"):
                    url = url[:-1]
                service_urls[service_key] = url
                break
            elif not required:
                skip = input(f"Skip {service_name}? (y/N): ").strip().lower()
                if skip == 'y':
                    break
            else:
                print(f"❌ {service_name} is required")
    
    if not service_urls:
        print("❌ No service URLs provided")
        sys.exit(1)
    
    # Run verification
    verifier = DeploymentVerifier(service_urls)
    results = verifier.verify_all_services()
    
    # Generate and display report
    print("\n" + "=" * 60)
    report = verifier.generate_report(results)
    print(report)
    
    # Save report to file
    report_file = f"deployment_report_{int(time.time())}.txt"
    with open(report_file, "w") as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_file}")
    
    # Exit with appropriate code
    sys.exit(0 if results["overall_status"] else 1)

if __name__ == "__main__":
    main()