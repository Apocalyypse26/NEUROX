# NEUROX - Token Trust Intelligence

NEUROX is a premium Crypto/AI SaaS platform engineered to provide institutional-grade virality scoring, pattern detection, and trust intelligence for crypto assets. Featuring a state-of-the-art "Liquid Glass" frontend and a multi-model AI backend, NEUROX scans token branding, launch assets, and public visuals to surface high-fidelity trust signals and scam risks in seconds.

## Project Architecture

```text
neurogravity/
├── src/                    # React frontend (Vite)
│   ├── components/         # Liquid Glass UI components
│   ├── pages/              # Cinematic pages (Home, Dashboard, Auth, Results)
│   └── ...
├── premium.css             # High-fidelity design system and micro-interactions
├── tailwind.config.js      # Core design tokens (Colors, Fonts, Layout)
├── neurox-backend/         # Core AI pipelines and analysis queues
├── backend/                # Legacy Python FastAPI endpoints
└── supabase/               # Database configuration and Edge Functions
```

## Core Features & Aesthetics

- **Cinematic Liquid Glass UI**: Fully frosted, translucent glass components (`.liquid-glass`) with inner 3D gloss effects, multi-stop gradient masks, and 3D pill-shaped action buttons.
- **Scroll-Aware Animations**: Integrated `framer-motion` for fluid, viewport-triggered entry sequences and structural reveals across all marketing and dashboard views.
- **Visual Evidence Layer**: Simulated neural-link scanner previews that process token assets and visually demonstrate pattern detection logic on the landing page.
- **Premium Design System**: Rooted in high-contrast dark mode (`#000000`) with high-voltage orange accents (`#FF4500` - `#FF6B35`), completely managed via modern Tailwind configuration.
- **Tiered Scanning Engine**: Seamless progression from Free (Scavenger) to Pro (Prime at $49/mo), unlocking full diagnostic directives and PDF evidentiary exports.

## Tech Stack

- **Frontend**: React, Vite, Tailwind CSS, Framer Motion
- **Backend & AI**: Node.js, Python (FastAPI), Claude Vision API, Helius (On-chain data)
- **Infrastructure**: Supabase (PostgreSQL, Auth, Storage, Edge Functions)

## Local Development

### Frontend Setup
```bash
# Install dependencies
npm install

# Start Vite dev server with Stagewise integrations
npm run dev
```

### Backend Setup (Node/Python)
```bash
# Ensure you are running inside neurox-backend
cd neurox-backend
npm install
npm run dev
```

## Environment Variables

| Variable | Description | Where to Set |
|----------|-------------|--------------|
| `VITE_SUPABASE_URL` | Supabase project endpoint | Frontend (Vercel) |
| `VITE_SUPABASE_ANON_KEY` | Supabase anonymous public key | Frontend (Vercel) |
| `VITE_API_URL` | Backend pipeline URL | Frontend (Vercel) |
| `USE_REAL_TRIBE` | Toggle mock vs. real Claude analysis | Backend |
| `CORS_ORIGINS` | Permitted frontend domains | Backend |

## Production Deployment

### 1. Deploy API (Render/Railway)
1. Connect your repository and point the Root Directory to the appropriate backend folder.
2. Build and expose the service on port `8000` or `3000` depending on the environment.
3. Configure your production environment variables (e.g. `CORS_ORIGINS` left empty initially).

### 2. Deploy Frontend (Vercel)
1. Import repository and select **Vite**.
2. Keep the root directory at `./`.
3. Add the `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`, and the live backend API URL.
4. Deploy the application.

### 3. Finalize CORS
Once Vercel provisions a production URL (e.g., `https://neurox.vercel.app`), append it to the backend `CORS_ORIGINS` variable to permit secure cross-origin requests.
