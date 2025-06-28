# VSCode Configuration for Credit Card Guru

This directory contains VSCode configurations to enhance your development experience with the Credit Card Guru Django application.

## 🚀 Quick Start

1. **Open the project in VSCode**
2. **Install recommended extensions** when prompted (or manually from `extensions.json`)
3. **Select Python interpreter**: Use `./venv/bin/python`
4. **Start debugging**: Press `F5` or use the Run and Debug panel

## 📁 Configuration Files

### `launch.json` - Debug Configurations
- **Django: Run Server** - Start development server with debugging
- **Django: Run Server (Debug)** - Enhanced debugging with --noreload
- **Django: Run Tests** - Run Django test suite
- **Django: Shell** - Interactive Django shell with extensions
- **Django: Import Cards** - Import sample credit card data
- **Django: Migrate** - Apply database migrations
- **Django: Make Migrations** - Create new migrations
- **Django: Create Superuser** - Create admin user

### `tasks.json` - Build Tasks
- **Django: Run Server** - Quick server start (Ctrl+Shift+P → Tasks: Run Task)
- **Django: Run Tests** - Execute test suite
- **Django: Migrate/Make Migrations** - Database management
- **Install Dependencies** - Install from requirements.txt
- **Setup Project** - Complete initial setup sequence

### `settings.json` - Workspace Settings
- Python interpreter path (`./venv/bin/python`)
- Linting with flake8 (pylint disabled)
- Formatting with Black (120 char line length)
- Django-specific file associations
- Test discovery configuration
- File exclusions (__pycache__, *.pyc, etc.)

### `extensions.json` - Recommended Extensions
- **Python** - Core Python support
- **Django** - Django template syntax highlighting
- **Black Formatter** - Code formatting
- **Flake8** - Linting
- **GitLens** - Enhanced Git integration
- And more...

### `snippets.code-snippets` - Custom Snippets
- `djmodel` - Django model template
- `djview` - Django REST view template
- `djserializer` - DRF serializer template
- `djurl` - URL pattern template
- `djcommand` - Management command template
- `ccmodel` - Credit card model template

## 🎯 Usage Examples

### Running the Server
1. Press `F5` or `Ctrl+F5`
2. Select "Django: Run Server"
3. Server starts at http://127.0.0.1:8000/

### Debugging
1. Set breakpoints in your code
2. Press `F5`
3. Select "Django: Run Server (Debug)"
4. Trigger the code path to hit breakpoints

### Running Tests
1. `Ctrl+Shift+P` → "Tasks: Run Task"
2. Select "Django: Run Tests"
3. Or use the debug configuration for test debugging

### Using Snippets
1. Type snippet prefix (e.g., `djmodel`)
2. Press `Tab` to expand
3. Fill in the placeholders

## 🔧 Customization

### Personal Settings
Personal VSCode settings are gitignored. Create `.vscode/settings.json` for personal overrides:

```json
{
    "python.linting.flake8Args": ["--max-line-length=100"],
    "editor.fontSize": 14
}
```

### Adding New Configurations
1. **Debug configs**: Add to `launch.json` configurations array
2. **Tasks**: Add to `tasks.json` tasks array  
3. **Snippets**: Add to `snippets.code-snippets`

## 🐛 Troubleshooting

### Python Interpreter Not Found
1. `Ctrl+Shift+P` → "Python: Select Interpreter"
2. Choose `./venv/bin/python`
3. Or manually set in settings: `"python.defaultInterpreterPath": "./venv/bin/python"`

### Django Not Detected
Ensure these settings are correct:
```json
{
    "django.settings.module": "creditcard_guru.settings",
    "django.project.root": "${workspaceFolder}",
    "django.manage.py": "${workspaceFolder}/manage.py"
}
```

### Debugging Not Working
1. Check virtual environment is activated
2. Verify `DJANGO_SETTINGS_MODULE` environment variable
3. Ensure Django is installed: `./venv/bin/pip list | grep Django`

## 📚 Useful Keyboard Shortcuts

- `F5` - Start debugging
- `Ctrl+F5` - Run without debugging  
- `Ctrl+Shift+P` - Command palette
- `Ctrl+Shift+\`` - New terminal
- `Ctrl+Shift+D` - Debug panel
- `Ctrl+Shift+E` - Explorer panel
- `Ctrl+\`` - Toggle terminal

## 🎨 Theme Recommendations

For the best Django development experience:
- **Dark**: Dark+ (default dark), Monokai, One Dark Pro
- **Light**: Light+ (default light), Solarized Light

Install theme extensions for more options!