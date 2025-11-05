# GSSR Frontend (mini-dashboard)

This is a small Next.js 14 App Router dashboard skeleton for the GSSR project.

What was added:

- `lib/api.ts` — typed API helpers mapped to `API_REFERENCE.md` endpoints.
- `hooks/useStatus.tsx` — React Query hook to poll `GET /status/{job_id}`.
- `components/` — `DocumentList`, `UploadButton`, `DocumentStatusPanel`.
- `app/page.tsx` — dashboard layout wiring the components.

Environment
-----------

Create a `.env.local` in `frontend/` and set:

```
NEXT_PUBLIC_API_URL=https://your-api-base-url/
```

Install & run
--------------

From `frontend/`:

```bash
npm install
npm run dev
```

Notes
-----

- The UI is intentionally lightweight and uses Tailwind classes. It uses `@tanstack/react-query` and `axios`.
- The upload flow: `POST /upload` → PUT to returned presigned URL → `POST /trigger/{job_id}` (best-effort).
This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
