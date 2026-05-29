# Architecture

## Monitoring & Alerts (THU-53) Added
- Models: Watchlist, WatchlistItem, Portfolio, Position, AlertRule, AlertEvent, DeliveryChannel.
- APIs (/monitor): bootstrap, watchlists CRUD, portfolio positions (manual + CSV import), exposure analytics, alert rules, channels, scan + deliver.
- Router wired; basic portfolio exposure page at /portfolio/[id].
- Delivery channels: in-app (recorded), webhook (POST), email/slack/teams placeholders (Phase 1 stubs).
