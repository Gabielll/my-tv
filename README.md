# 📺 Personal Media Server

A personal media server designed to simulate 24/7 TV channels using an on-demand streaming model. **Now deployable 100% free on the cloud!**

## 🚀 Quick Start

### ☁️ Cloud Deployment (Recommended - 100% Free!)

Deploy to Render's free tier with external services:

```bash
# 1. Fork this repository on GitHub
# 2. Set up external services (5 minutes):
#    - CockroachDB Cloud (Database)
#    - CloudAMQP (Message Queue)  
#    - Cloudflare R2 (Storage)
#    - TMDB API (Metadata)
#    - Google Gemini API (AI)
# 3. Deploy to Render using render.yaml
# 4. Configure UptimeRobot to keep services alive
```

**📖 Detailed Instructions:** [README_RENDER_DEPLOYMENT.md](README_RENDER_DEPLOYMENT.md)

### 🏠 Local Development

For local development with external services:

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd <project-directory>
   ```

2. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your external service credentials
   ```

3. **Run with Docker Compose:**
   ```bash
   docker-compose up -d
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f <service-name>
   ```

5. **Stop services:**
   ```bash
   docker-compose down
   ```

## 🏗️ Architecture

The system consists of 8 services running as web services:

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │    │    Admin UI      │    │   Stream API    │
│  (Static Site)  │    │  (Web Service)   │    │ (Web Service)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│ Media Manager   │    │Metadata Enricher │    │Normalization    │
│ (Web Service)   │◄──►│  (Web Service)   │◄──►│   Worker        │
└─────────────────┘    └──────────────────┘    │ (Web Service)   │
                                │               └─────────────────┘
                                ▼                        │
┌─────────────────┐    ┌──────────────────┐             ▼
│ Scheduler AI    │    │ Scene Analyzer   │    ┌─────────────────┐
│ (Web Service)   │◄───│  (Web Service)   │◄───│  CloudAMQP      │
└─────────────────┘    └──────────────────┘    │ (Message Queue) │
         │                       │              └─────────────────┘
         ▼                       ▼
┌─────────────────┐    ┌──────────────────┐
│ CockroachDB     │    │  Cloudflare R2   │
│   (Database)    │    │   (Storage)      │
└─────────────────┘    └──────────────────┘
```

## 💰 Cost Breakdown (100% Free!)

| Service | Plan | Limit | Monthly Cost |
|---------|------|-------|--------------|
| **Render** | Free Tier | 750h/month × 7 services | $0.00 |
| **CockroachDB** | Serverless | 5GB storage | $0.00 |
| **CloudAMQP** | Little Lemur | 1M messages/month | $0.00 |
| **Cloudflare R2** | Free Tier | 10GB storage | $0.00 |
| **TMDB API** | Free | 1000 requests/day | $0.00 |
| **Google Gemini** | Free | 60 requests/minute | $0.00 |
| **UptimeRobot** | Free | 50 monitors | $0.00 |
| **TOTAL** | | | **$0.00** 🎉 |

## 📚 Documentation

### 🚀 Deployment Guides
- **[README_RENDER_DEPLOYMENT.md](README_RENDER_DEPLOYMENT.md)** - Quick 5-minute deployment guide
- **[RENDER_DEPLOYMENT_INSTRUCTIONS.md](RENDER_DEPLOYMENT_INSTRUCTIONS.md)** - Detailed step-by-step instructions
- **[docs/RENDER_DEPLOYMENT_GUIDE.md](docs/RENDER_DEPLOYMENT_GUIDE.md)** - Complete deployment guide with troubleshooting

### 🛠️ Development Guides  
- **[docs/LOCAL_DEVELOPMENT_GUIDE.md](docs/LOCAL_DEVELOPMENT_GUIDE.md)** - Local development setup
- **[GUIDE.md](GUIDE.md)** - Comprehensive usage guide
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System architecture overview

### 🔧 Operations
- **[scripts/setup_uptimerobot.py](scripts/setup_uptimerobot.py)** - Automated UptimeRobot setup
- **[scripts/verify_deployment.py](scripts/verify_deployment.py)** - Deployment verification
- **[tests/](tests/)** - Integration tests for all services

## 🎯 Features

- **📺 24/7 TV Channel Simulation** - Continuous streaming experience
- **🎬 Automatic Metadata Enrichment** - TMDB integration for movie/TV data
- **🤖 AI-Powered Descriptions** - Google Gemini for intelligent content descriptions
- **📱 Web-Based Admin Interface** - Easy file upload and management
- **🔄 Automatic Video Processing** - Normalization and scene analysis
- **📊 Smart Scheduling** - AI-driven EPG generation
- **☁️ Hybrid Storage** - Local + Cloudflare R2 for scalability
- **📈 Health Monitoring** - Built-in health checks and monitoring
- **🔍 Structured Logging** - JSON logging with correlation IDs
- **🚀 Production Ready** - Deployed on Render with external services

## 🧪 Testing

Run integration tests to verify everything works:

```bash
# Test converted services
python tests/test_e2e_converted_services.py

# Test external service connectivity  
python tests/test_external_services.py

# Test complete pipeline
python tests/test_e2e_complete_pipeline.py

# Verify deployment
python scripts/verify_deployment.py
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

**🎉 Ready to deploy your own free media server in the cloud? Start with [README_RENDER_DEPLOYMENT.md](README_RENDER_DEPLOYMENT.md)!**
