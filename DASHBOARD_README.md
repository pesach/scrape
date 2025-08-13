# Link Fetcher Dashboard

A modern, interactive web dashboard for managing and fetching pending links with manual click-to-fetch functionality.

## Features

- **Visual Dashboard**: Clean, modern UI to view all your pending links
- **Manual Fetch Control**: Click individual "Fetch" buttons to manually trigger link fetching
- **Batch Operations**: "Fetch All Pending" button to process all pending links at once
- **Status Tracking**: Real-time status updates (Pending, Fetching, Completed, Failed)
- **Filter Views**: Filter links by status (All, Pending, Fetching, Completed, Failed)
- **Add New Links**: Easy modal interface to add new URLs to the queue
- **Retry Failed**: Retry failed links with a single click
- **Statistics**: Live statistics showing total, pending, completed, and failed links
- **Persistent Storage**: Links are saved in browser localStorage
- **Toast Notifications**: Visual feedback for all actions

## How to Use

### Starting the Dashboard

1. **Run the server**:
   ```bash
   python3 server.py
   ```
   Or if already running, the dashboard is available at: http://localhost:8080

2. **Open in Browser**:
   Navigate to http://localhost:8080 in your web browser

### Dashboard Controls

#### Fetching Pending Links

You have **three ways** to fetch pending links:

1. **Individual Fetch** (Manual Click):
   - Each pending link has a blue "Fetch" button
   - Click the button to fetch that specific link
   - The button changes to "Fetching..." with a spinner during the process
   - Once complete, the status updates to "Completed" or "Failed"

2. **Fetch All Pending**:
   - Click the "⚡ Fetch All Pending" button at the top
   - This will automatically fetch all pending links sequentially
   - Each link will be processed with a small delay to avoid overwhelming servers

3. **Retry Failed**:
   - Failed links show an orange "Retry" button
   - Click to retry fetching that specific link

#### Managing Links

- **Add New Link**: 
  - Click "➕ Add New Link" button
  - Enter the URL in the modal
  - Press Enter or click "Add Link"

- **Remove Link**:
  - Each link has a red "Remove" button
  - Click to delete the link from the queue

- **Clear Completed**:
  - Click "🗑️ Clear Completed" to remove all successfully fetched links

- **Filter Links**:
  - Use the filter buttons to view specific status types
  - Options: All, Pending, Fetching, Completed, Failed

#### Dashboard Information

Each link displays:
- **URL**: The link to be fetched
- **Status**: Current state (pending/fetching/completed/failed)
- **Added**: Timestamp when the link was added
- **Attempts**: Number of fetch attempts
- **Fetched**: Timestamp of successful fetch (if completed)

## Sample Links

The dashboard comes pre-loaded with sample links for testing:
- `https://jsonplaceholder.typicode.com/posts/1` - Working API endpoint
- `https://jsonplaceholder.typicode.com/users` - Working API endpoint
- `https://example.com/api/data1` - Sample URL (will simulate success)
- `https://example.com/api/data2` - Sample URL (will simulate success)

## Technical Details

- **Frontend**: Pure HTML/CSS/JavaScript (no frameworks required)
- **Backend**: Python HTTP server with API endpoints
- **Storage**: Browser localStorage for persistence
- **CORS**: Enabled for API testing

## Files

- `dashboard.html` - Main dashboard interface
- `dashboard.js` - JavaScript functionality and link management
- `server.py` - Python server to serve the dashboard
- `DASHBOARD_README.md` - This file

## Notes

- Links that fail due to CORS or network issues will automatically simulate success after 1 second for demo purposes
- The dashboard auto-refreshes statistics every 5 seconds
- All data is stored locally in your browser's localStorage