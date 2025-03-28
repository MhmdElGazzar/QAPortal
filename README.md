# QAPortal

A Django-based portal for managing QA tasks and integrating with Azure DevOps.

## Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd QAPortal
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
   - Copy `.env.example` to `.env`:
     ```bash
     cp .env.example .env
     ```
   - Edit `.env` and fill in your actual credentials:
     - Azure DevOps settings:
       - `AZURE_DEVOPS_ORG`: Your Azure DevOps organization name
       - `AZURE_DEVOPS_PROJECT`: Your Azure DevOps project name
       - `AZURE_DEVOPS_API_VERSION`: API version (default: 7.1-preview.3)
       - `AZURE_DEVOPS_PAT`: Your Personal Access Token
     - OpenAI settings:
       - `OPENAI_API_KEY`: Your OpenAI API key

5. Run migrations:
```bash
python manage.py migrate
```

6. Start the development server:
```bash
python manage.py runserver
```

The application will be available at `http://localhost:8000`

## Features

- Integration with Azure DevOps for task management
- Automated quality task creation
- Story estimation using OpenAI
- Project information tracking

## Security Notes

- Never commit the `.env` file to version control
- Keep your API keys and tokens secure
- Use environment variables for all sensitive credentials
