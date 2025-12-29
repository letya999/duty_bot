"""
HTML templates for authentication flows.
"""


def telegram_login_page() -> str:
    """
    HTML page for Telegram login.

    Uses Telegram Web App API to get user authentication data
    and send it to the backend callback endpoint.
    """
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Login</title>
        <script async src="https://telegram.org/js/telegram-web-app.js"></script>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 500px;
                margin: 0 auto;
                background: white;
                padding: 20px;
                border-radius: 10px;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Telegram Login</h1>
            <p>Opening Telegram login...</p>
            <p id="status">Loading...</p>
        </div>
        <script>
            const tg = window.Telegram.WebApp;

            async function authenticate() {
                const initData = tg.initData;
                if (!initData) {
                    document.getElementById('status').textContent = 'Error: initData not available';
                    return;
                }

                try {
                    const response = await fetch('/web/auth/telegram-callback', {
                        method: 'POST',
                        credentials: 'include',
                        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                        body: 'init_data=' + encodeURIComponent(initData)
                    });

                    if (response.ok) {
                        window.location.href = '/web/dashboard';
                    } else {
                        const data = await response.json();
                        document.getElementById('status').textContent = 'Error: ' + data.detail;
                    }
                } catch (error) {
                    document.getElementById('status').textContent = 'Error: ' + error.message;
                }
            }

            authenticate();
        </script>
    </body>
    </html>
    """


def redirect_with_user_data(user_data: str) -> str:
    """
    Bridge HTML page to redirect and set user data in localStorage.

    Args:
        user_data: JSON-encoded user data (double-encoded for HTML safety)

    Returns:
        HTML that redirects to dashboard after setting localStorage
    """
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>Redirecting...</title></head>
    <body>
        <script>
            // Store only non-sensitive user data for UI state
            localStorage.setItem('user', {user_data});
            // Session token is in httpOnly cookie - DO NOT store in localStorage
            window.location.href = '/';
        </script>
    </body>
    </html>
    """
