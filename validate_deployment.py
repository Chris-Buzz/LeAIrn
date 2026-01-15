#!/usr/bin/env python3
"""
Deployment validation script for LearnAI booking system.
Checks that all required files and configurations are in place.
"""

import os
import sys
import json


def check_file_exists(filepath, description):
    """Check if a required file exists."""
    exists = os.path.exists(filepath)
    status = "OK" if exists else "MISSING"
    print(f"  [{status}] {description}: {filepath}")
    return exists


def check_env_var(var_name, required=True):
    """Check if an environment variable is set."""
    value = os.getenv(var_name)
    if value:
        # Mask sensitive values
        if 'password' in var_name.lower() or 'secret' in var_name.lower():
            display = '*' * 8
        else:
            display = value[:20] + '...' if len(value) > 20 else value
        print(f"  [OK] {var_name}: {display}")
        return True
    else:
        status = "MISSING" if required else "NOT SET"
        print(f"  [{status}] {var_name}")
        return not required


def validate_json_file(filepath, required_keys=None):
    """Validate a JSON file."""
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        if required_keys:
            missing = [k for k in required_keys if k not in data]
            if missing:
                print(f"  [WARNING] Missing keys in {filepath}: {missing}")
                return False
        print(f"  [OK] {filepath} is valid JSON")
        return True
    except FileNotFoundError:
        print(f"  [MISSING] {filepath}")
        return False
    except json.JSONDecodeError as e:
        print(f"  [ERROR] {filepath} is not valid JSON: {e}")
        return False


def main():
    print("=" * 60)
    print("LearnAI Deployment Validation")
    print("=" * 60)

    all_passed = True

    # Check required files
    print("\n[1/5] Checking required files...")
    required_files = [
        ('app.py', 'Main application'),
        ('firestore_db.py', 'Database module'),
        ('requirements.txt', 'Dependencies'),
        ('vercel.json', 'Vercel configuration'),
        ('.gitignore', 'Git ignore file'),
    ]

    for filepath, description in required_files:
        if not check_file_exists(filepath, description):
            all_passed = False

    # Check directories
    print("\n[2/5] Checking required directories...")
    required_dirs = [
        ('routes', 'Route blueprints'),
        ('services', 'Service modules'),
        ('templates', 'HTML templates'),
        ('static', 'Static files'),
        ('middleware', 'Middleware'),
        ('utils', 'Utility modules'),
    ]

    for dirpath, description in required_dirs:
        if not os.path.isdir(dirpath):
            print(f"  [MISSING] {description}: {dirpath}")
            all_passed = False
        else:
            print(f"  [OK] {description}: {dirpath}")

    # Check environment variables
    print("\n[3/5] Checking environment variables...")
    from dotenv import load_dotenv
    load_dotenv()

    required_env = [
        'FLASK_SECRET_KEY',
        'GOOGLE_CLIENT_ID',
        'GOOGLE_CLIENT_SECRET',
        'EMAIL_USER',
        'EMAIL_PASSWORD',
    ]

    optional_env = [
        'OPENAI_API_KEY',
        'ANTHROPIC_API_KEY',
    ]

    for var in required_env:
        if not check_env_var(var, required=True):
            all_passed = False

    for var in optional_env:
        check_env_var(var, required=False)

    # Check Firebase credentials
    print("\n[4/5] Checking Firebase configuration...")
    firebase_creds = 'firebase-credentials.json'
    if os.path.exists(firebase_creds):
        required_keys = ['type', 'project_id', 'private_key', 'client_email']
        if not validate_json_file(firebase_creds, required_keys):
            all_passed = False
    else:
        print(f"  [MISSING] {firebase_creds}")
        all_passed = False

    # Check templates
    print("\n[5/5] Checking templates...")
    required_templates = [
        'index.html',
        'admin.html',
        'admin_login.html',
        'feedback.html',
    ]

    for template in required_templates:
        filepath = os.path.join('templates', template)
        if not check_file_exists(filepath, f'Template: {template}'):
            all_passed = False

    # Summary
    print("\n" + "=" * 60)
    if all_passed:
        print("VALIDATION PASSED - Ready for deployment")
        return 0
    else:
        print("VALIDATION FAILED - Please fix the issues above")
        return 1


if __name__ == '__main__':
    sys.exit(main())
