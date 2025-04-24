# Deploying to PythonAnywhere

This guide walks through deploying the Credit Card Roadmap application to PythonAnywhere with the new project structure.

## Setup Steps

### 1. Sign Up and Create a Web App

1. Sign up for a PythonAnywhere account at https://www.pythonanywhere.com/
2. From your dashboard, click on the **Web** tab
3. Click **Add a new web app**
4. Choose **Manual configuration** (not the "Flask" option)
5. Select **Python 3.11**

### 2. Set Up Your Code

1. In the PythonAnywhere dashboard, go to the **Consoles** tab
2. Start a new Bash console
3. Clone your repository:
   ```bash
   git clone https://github.com/yourusername/creditcard-roadmap.git
   ```
   
   If using a private repository, set up an SSH key or use HTTPS with a personal access token.

### 3. Configure Virtual Environment

1. In the Bash console, create and activate a virtual environment:
   ```bash
   cd creditcard-roadmap
   python -m venv venv
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### 4. Configure Web App

1. Go back to the **Web** tab
2. In the **Code** section:
   - Set **Source code** to: `/home/yourusername/creditcard-roadmap`
   - Set **Working directory** to: `/home/yourusername/creditcard-roadmap`

3. In the **Virtualenv** section:
   - Enter: `/home/yourusername/creditcard-roadmap/venv`

4. In the **WSGI configuration file** section, click the link to edit the WSGI file

5. Replace the contents with:
   ```python
   import sys
   import os
   
   # Add the application to the path
   path = '/home/yourusername/creditcard-roadmap'
   if path not in sys.path:
       sys.path.append(path)
   
   # Import directly from app
   from app import create_app
   application = create_app('production')
   ```

### 5. Set Up Database

1. In the Bash console, initialize the database:
   ```bash
   cd creditcard-roadmap
   python reset_db.py
   ```

### 6. Static Files

1. Go back to the **Web** tab
2. In the **Static files** section, add:
   - URL: `/static/`
   - Path: `/home/yourusername/creditcard-roadmap/app/static`

### 7. Environment Variables

1. Click the **Web** tab
2. Scroll down to the **Environment variables** section and add:
   - `FLASK_ENV`: `production`
   - `SECRET_KEY`: `your-secure-secret-key`

### 8. Reload and Test

1. Click the **Reload** button to restart your web app
2. Visit your site at `yourusername.pythonanywhere.com`

## Project Structure

The new project structure follows Flask best practices:

```
/creditcard-roadmap/       (project root)
├── app/                  (main application package)
│   ├── __init__.py      (with create_app factory)
│   ├── models/
│   ├── routes/
│   ├── templates/
│   └── static/
├── migrations/           (Flask-Migrate files)
├── tests/                (test files)
├── scripts/              (utility scripts)
├── config.py             (configuration file)
├── run.py                (development server script)
├── wsgi.py               (production entry point)
└── requirements.txt      (dependencies)
```

## Troubleshooting

- **Application errors**: Check the error logs in the Web tab
- **Dependency issues**: Make sure all dependencies are installed in your virtualenv
- **Database problems**: Check file permissions and paths
- **Import errors**: Ensure paths are correctly set in the WSGI file

## Maintenance

- **Database migrations**: Run database migrations after code updates:
  ```bash
  cd /home/yourusername/creditcard-roadmap
  python -c "from app import db; db.create_all()"
  ```
  
- **Code updates**: Pull the latest code and reload the web app:
  ```bash
  cd /home/yourusername/creditcard-roadmap
  git pull
  # If dependencies changed, activate venv and run: pip install -r requirements.txt
  ```
  Then click the **Reload** button in the Web tab. 