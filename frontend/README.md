# Frontend Setup Guide

## Phase 1: Development Environment

### Prerequisites
- Node.js 16+ and npm 8+
- Python 3.11+ with existing backend set up

### Installation

1. **Install Node.js** (if not already installed):
   ```bash
   # macOS with Homebrew
   brew install node
   
   # Ubuntu/Debian
   sudo apt-get install nodejs npm
   
   # Or download from https://nodejs.org/
   ```

2. **Install frontend dependencies**:
   ```bash
   cd frontend
   npm install
   ```

3. **Copy environment file**:
   ```bash
   cp .env.example .env
   ```

4. **Update .env if needed**:
   ```bash
   VITE_API_BASE_URL=http://localhost:8000
   VITE_APP_NAME=Körüg
   ```

### Running Development Servers

**Terminal 1 - Start Backend**:
```bash
cd /path/to/korug
python -m korug.run
# Backend runs on http://localhost:8000
```

**Terminal 2 - Start Frontend**:
```bash
cd /path/to/korug/frontend
npm run dev
# Frontend runs on http://localhost:5173
```

### Access Dashboard

Open your browser and navigate to:
```
http://localhost:5173
```

**Demo Credentials**:
- Username: `admin`
- Password: `password`

### Available Scripts

- `npm run dev` - Start development server with hot reload
- `npm run build` - Build for production
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint
- `npm run type-check` - TypeScript type checking

## Phase 1 Features

### ✅ Implemented
- Login/Logout authentication with JWT
- Token refresh mechanism
- Dashboard home with stats cards
- Domain list (view, add, delete)
- Material-UI styling
- Responsive layout
- API client with error handling

### 🔄 In Progress (Phase 2)
- Vulnerability charts and trending
- Alert management
- Subdomain discovery timeline
- Real-time scan progress
- False positive marking

### 📋 Planned (Phase 3+)
- User management
- API key management
- Advanced filtering
- Bulk operations
- Export/reporting

## Troubleshooting

### Port Already in Use

If port 5173 is in use:
```bash
npm run dev -- --port 5174
```

### API Connection Issues

1. Check backend is running: `curl http://localhost:8000/health`
2. Verify `.env` has correct API base URL
3. Check browser console for CORS errors
4. Ensure backend CORS is configured

### Build Errors

Clear node_modules and reinstall:
```bash
rm -rf node_modules package-lock.json
npm install
npm run build
```

### TypeScript Errors

Run type checking:
```bash
npm run type-check
```

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable React components
│   │   ├── common/      # Navbar, Spinner, Dialogs
│   │   ├── dashboard/   # Dashboard cards & charts
│   │   └── domains/     # Domain management
│   ├── pages/           # Full page components
│   ├── api/             # API layer (Axios)
│   ├── hooks/           # Custom React hooks
│   ├── types/           # TypeScript definitions
│   ├── utils/           # Utility functions
│   ├── styles/          # Material-UI theme
│   ├── App.tsx          # Main app component
│   └── main.tsx         # Entry point
├── public/              # Static files
├── package.json         # Dependencies
├── tsconfig.json        # TypeScript config
├── vite.config.ts       # Vite config
└── index.html           # HTML entry
```

## Next Steps

1. Complete Phase 1 setup and verify dashboard loads
2. Test login flow and domain management
3. Review components in browser DevTools
4. Prepare Phase 2 features (charts, alerts)
5. Add unit tests as needed

## Support

For issues or questions:
1. Check browser console for errors
2. Review backend logs for API errors
3. Open an issue on GitHub
