# GH Trades Dashboard

Live trading dashboard for GH TRADES signals with Discord OAuth authentication.

## Features

- 📊 Real-time signal history from Telegram
- 📈 P/L tracking with customizable partial exit strategies
- 🎯 Strategy optimizer (find optimal TP allocations)
- 🔐 Discord OAuth authentication
- 👥 Multi-account MT5 linking
- 🎨 Interactive charts and metrics

## Quick Start

### Local Development

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables (create `.env`):
```env
DISCORD_CLIENT_ID=your_client_id
DISCORD_CLIENT_SECRET=your_client_secret
DISCORD_REDIRECT_URI=http://localhost:5000/auth/discord/callback
SECRET_KEY=your_secret_key
DATABASE_PATH=telegram_messages.db
PORT=5000
```

3. Run the dashboard:
```bash
python dashboard_backend.py
```

4. Visit: http://localhost:5000

### Deploy to Railway

1. Push to GitHub
2. Connect Railway to this repository
3. Add environment variables in Railway dashboard
4. Deploy automatically

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

## Tech Stack

- **Backend**: Flask + SQLite
- **Frontend**: Vanilla JS + Chart.js
- **Auth**: Discord OAuth 2.0
- **Hosting**: Railway

## File Structure

```
gh-trades-dashboard/
├── dashboard_backend.py       # Flask API
├── dashboard_static/
│   ├── index.html            # Frontend
│   ├── dashboard.js          # JavaScript logic
│   └── styles.css            # Styling
├── telegram_messages.db      # SQLite database
├── optimize_exit_strategy.py # Strategy optimizer
├── setup_user_database.py    # Database schema setup
├── requirements.txt          # Python dependencies
├── Procfile                  # Railway start command
└── railway.json              # Railway configuration
```

## Strategy Optimization

Run the optimizer to find the best partial exit strategy:

```bash
python optimize_exit_strategy.py
```

Results:
- Default (50-20-10-10-10): +15.71%
- Optimized (5-0-0-0-95): +24.73% ✨

## License

Private - GH Trades Community
