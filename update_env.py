
import os

env_file = '.env'
new_redirect = 'https://rona-isobathythermal-nondeficiently.ngrok-free.dev/api/admin/auth/slack/callback'
new_cors = 'https://rona-isobathythermal-nondeficiently.ngrok-free.dev'

with open(env_file, 'r', encoding='utf-8') as f:
    lines = f.readlines()

with open(env_file, 'w', encoding='utf-8') as f:
    for line in lines:
        if line.startswith('SLACK_REDIRECT_URI='):
            f.write(f'SLACK_REDIRECT_URI={new_redirect}\n')
        elif line.startswith('CORS_ORIGINS='):
            f.write(f'CORS_ORIGINS={new_cors}\n')
        else:
            f.write(line)
