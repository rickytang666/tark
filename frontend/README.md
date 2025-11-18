# Tark frontend

next.js web interface for generating 3d meshes from real locations.

## setup

```bash
npm install
npm run dev
```

opens at `http://localhost:3000`

### env vars

create `.env`:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## structure

```
app/
  page.tsx          # landing page
  layout.tsx        # root layout
components/         # react components (next phase)
lib/
  api.ts           # backend api client
```

## scripts

```bash
npm run dev        # dev server (turbopack)
npm run build      # production build
npm run lint       # eslint
npm run type-check # typescript check
```

## api client

```typescript
import { generateMesh, calculateAreaSize } from "@/lib/api";

// generate mesh
const result = await generateMesh({
  north: 37.8,
  south: 37.75,
  east: -122.4,
  west: -122.45,
});

// calculate area
const { width, height, area } = calculateAreaSize(bbox);
```

## next steps

- leaflet map integration
- rectangle selection tool
- area preview ui
- validation feedback
