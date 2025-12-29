# Setup Instructions - Environment Configuration

## Overview
This project uses environment variables to manage sensitive credentials like API keys. This is a security best practice that prevents accidental exposure of secrets.

## Required API Keys

### 1. Google Gemini API Key
Used for AI video explanation and summarization.

**Steps to obtain:**
1. Go to https://ai.google.dev/
2. Click "Get API Key" 
3. Create a new API key for your project
4. Copy the key to your `.env` file as `API`

**Important:** If you receive a "403 API key was reported as leaked" error:
- The old key has been compromised
- Delete it immediately from Google Cloud Console
- Create a new key
- Update your `.env` file

### 2. JWT Secret Key
Used for authentication tokens (can be any random string).

**Generate a secure key:**
```bash
# Using Python
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Using OpenSSL
openssl rand -hex 32
```

### 3. Google Maps API Key (Frontend only)
Used for map display in the mobile app.

**Setup:**
1. Go to https://console.cloud.google.com/
2. Create or select your project
3. Enable the Maps API
4. Create an API key with map restrictions
5. Add to your frontend environment

## Local Setup

### Backend

```bash
cd Backend

# 1. Create .env file
cp .env.example .env

# 2. Edit .env and add your keys
# Required:
API=your_google_gemini_api_key_here
SECRET_KEY=your_jwt_secret_here

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test the configuration
python -c "from ExplainX_LLM import LLM; llm = LLM(); print('✅ API configured successfully')"

# 5. Run the server
uvicorn newserver:app --reload
```

### Frontend

```bash
cd Frontend/apps/web

# 1. Create .env.local file (or update existing)
echo "EXPO_PUBLIC_GOOGLE_MAPS_API_KEY=your_key_here" > .env.local

# 2. Install dependencies
npm install  # or bun install

# 3. Run development server
npm run dev
```

## Docker Setup

If using Docker, set environment variables when running the container:

```bash
docker run -e API=your_key \
           -e SECRET_KEY=your_secret \
           -p 8080:8080 \
           your-image-name
```

Or use a `.env` file with Docker Compose:

```yaml
services:
  backend:
    environment:
      - API=${API}
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_URL=sqlite:///./auth.db
```

## Production Deployment

### Using Environment Variables (Recommended)

**Heroku:**
```bash
heroku config:set API="your_key"
heroku config:set SECRET_KEY="your_secret"
```

**AWS Lambda:**
Use AWS Secrets Manager or Parameter Store

**Google Cloud Run:**
```bash
gcloud run deploy my-service \
  --update-env-vars API=your_key,SECRET_KEY=your_secret
```

### Using Secrets Management

**AWS Secrets Manager:**
```python
import boto3
client = boto3.client('secretsmanager')
secret = client.get_secret_value(SecretId='my-secret')
api_key = secret['SecretString']
```

**HashiCorp Vault:**
```python
import hvac
client = hvac.Client(url='https://vault.example.com', token='your-token')
secret = client.secrets.kv.v2.read_secret_version(path='secret/api-key')
api_key = secret['data']['data']['API']
```

## Troubleshooting

### Error: "API not configured" or "Missing required environment variable"

**Solution:**
1. Check that .env file exists in the Backend directory
2. Verify the variable name matches (case-sensitive): `API`
3. Verify the .env file has the line: `API=your_actual_key_here`
4. Restart your application

### Error: "403 Your API key was reported as leaked"

**Solution:**
1. Go to https://console.cloud.google.com/
2. Navigate to APIs & Services > Credentials
3. Delete the compromised key immediately
4. Create a new API key
5. Update your .env file with the new key
6. Restart your application

### Error: "SECRET_KEY not set in environment variables"

**Solution:**
1. This is a warning, not an error (development mode)
2. For production, set: `SECRET_KEY=your_secure_random_string`
3. Generate a secure key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

### Cannot find module "python-dotenv"

**Solution:**
```bash
pip install python-dotenv
# Or reinstall requirements
pip install -r requirements.txt
```

## Security Reminders

✅ **DO:**
- Keep .env files in .gitignore
- Use different keys for dev/staging/production
- Rotate keys periodically
- Store secrets in a secure password manager
- Use environment variables in all environments

❌ **DON'T:**
- Commit .env files to git
- Hardcode API keys in source code
- Share .env files via email or chat
- Use the same key for multiple projects
- Log or print API keys

## File Locations

```
video Explainer/
├── .env (DO NOT COMMIT - local only)
├── .env.example (Template - safe to commit)
├── .gitignore (includes .env)
├── Backend/
│   ├── .env (DO NOT COMMIT)
│   ├── ExplainX_LLM.py (uses os.getenv("API"))
│   └── auth_utils.py (uses os.getenv("SECRET_KEY"))
└── Frontend/
    ├── .env.local (DO NOT COMMIT)
    └── apps/web/maps.web.jsx
```

## Related Documentation

- [SECURITY_FIX.md](./SECURITY_FIX.md) - Detailed security incident report
- [.env.example](./.env.example) - Environment variable template
- [Backend/requirements.txt](./Backend/requirements.txt) - Python dependencies
